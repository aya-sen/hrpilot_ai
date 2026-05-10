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

@router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)):

    total_employees   = db.query(models.Employee).count()
    active_employees  = db.query(models.Employee).filter(models.Employee.status == "Active").count()
    on_leave          = db.query(models.Employee).filter(models.Employee.status == "On Leave").count()

    pending_leaves    = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status.in_(["Pending_Manager", "Pending_HR"])
    ).count()

    approved_leaves   = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == "Approved"
    ).count()

    pending_docs      = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.status == "Pending"
    ).count()

    generated_docs    = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.status.in_(["Generated", "Delivered"])
    ).count()

    return {
        "total_employees":  total_employees,
        "active_employees": active_employees,
        "on_leave":         on_leave,
        "pending_leaves":   pending_leaves,
        "approved_leaves":  approved_leaves,
        "pending_documents": pending_docs,
        "generated_documents": generated_docs
    }

# ══════════════════════════════════════════════════════════════════════════════
# LEAVE ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/leaves-by-department")
def leaves_by_department(db: Session = Depends(get_db)):

    results = db.query(
        models.Employee.department,
        func.count(models.LeaveRequest.request_id).label("total_leaves")
    ).join(
        models.LeaveRequest,
        models.Employee.employee_id == models.LeaveRequest.employee_id
    ).group_by(
        models.Employee.department
    ).all()

    return [{"department": r.department, "total_leaves": r.total_leaves} for r in results]


@router.get("/leaves-by-type")
def leaves_by_type(db: Session = Depends(get_db)):

    results = db.query(
        models.LeaveRequest.leave_type,
        func.count(models.LeaveRequest.request_id).label("count")
    ).group_by(
        models.LeaveRequest.leave_type
    ).all()

    return [{"leave_type": r.leave_type, "count": r.count} for r in results]


@router.get("/leaves-by-status")
def leaves_by_status(db: Session = Depends(get_db)):

    results = db.query(
        models.LeaveRequest.status,
        func.count(models.LeaveRequest.request_id).label("count")
    ).group_by(
        models.LeaveRequest.status
    ).all()

    return [{"status": r.status, "count": r.count} for r in results]


@router.get("/monthly-trends")
def monthly_trends(db: Session = Depends(get_db)):

    results = db.query(
        func.month(models.LeaveRequest.submission_date).label("month"),
        func.year(models.LeaveRequest.submission_date).label("year"),
        func.count(models.LeaveRequest.request_id).label("count")
    ).group_by(
        func.year(models.LeaveRequest.submission_date),
        func.month(models.LeaveRequest.submission_date)
    ).order_by(
        func.year(models.LeaveRequest.submission_date),
        func.month(models.LeaveRequest.submission_date)
    ).all()

    months_fr = ['', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']

    return [
        {
            "period": f"{months_fr[r.month]} {r.year}",
            "count": r.count
        }
        for r in results
    ]

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/documents-by-type")
def documents_by_type(db: Session = Depends(get_db)):

    results = db.query(
        models.DocumentRequest.document_type,
        func.count(models.DocumentRequest.doc_request_id).label("count")
    ).group_by(
        models.DocumentRequest.document_type
    ).all()

    return [{"document_type": r.document_type, "count": r.count} for r in results]


@router.get("/avg-processing-time")
def avg_processing_time(db: Session = Depends(get_db)):

    results = db.query(
        models.DocumentRequest.document_type,
        func.avg(
            func.datediff(
                models.DocumentRequest.delivery_date,
                models.DocumentRequest.request_date
            )
        ).label("avg_days")
    ).filter(
        models.DocumentRequest.delivery_date != None
    ).group_by(
        models.DocumentRequest.document_type
    ).all()

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

@router.get("/burnout-risk")
def detect_burnout_risk(db: Session = Depends(get_db)):

    six_months_ago = date.today() - timedelta(days=180)

    # Get all active employees
    all_employees = db.query(models.Employee).filter(
        models.Employee.status == "Active",
        models.Employee.role == "Employee"
    ).all()

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
            ).order_by(
                models.LeaveRequest.start_date.desc()
            ).first()

            at_risk.append({
                "employee_id":   emp.employee_id,
                "name":          f"{emp.first_name} {emp.last_name}",
                "department":    emp.department,
                "city":          emp.city,
                "leave_balance": emp.leave_balance_days,
                "last_leave":    str(last_leave.start_date) if last_leave else "Jamais",
                "risk_level":    "High" if not last_leave else "Medium",
                "recommendation": f"Recommandation : {emp.first_name} n'a pas pris de congé depuis plus de 6 mois. Suggérez-lui de poser quelques jours."
            })

    return {
        "total_at_risk": len(at_risk),
        "employees": at_risk
    }


@router.get("/absence-predictions")
def absence_predictions(db: Session = Depends(get_db)):

    # Analyze historical data by month to find peak periods
    results = db.query(
        func.month(models.LeaveRequest.start_date).label("month"),
        func.count(models.LeaveRequest.request_id).label("count")
    ).filter(
        models.LeaveRequest.status == "Approved"
    ).group_by(
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


@router.get("/department-alerts")
def department_alerts(db: Session = Depends(get_db)):

    alerts = []
    departments = ["IT", "Finance", "HR", "Marketing", "Sales", "Operations", "Support", "R&D"]

    for dept in departments:
        team_size = db.query(models.Employee).filter(
            models.Employee.department == dept
        ).count()

        # Count currently approved absences
        current_absences = db.query(models.LeaveRequest).join(
            models.Employee,
            models.LeaveRequest.employee_id == models.Employee.employee_id
        ).filter(
            models.Employee.department == dept,
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= date.today(),
            models.LeaveRequest.end_date >= date.today()
        ).count()

        if team_size > 0:
            absence_rate = (current_absences / team_size) * 100

            if absence_rate >= 30:
                alerts.append({
                    "department":     dept,
                    "team_size":      team_size,
                    "absent_today":   current_absences,
                    "absence_rate":   round(absence_rate, 1),
                    "alert_level":    "Critical" if absence_rate >= 50 else "Warning",
                    "message":        f"⚠️ {dept}: {current_absences}/{team_size} employés absents aujourd'hui ({round(absence_rate,1)}%)"
                })

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }


@router.get("/city-stats/{city}")
def city_stats(city: str, db: Session = Depends(get_db)):

    total = db.query(models.Employee).filter(
        models.Employee.city == city
    ).count()

    active = db.query(models.Employee).filter(
        models.Employee.city == city,
        models.Employee.status == "Active"
    ).count()

    pending_leaves = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.city == city,
        models.LeaveRequest.status == "Pending_HR"
    ).count()

    pending_docs = db.query(models.DocumentRequest).join(
        models.Employee,
        models.DocumentRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.city == city,
        models.DocumentRequest.status == "Pending"
    ).count()

    return {
        "city":           city,
        "total_employees": total,
        "active":         active,
        "pending_leaves": pending_leaves,
        "pending_docs":   pending_docs
    }



@router.get("/gender-distribution")
def gender_distribution(db: Session = Depends(get_db)):
    results = db.query(
        models.Employee.gender,
        func.count(models.Employee.employee_id).label("count")
    ).group_by(models.Employee.gender).all()
    return [{"gender": r.gender, "count": r.count} for r in results]


@router.get("/contract-distribution")
def contract_distribution(db: Session = Depends(get_db)):
    results = db.query(
        models.Employee.contract_type,
        func.count(models.Employee.employee_id).label("count")
    ).group_by(models.Employee.contract_type).all()
    return [{"contract_type": r.contract_type, "count": r.count} for r in results]


@router.get("/turnover-rate")
def turnover_rate(db: Session = Depends(get_db)):
    total     = db.query(models.Employee).count()
    resigned  = db.query(models.Employee).filter(
        models.Employee.status == "Resigned"
    ).count()
    rate = round((resigned / total * 100), 1) if total > 0 else 0
    return {"total": total, "resigned": resigned, "turnover_rate": rate}


@router.get("/avg-seniority")
def avg_seniority(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).filter(
        models.Employee.hire_date != None
    ).all()
    if not employees:
        return {"avg_years": 0}
    today = date.today()
    total_days = sum((today - emp.hire_date).days for emp in employees)
    avg_years  = round(total_days / len(employees) / 365, 1)
    return {"avg_years": avg_years, "total_employees": len(employees)}


@router.get("/absenteeism-rate/{city}")
def absenteeism_rate(city: str, db: Session = Depends(get_db)):
    total_city = db.query(models.Employee).filter(
        models.Employee.city == city
    ).count()
    on_leave = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.city == city,
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= date.today(),
        models.LeaveRequest.end_date >= date.today()
    ).count()
    rate = round((on_leave / total_city * 100), 1) if total_city > 0 else 0
    return {"city": city, "total": total_city, "on_leave": on_leave, "rate": rate}