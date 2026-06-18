from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, case
from backend.database import get_db
import backend.models as models
from datetime import date, datetime, timedelta

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard Analytics"]
)


@router.get("/city-stats/{city}")
def city_stats(city: str, db: Session = Depends(get_db)):

    # 1. Total Employés
    query_total = db.query(models.Employee)
    if city != "all":
        query_total = query_total.filter(models.Employee.city == city)
    total = query_total.count()

    # 2. Actifs
    query_active = db.query(models.Employee).filter(models.Employee.status == "Active")
    if city != "all":
        query_active = query_active.filter(models.Employee.city == city)
    active = query_active.count()

    # 3. Congés en attente
    query_leaves = db.query(models.LeaveRequest).join(
        models.Employee, models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(models.LeaveRequest.status == "Pending_HR")
    if city != "all":
        query_leaves = query_leaves.filter(models.Employee.city == city)
    pending_leaves = query_leaves.count()

    # 4. Docs en attente
    query_docs = db.query(models.DocumentRequest).join(
        models.Employee, models.DocumentRequest.employee_id == models.Employee.employee_id
    ).filter(models.DocumentRequest.status == "Pending")
    if city != "all":
        query_docs = query_docs.filter(models.Employee.city == city)
    pending_docs = query_docs.count()

    return {
        "city": city,
        "total_employees": total,
        "active": active,
        "pending_leaves": pending_leaves,
        "pending_docs": pending_docs
    }

# ══════════════════════════════════════════════════════════════════════════════
# LEAVE ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/leaves-pressure-summer/{city}")
def get_leaves_pressure_summer(city: str, db: Session = Depends(get_db)):
    months = [6, 7, 8]  # Juin, Juillet, Août 2026
    departments = [d[0] for d in db.query(models.Employee.department).distinct().all() if d[0]]
    
    pressure_data = []
    
    for dept in departments:
        for m in months:
            # 1. Nombre total d'employés dans le département (pour calibrer la taille de l'équipe)
            emp_query = db.query(models.Employee.employee_id).filter(models.Employee.department == dept)
            if city.lower() != "all":
                emp_query = emp_query.filter(models.Employee.city.ilike(city))
            
            total_staff = emp_query.count()
            if total_staff == 0:
                continue
                
            # 2. Compter le nombre de demandes EN ATTENTE (Pending) pour ce mois
            # CORRECTION : On crée la sous-requête et on lui applique le filtre city !
            sub_emp_query = db.query(models.Employee.employee_id).filter(models.Employee.department == dept)
            if city.lower() != "all":
                sub_emp_query = sub_emp_query.filter(models.Employee.city.ilike(city))

            pending_requests = db.query(models.LeaveRequest.employee_id).distinct().filter(
                models.LeaveRequest.employee_id.in_(sub_emp_query), # Utilise la sous-requête filtrée ici
                models.LeaveRequest.status == "Pending_Manager",
                extract('month', models.LeaveRequest.start_date) == m,
                extract('year', models.LeaveRequest.start_date) == 2026
            ).count()
            
            month_names = {6: "Juin", 7: "Juillet", 8: "Août"}
            pressure_data.append({
                "Département": dept,
                "Mois": month_names[m],
                "Demandes en Attente": pending_requests,
                "Alerte Risque": "Élevé" if (pending_requests / total_staff) > 0.3 else "Normal"
            })
            
    return pressure_data

from datetime import datetime
from sqlalchemy import extract

@router.get("/leaves-by-type/{city}")
def get_leaves_by_type(city: str, db: Session = Depends(get_db)):
    # 1. On récupère automatiquement l'année actuelle du serveur
    current_year = datetime.now().year

    # 2. On initialise la base de la requête avec la jointure indispensable
    # et on filtre dynamiquement sur l'année en cours
    query = db.query(
        models.LeaveRequest.leave_type,
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        extract('year', models.LeaveRequest.start_date) == current_year
    )

    # 3. On applique le filtre de ville SEULEMENT si ce n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 4. On groupe et on exécute
    results = query.group_by(models.LeaveRequest.leave_type).all()
    
    return [{"leave_type": r.leave_type, "count": r.count} for r in results]
# ══════════════════════════════════════════════════════════════════════════════
# SMART FEATURES — BURNOUT & PREDICTIONS
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/burnout-risk/{city}")
def get_burnout_risk(city: str, db: Session = Depends(get_db)):
    six_months_ago = date.today() - timedelta(days=180)
    
    # 1. On prépare la requête de base pour les employés actifs
    query = db.query(models.Employee).filter(
        models.Employee.status == "Active",
        models.Employee.role == "Employee"
    )

    # 2. On ajoute le filtre de ville SEULEMENT si ce n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)
    
    # 3. On récupère la liste des employés (filtrée ou non)
    all_employees = query.all()

    at_risk = []
    
    # --- AJOUT SÉCURITÉ ANNÉE EN COURS ---
    from datetime import datetime
    current_year = datetime.now().year

    for emp in all_employees:
        # Check if they have any approved leave in last 6 months
        recent_leave = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.employee_id == emp.employee_id,
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date >= six_months_ago
        ).first()

        if not recent_leave:
            # Check when was their last approved leave ever
            last_leave = db.query(models.LeaveRequest).filter(
                models.LeaveRequest.employee_id == emp.employee_id,
                models.LeaveRequest.status == "Approved"
            ).order_by(models.LeaveRequest.start_date.desc()).first()

            # ── 🛠️ CALCUL DYNAMIQUE DU SOLDE POUR L'ANNÉE EN COURS ──
            # On cherche uniquement les congés approuvés de l'année en cours
            approved_leaves_this_year = db.query(models.LeaveRequest).filter(
                models.LeaveRequest.employee_id == emp.employee_id,
                models.LeaveRequest.status == "Approved",
                models.LeaveRequest.start_date >= f"{current_year}-01-01",
                models.LeaveRequest.end_date <= f"{current_year}-12-31"
            ).all()
            
            days_taken_this_year = sum(int(l.duration_days or 0) for l in approved_leaves_this_year)
            
            # Allocation de base légale (26 jours) moins les jours pris cette année
            LEGAL_BASE_ALLOCATION = 26
            solde_current_year = max(LEGAL_BASE_ALLOCATION - days_taken_this_year, 0)
            # ────────────────────────────────────────────────────────

            at_risk.append({
                "employee_id": emp.employee_id,
                "name": f"{emp.first_name} {emp.last_name}",
                "department": emp.department,
                "city": emp.city,
                "leave_balance": solde_current_year,  # <-- On utilise le solde corrigé ici !
                "last_leave": str(last_leave.start_date) if last_leave else "Jamais",
                "risk_level": "High" if not last_leave else "Medium",
                "recommendation": f"{emp.first_name} n'a pas pris de congé depuis 6+ mois."
            })
            
    return {"total_at_risk": len(at_risk), "employees": at_risk}

@router.get("/leaves-monthly-current-year/{city}")
def get_leaves_monthly_current_year(city: str, db: Session = Depends(get_db)):
    # Détection AUTOMATIQUE de l'année en cours
    current_year = datetime.now().year
    
    # 1. Requête sur l'année dynamique détectée avec statut Approved
    query = db.query(
        extract('month', models.LeaveRequest.start_date).label("month"),
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.LeaveRequest.status == "Approved",
        extract('year', models.LeaveRequest.start_date) == current_year
    )

    # 2. Filtre géographique
    if city.lower() != "all":
        query = query.filter(models.Employee.city.ilike(city))

    results = query.group_by(extract('month', models.LeaveRequest.start_date)).all()

    # Initialisation de tous les mois à 0 pour avoir un graphique propre de Janvier à Décembre
    months_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    
    full_year_data = {months_fr[i]: 0 for i in range(1, 13)}
    
    for r in results:
        if r.month:
            full_year_data[months_fr[int(r.month)]] = r.count

    # Formatage final pour le tableau de données
    monthly_data = [{"month": m, "absences": count} for m, count in full_year_data.items()]

    # Calcul du pic de l'année en cours
    peak = max(monthly_data, key=lambda x: x["absences"]) if results else None

    # Message professionnel dynamique avec l'année automatique
    if peak and peak["absences"] > 0:
        info_msg = f"Pic d'absences enregistré en {peak['month']} avec {peak['absences']} congés validés pour {current_year}."
    else:
        info_msg = f"Aucune absence enregistrée ou validée sur l'année {current_year}."

    return {
        "monthly_distribution": monthly_data,
        "peak_month": peak["month"] if (peak and peak["absences"] > 0) else None,
        "info_message": info_msg
    }


@router.get("/gender-distribution/{city}")
def gender_distribution(city: str, db: Session = Depends(get_db)):
    # On initialise la requête
    query = db.query(
        models.Employee.gender,
        func.count(models.Employee.employee_id).label("count")
    )

    # Filtre conditionnel pour la ville
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # Groupement et exécution
    results = query.group_by(models.Employee.gender).all()
    
    return [{"gender": r.gender, "count": r.count} for r in results]


@router.get("/contract-distribution/{city}")
def contract_distribution(city: str, db: Session = Depends(get_db)):
    # On initialise la requête
    query = db.query(
        models.Employee.contract_type,
        func.count(models.Employee.employee_id).label("count")
    )

    # Filtre conditionnel pour la ville
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # Groupement et exécution
    results = query.group_by(models.Employee.contract_type).all()
    
    return [{"contract_type": r.contract_type, "count": r.count} for r in results]


@router.get("/turnover-rate/{city}")
def turnover_rate(city: str, db: Session = Depends(get_db)):
    query = db.query(models.Employee)
    if city != "all":
        query = query.filter(models.Employee.city == city)
    
    total    = query.count()
    resigned = query.filter(models.Employee.status == "Resigned").count()
    rate     = round((resigned / total * 100), 1) if total > 0 else 0
    return {"total": total, "resigned": resigned, "turnover_rate": rate}


@router.get("/avg-seniority/{city}")
def avg_seniority(city: str, db: Session = Depends(get_db)):
    query = db.query(models.Employee).filter(
        models.Employee.hire_date != None
    )
    if city != "all":
        query = query.filter(models.Employee.city == city)
    
    employees = query.all()
    if not employees:
        return {"avg_years": 0}
    today     = date.today()
    total_days = sum((today - emp.hire_date).days for emp in employees)
    avg_years  = round(total_days / len(employees) / 365, 1)
    return {"avg_years": avg_years, "total_employees": len(employees)}



@router.get("/absenteeism-rate/{city}")
def get_absenteeism_rate(city: str, db: Session = Depends(get_db)):
    # 1. Calculer le nombre total d'employés
    emp_query = db.query(models.Employee).filter(models.Employee.status == "Active")
    if city != "all":
        emp_query = emp_query.filter(models.Employee.city == city)
    
    total_employees = emp_query.count()
    
    if total_employees == 0:
        return {"rate": 0.0}

    # 2. Calculer le nombre d'employés absents AUJOURD'HUI
    # Un employé est absent si son congé est 'Approved' et que la date du jour est incluse
    absent_query = db.query(models.LeaveRequest).join(
        models.Employee, models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= date.today(),
        models.LeaveRequest.end_date >= date.today()
    )
    
    if city != "all":
        absent_query = absent_query.filter(models.Employee.city == city)
    
    # On utilise .distinct() au cas où un employé aurait deux demandes le même jour
    absent_count = absent_query.distinct(models.LeaveRequest.employee_id).count()

    # 3. Calcul du taux
    rate = (absent_count / total_employees) * 100
    
    return {
        "city": city,
        "absent_count": absent_count,
        "total_employees": total_employees,
        "rate": round(rate, 1)
    }

@router.get("/department-alerts/{city}")
def get_department_alerts(city: str, db: Session = Depends(get_db)):
    # 1. Liste des départements
    departments = [d[0] for d in db.query(models.Employee.department).distinct().all() if d[0]]
    alerts = []

    for dept in departments:
        # 2. Filtrage TRÈS strict par département ET ville
        query = db.query(models.Employee).filter(models.Employee.department == dept)
        
        if city.lower() != "all":
            # On force la comparaison en minuscules pour éviter les erreurs de frappe (ex: rabat vs Rabat)
            query = query.filter(models.Employee.city.ilike(city))
        
        employees = query.all()
        employee_ids = [e.employee_id for e in employees]
        total_dept = len(employee_ids)

        if total_dept == 0:
            continue

        # Step 3 — get the raw IDs as a plain Python set
        absent_rows = db.query(models.LeaveRequest.employee_id).filter(
            models.LeaveRequest.employee_id.in_(employee_ids),
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= date.today(),
            models.LeaveRequest.end_date >= date.today()
        ).all()

        # Unpack tuples and deduplicate in Python — 100% reliable
        absent_ids_set = set(row[0] for row in absent_rows)

        # Intersect with the known valid employee IDs — bulletproof
        valid_employee_ids_set = set(employee_ids)
        absent_count = len(absent_ids_set & valid_employee_ids_set)

        # 4. Calcul final
        absence_rate = (absent_count / total_dept) if total_dept > 0 else 0
        
        if absence_rate > 0.3:
            level = "Critical" if absence_rate > 0.5 else "Warning"
            # On utilise 'city' pour le message
            display_city = city if city.lower() != "all" else "National"
            
            alerts.append({
                "department": dept,
                "absent_count": absent_count,
                "total_count": total_dept,
                "alert_level": level,
                "message": f"🚨 {dept} ({display_city}) : {absent_count}/{total_dept} absents ({round(absence_rate*100, 1)}%)"
            })

    return {"alerts": alerts}