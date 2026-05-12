from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.database import get_db
import backend.models as models
from datetime import date, timedelta

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard Analytics"]
)

# ══════════════════════════════════════════════════════════════════════════════
# GENERAL KPIs
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/kpis/{city}")
def get_kpis(city: str, db: Session = Depends(get_db)):
    emp_query = db.query(models.Employee)
    if city != "all":
        emp_query = emp_query.filter(models.Employee.city == city)

    total_employees  = emp_query.count()
    active_employees = emp_query.filter(
        models.Employee.status == "Active").count()
    on_leave         = emp_query.filter(
        models.Employee.status == "On Leave").count()

    leave_query = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    )
    if city != "all":
        leave_query = leave_query.filter(models.Employee.city == city)

    pending_leaves  = leave_query.filter(
        models.LeaveRequest.status.in_(["Pending_Manager","Pending_HR"])
    ).count()
    approved_leaves = leave_query.filter(
        models.LeaveRequest.status == "Approved"
    ).count()

    doc_query = db.query(models.DocumentRequest).join(
        models.Employee,
        models.DocumentRequest.employee_id == models.Employee.employee_id
    )
    if city != "all":
        doc_query = doc_query.filter(models.Employee.city == city)

    pending_docs   = doc_query.filter(
        models.DocumentRequest.status == "Pending").count()
    generated_docs = doc_query.filter(
        models.DocumentRequest.status.in_(["Generated","Delivered"])
    ).count()

    return {
        "total_employees":     total_employees,
        "active_employees":    active_employees,
        "on_leave":            on_leave,
        "pending_leaves":      pending_leaves,
        "approved_leaves":     approved_leaves,
        "pending_documents":   pending_docs,
        "generated_documents": generated_docs
    }

# ══════════════════════════════════════════════════════════════════════════════
# LEAVE ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/leaves-by-department/{city}")
def leaves_by_department(city: str, db: Session = Depends(get_db)):
    # 1. On prépare la base de la requête (SELECT, JOIN, GROUP BY)
    query = db.query(
        models.Employee.department,
        func.count(models.LeaveRequest.request_id).label("total_leaves")
    ).join(
        models.LeaveRequest,
        models.Employee.employee_id == models.LeaveRequest.employee_id
    )

    # 2. ON AJOUTE LE FILTRE ICI : seulement si city n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. On termine par le group_by et on exécute (.all())
    results = query.group_by(models.Employee.department).all()
    
    return [{"department": r.department, "total_leaves": r.total_leaves} for r in results]


@router.get("/leaves-by-type/{city}")
def get_leaves_by_type(city: str, db: Session = Depends(get_db)):
    # 1. On initialise la base de la requête avec le JOIN indispensable
    query = db.query(
        models.LeaveRequest.leave_type,
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    )

    # 2. On applique le filtre de ville SEULEMENT si ce n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. On groupe et on exécute
    results = query.group_by(models.LeaveRequest.leave_type).all()
    
    return [{"leave_type": r.leave_type, "count": r.count} for r in results]


@router.get("/leaves-by-status/{city}")
def leaves_by_status(city: str, db: Session = Depends(get_db)):
    # 1. On initialise la requête avec le JOIN
    query = db.query(
        models.LeaveRequest.status,
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    )

    # 2. Application conditionnelle du filtre par ville
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. Groupement par statut et exécution
    results = query.group_by(models.LeaveRequest.status).all()
    
    return [{"status": r.status, "count": r.count} for r in results]

@router.get("/monthly-trends/{city}")
def monthly_trends(city: str, db: Session = Depends(get_db)):
    # 1. On prépare la base de la requête avec le JOIN
    query = db.query(
        func.month(models.LeaveRequest.submission_date).label("month"),
        func.year(models.LeaveRequest.submission_date).label("year"),
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    )

    # 2. On applique le filtre seulement si city n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. On ajoute le groupement et l'ordonnancement avant d'exécuter
    results = query.group_by(
        func.year(models.LeaveRequest.submission_date),
        func.month(models.LeaveRequest.submission_date)
    ).order_by(
        func.year(models.LeaveRequest.submission_date),
        func.month(models.LeaveRequest.submission_date)
    ).all()

    months_fr = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    
    return [{"period": f"{months_fr[r.month]} {r.year}",
             "count": r.count} for r in results]


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/documents-by-type/{city}")
def documents_by_type(city: str, db: Session = Depends(get_db)):
    # 1. Préparation de la requête de base avec la jointure vers Employee
    query = db.query(
        models.DocumentRequest.document_type,
        func.count(models.DocumentRequest.doc_request_id).label("count")
    ).join(
        models.Employee,
        models.DocumentRequest.employee_id == models.Employee.employee_id
    )

    # 2. On applique le filtre seulement si city n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. Groupement et exécution
    results = query.group_by(models.DocumentRequest.document_type).all()
    
    return [{"document_type": r.document_type, "count": r.count} for r in results]


@router.get("/avg-processing-time/{city}")
def avg_processing_time(city: str, db: Session = Depends(get_db)):
    query = db.query(
        models.DocumentRequest.document_type,
        func.avg(func.datediff(
            models.DocumentRequest.delivery_date,
            models.DocumentRequest.request_date
        )).label("avg_days")
    ).join(
        models.Employee,
        models.DocumentRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.DocumentRequest.delivery_date != None
    )
    if city != "all":
        query = query.filter(models.Employee.city == city)

    results = query.group_by(models.DocumentRequest.document_type).all()
    return [
        {
            "document_type": r.document_type,
            "avg_days": round(float(r.avg_days), 1) if r.avg_days else 0
        }
        for r in results
    ]

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

            at_risk.append({
                "employee_id": emp.employee_id,
                "name": f"{emp.first_name} {emp.last_name}",
                "department": emp.department,
                "city": emp.city,
                "leave_balance": emp.leave_balance_days,
                "last_leave": str(last_leave.start_date) if last_leave else "Jamais",
                "risk_level": "High" if not last_leave else "Medium",
                "recommendation": f"{emp.first_name} n'a pas pris de congé depuis 6+ mois."
            })
            
    return {"total_at_risk": len(at_risk), "employees": at_risk}


@router.get("/absence-predictions/{city}")
def absence_predictions(city: str, db: Session = Depends(get_db)):
    # 1. On initialise la requête avec le JOIN
    query = db.query(
        func.month(models.LeaveRequest.start_date).label("month"),
        func.count(models.LeaveRequest.request_id).label("count")
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.LeaveRequest.status == "Approved"
    )

    # 2. On ajoute le filtre de ville SEULEMENT si ce n'est pas "all"
    if city != "all":
        query = query.filter(models.Employee.city == city)

    # 3. On groupe, on trie et on exécute
    results = query.group_by(
        func.month(models.LeaveRequest.start_date)
    ).order_by(
        func.month(models.LeaveRequest.start_date)
    ).all()

    months_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    
    monthly_data = [{"month": months_fr[r.month], "absences": r.count} for r in results]

    # Find peak month
    peak = max(monthly_data, key=lambda x: x["absences"]) if monthly_data else None

    return {
        "monthly_distribution": monthly_data,
        "peak_month": peak["month"] if peak else None,
        "peak_absences": peak["absences"] if peak else 0,
        "prediction": f"Pic d'absences prévu en {peak['month']} ({peak['absences']} demandes historiquement)" if peak else "Données insuffisantes"
    }

@router.get("/department-alerts/{city}")
def department_alerts(city: str, db: Session = Depends(get_db)):
    alerts      = []
    departments = ["IT","Finance","HR","Marketing",
                   "Sales","Operations","Support","R&D"]

    for dept in departments:
        query = db.query(models.Employee).filter(
            models.Employee.department == dept
        )
        if city != "all":
            query = query.filter(models.Employee.city == city)
        team_size = query.count()

        absence_query = db.query(models.LeaveRequest).join(
            models.Employee,
            models.LeaveRequest.employee_id == models.Employee.employee_id
        ).filter(
            models.Employee.department == dept,
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= date.today(),
            models.LeaveRequest.end_date   >= date.today()
        )
        if city != "all":
            absence_query = absence_query.filter(models.Employee.city == city)
        current_absences = absence_query.count()

        if team_size > 0:
            absence_rate = (current_absences / team_size) * 100

            if absence_rate >= 30:
                alerts.append({
                    "department":    dept,
                    "team_size":     team_size,
                    "absent_today":  current_absences,
                    "absence_rate":  round(absence_rate, 1),
                    "alert_level":   "Critical" if absence_rate >= 50 else "Warning",
                    "message":       f"⚠️ {dept}: {current_absences}/{team_size} absents ({round(absence_rate,1)}%)"
                })

    return {"total_alerts": len(alerts), "alerts": alerts}


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

@router.get("/dashboard/department-alerts/{city}")
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

        # 3. On compte les absents uniquement parmi CES employés
        absent_employee_ids = db.query(models.LeaveRequest.employee_id).filter(
            models.LeaveRequest.employee_id.in_(employee_ids),
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= date.today(),
            models.LeaveRequest.end_date >= date.today()
        ).distinct().all()

        absent_count = len(absent_employee_ids)

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