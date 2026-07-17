from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import EmployeeResponse 
import backend.models as models
from typing import List
import bcrypt as bcrypt_lib


router = APIRouter(
    prefix="/employees",
    tags=["Employees"]
)

def has_active_approved_leave(employee_id: int, today: date, db: Session) -> bool:
    return (
        db.query(models.LeaveRequest)
        .filter(
            models.LeaveRequest.employee_id == employee_id,
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= today,
            models.LeaveRequest.end_date >= today,
        )
        .first()
        is not None
    )


def get_real_solde(employee_id: int, year: int, db: Session) -> int:
    # 1. Récupérer les droits définis en base (Total autorisé + Ajustement manuel)
    balance_record = db.query(models.AnnualBalance).filter(
        models.AnnualBalance.employee_id == employee_id,
        models.AnnualBalance.year == year
    ).first()
    
    # Si rien n'est défini pour l'année, on part sur 26 par défaut
    total_allowed = balance_record.total_allowed if balance_record else 26
    manual_adjustment = balance_record.manual_adjustment if balance_record else 0
    
    # 2. Calculer les jours pris cette année
    # On utilise l'overlap logic (plus précis)
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    
    leaves_taken = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= year_end,
        models.LeaveRequest.end_date >= year_start
    ).all()
    
    days_taken = sum(int(l.duration_days or 0) for l in leaves_taken)
    
    # 3. Formule finale
    return max((total_allowed + manual_adjustment) - days_taken, 0)

@router.get("/")
def get_all_employees(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).all()
    current_year = datetime.now().year
    today = date.today()

    results = []
    for emp in employees:
        emp_dict = {c.name: getattr(emp, c.name) for c in emp.__table__.columns}
        emp_dict['leave_balance_days'] = get_real_solde(emp.employee_id, current_year, db)

        if emp.status != "Resigned":
            computed_status = "On Leave" if has_active_approved_leave(emp.employee_id, today, db) else "Active"
            emp_dict['status'] = computed_status

            # ✅ Persiste la correction en base si elle diffère
            if emp.status != computed_status:
                emp.status = computed_status

        results.append(emp_dict)

    db.commit()  # sauvegarde toutes les corrections faites dans la boucle
    return results


# ── Get one employee by ID ────────────────────────────────────────────────────
@router.get("/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    current_year = datetime.now().year
    today = date.today()
    real_solde = get_real_solde(employee_id, current_year, db)
    
    emp_dict = {c.name: getattr(employee, c.name) for c in employee.__table__.columns}
    emp_dict['leave_balance_days'] = real_solde

    if employee.status != "Resigned":
        computed_status = "On Leave" if has_active_approved_leave(employee_id, today, db) else "Active"
        emp_dict['status'] = computed_status
        if employee.status != computed_status:
            employee.status = computed_status
            db.commit()
    
    return emp_dict


# ── Get employees by department ───────────────────────────────────────────────
@router.get("/department/{department}")
def get_by_department(department: str, db: Session = Depends(get_db)):
    employees = db.query(models.Employee).filter(models.Employee.department == department).all()
    current_year = datetime.now().year
    today = date.today()
    
    results = []
    for emp in employees:
        emp_dict = {c.name: getattr(emp, c.name) for c in emp.__table__.columns}
        emp_dict['leave_balance_days'] = get_real_solde(emp.employee_id, current_year, db)

        if emp.status != "Resigned":
            computed_status = "On Leave" if has_active_approved_leave(emp.employee_id, today, db) else "Active"
            emp_dict['status'] = computed_status
            if emp.status != computed_status:
                emp.status = computed_status

        results.append(emp_dict)
        
    db.commit()
    return results


# ── Get team of a manager ─────────────────────────────────────────────────────
@router.get("/manager/{manager_id}/team")
def get_manager_team(manager_id: int, db: Session = Depends(get_db)):
    team = db.query(models.Employee).filter(models.Employee.manager_id == manager_id).all()
    current_year = datetime.now().year
    today = date.today()
    
    results = []
    for emp in team:
        emp_dict = {c.name: getattr(emp, c.name) for c in emp.__table__.columns}
        emp_dict['leave_balance_days'] = get_real_solde(emp.employee_id, current_year, db)

        if emp.status != "Resigned":
            computed_status = "On Leave" if has_active_approved_leave(emp.employee_id, today, db) else "Active"
            emp_dict['status'] = computed_status
            if emp.status != computed_status:
                emp.status = computed_status

        results.append(emp_dict)
        
    db.commit()
    return results

# ── Update employee (HR only) ─────────────────────────────────────────────────
@router.put("/{employee_id}/status")
def update_status(employee_id: int, new_status: str, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    employee.status = new_status
    db.commit()
    db.refresh(employee)
    return {"message": f"Status updated to {new_status}", "employee_id": employee_id}

# ── Update leave balance ──────────────────────────────────────────────────────
@router.put("/{employee_id}/leave-balance")
def update_leave_balance(employee_id: int, days_to_deduct: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    if employee.leave_balance_days < days_to_deduct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient leave balance. Available: {employee.leave_balance_days} days"
        )
    
    employee.leave_balance_days -= days_to_deduct
    db.commit()
    db.refresh(employee)
    return {
        "message": "Leave balance updated",
        "employee_id": employee_id,
        "new_balance": employee.leave_balance_days
    }


import bcrypt as bcrypt_lib

@router.put("/{employee_id}/change-password")
def change_password(employee_id: int, old_password: str,
                    new_password: str, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Verify old password
    if not bcrypt_lib.checkpw(old_password.encode("utf-8"),
                               employee.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")

    # Hash new password
    new_hash = bcrypt_lib.hashpw(new_password.encode("utf-8"),
                                 bcrypt_lib.gensalt()).decode("utf-8")
    employee.password_hash = new_hash

    # After success: disable forced change
    if hasattr(employee, "must_change_password"):
        employee.must_change_password = 0

    db.commit()
    return {"message": "Mot de passe modifié avec succès"}

from datetime import datetime  # À ajouter en haut de ton fichier backend
import os
import random
import string
from backend.mailer import send_temp_password_email


@router.post("/add")
def add_employee(data: dict, db: Session = Depends(get_db)):
    # ── 0) HR city security ────────────────────────────────────────────────
    hr_city = data.get("hr_city")
    if not hr_city:
        raise HTTPException(status_code=400, detail="Missing hr_city")

    if data.get("city") != hr_city:
        raise HTTPException(
            status_code=403,
            detail=f"City mismatch: data.city={data.get('city')} must match hr_city={hr_city}",
        )

    # 1. Vérification e-mail
    existing = db.query(models.Employee).filter(models.Employee.email == data.get("email")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # 2. Generate random temp password + hash
    alphabet = string.ascii_letters + string.digits
    temp_password = "".join(random.choice(alphabet) for _ in range(12)) + "!"

    temp_hash = bcrypt_lib.hashpw(
        temp_password.encode("utf-8"),
        bcrypt_lib.gensalt(),
    ).decode("utf-8")

    # ── 🛠️ RECHERCHE AUTOMATIQUE DU MANAGER DU DÉPARTEMENT ──
    detected_manager_id = None
    if data.get("role") == "Employee":
        dept_manager = db.query(models.Employee).filter(
            models.Employee.department == data.get("department"),
            models.Employee.role == "Manager",
            models.Employee.status == "Active",
        ).first()

        if dept_manager:
            detected_manager_id = dept_manager.employee_id
    # ────────────────────────────────────────────────────────

    new_emp = models.Employee(
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        email=data.get("email"),
        password_hash=temp_hash,
        must_change_password=1,
        phone_number=data.get("phone_number"),
        gender=data.get("gender"),
        birth_date=data.get("birth_date"),
        city=data.get("city"),
        department=data.get("department"),
        position=data.get("position"),
        contract_type=data.get("contract_type"),
        hire_date=data.get("hire_date"),
        salary=data.get("salary"),
        leave_balance_days=26,
        status="Active",
        role=data.get("role", "Employee"),
        manager_id=detected_manager_id,
    )

    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    # 3) Send temp password email once (plain once)
    #    If SMTP is not configured, we still keep the employee, but surface error.
    try:
        send_temp_password_email(
            to_email=new_emp.email,
            to_name=f"{new_emp.first_name}",
            city=hr_city,
            temp_password=temp_password,
        )
    except Exception as e:
        # Do not expose password in error.
        raise HTTPException(status_code=500, detail=f"Employee created but failed to send email: {e}")

    return {
        "message": "Employee added successfully (temp password emailed)",
        "employee_id": new_emp.employee_id,
    }


@router.put("/{employee_id}/update")
def update_employee(employee_id: int, data: dict, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # If HR updates leave_balance_days in the UI, store it in AnnualBalance for the CURRENT year
    if "leave_balance_days" in data and data["leave_balance_days"] is not None:
        current_year = datetime.now().year
        leave_balance_days = int(data["leave_balance_days"])

        # create or update AnnualBalance row for this employee+year
        balance = db.query(models.AnnualBalance).filter(
            models.AnnualBalance.employee_id == employee_id,
            models.AnnualBalance.year == current_year
        ).first()

        if not balance:
            balance = models.AnnualBalance(
                employee_id=employee_id,
                year=current_year,
                total_allowed=26,
                manual_adjustment=0,
            )
            db.add(balance)

        # We interpret UI value as the desired final balance for the year,
        # so we adjust manual_adjustment accordingly.
        # days taken is based on approved leaves in the current year.
        year_start = f"{current_year}-01-01"
        year_end = f"{current_year}-12-31"
        days_taken = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.employee_id == employee_id,
            models.LeaveRequest.status == "Approved",
            models.LeaveRequest.start_date <= year_end,
            models.LeaveRequest.end_date >= year_start,
        ).all()
        days_taken_sum = sum(int(l.duration_days or 0) for l in days_taken)

        # total_allowed is the legal entitlement (default 26)
        total_allowed = balance.total_allowed or 26
        # balance = total_allowed + manual_adjustment - days_taken_sum  => manual_adjustment = balance + days_taken_sum - total_allowed
        balance.manual_adjustment = int(leave_balance_days) + days_taken_sum - int(total_allowed)

        # keep employees.leave_balance_days in sync for compatibility with other code paths
        employee.leave_balance_days = leave_balance_days

    # Update the other editable fields (DO NOT overwrite leave_balance_days here)
    updatable_fields = [
        "first_name", "last_name", "phone_number", "city",
        "department", "position", "contract_type", "salary",
        "status", "role", "manager_id"
    ]

    for field in updatable_fields:
        if field in data and data[field] is not None:
            setattr(employee, field, data[field])
    
    db.commit()
    db.refresh(employee)
    return {"message": "Employee updated successfully"}