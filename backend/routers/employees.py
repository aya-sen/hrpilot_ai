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

# ── Get all employees (HR only) ───────────────────────────────────────────────
@router.get("/", response_model=List[EmployeeResponse])
def get_all_employees(db: Session = Depends(get_db)):
    employees = db.query(models.Employee).all()
    return employees

# ── Get one employee by ID ────────────────────────────────────────────────────
@router.get("/{employee_id}")  # 💡 Tip: Removed response_model so it accepts our custom dynamic dict
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    
    # 1. Compute approved leave days taken ONLY in the current year (2026)
    from datetime import datetime
    current_year = datetime.now().year
    
    approved_leaves_this_year = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date >= f"{current_year}-01-01",
        models.LeaveRequest.end_date <= f"{current_year}-12-31"
    ).all()
    
    days_taken_this_year = sum(int(l.duration_days or 0) for l in approved_leaves_this_year)
    
    # 2. Use the standard Moroccan legal baseline (18 days) for the prototype
    LEGAL_BASE_ALLOCATION = 18
    solde_2026 = max(LEGAL_BASE_ALLOCATION - days_taken_this_year, 0)
    
    # 3. Convert the SQLAlchemy object to a dictionary to safely swap the value
    employee_dict = {c.name: getattr(employee, c.name) for c in employee.__table__.columns}
    
    # 4. Overwrite the field before sending it to the frontend!
    employee_dict['leave_balance_days'] = solde_2026
    
    return employee_dict

# ── Get employees by department ───────────────────────────────────────────────
@router.get("/department/{department}", response_model=List[EmployeeResponse])
def get_by_department(department: str, db: Session = Depends(get_db)):
    employees = db.query(models.Employee).filter(
        models.Employee.department == department
    ).all()
    return employees

# ── Get team of a manager ─────────────────────────────────────────────────────
@router.get("/manager/{manager_id}/team", response_model=List[EmployeeResponse])
def get_manager_team(manager_id: int, db: Session = Depends(get_db)):
    team = db.query(models.Employee).filter(
        models.Employee.manager_id == manager_id
    ).all()
    return team

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
    if not bcrypt_lib.checkpw(old_password.encode('utf-8'),
                               employee.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    
    # Hash new password
    new_hash = bcrypt_lib.hashpw(new_password.encode('utf-8'),
                                  bcrypt_lib.gensalt()).decode('utf-8')
    employee.password_hash = new_hash
    db.commit()
    return {"message": "Mot de passe modifié avec succès"}


@router.post("/add")
def add_employee(data: dict, db: Session = Depends(get_db)):

    # Check email doesn't exist
    existing = db.query(models.Employee).filter(
        models.Employee.email == data.get("email")
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Hash default password
    default_hash = bcrypt_lib.hashpw(
        "Password123!".encode('utf-8'),
        bcrypt_lib.gensalt()
    ).decode('utf-8')

    new_emp = models.Employee(
        first_name        = data.get("first_name"),
        last_name         = data.get("last_name"),
        email             = data.get("email"),
        password_hash     = default_hash,
        phone_number      = data.get("phone_number"),
        gender            = data.get("gender"),
        birth_date        = data.get("birth_date"),
        city              = data.get("city"),
        department        = data.get("department"),
        position          = data.get("position"),
        contract_type     = data.get("contract_type"),
        hire_date         = data.get("hire_date"),
        salary            = data.get("salary"),
        leave_balance_days = 28,
        status            = "Active",
        role              = data.get("role", "Employee")
    )

    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    return {
        "message":     "Employee added successfully",
        "employee_id": new_emp.employee_id,
        "email":       new_emp.email
    }

@router.put("/{employee_id}/update")
def update_employee(employee_id: int, data: dict, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    updatable_fields = [
        "first_name", "last_name", "phone_number", "city",
        "department", "position", "contract_type", "salary",
        "leave_balance_days", "status", "role", "manager_id"
    ]
    for field in updatable_fields:
        if field in data and data[field] is not None:
            setattr(employee, field, data[field])
    
    db.commit()
    db.refresh(employee)
    return {"message": "Employee updated successfully"}