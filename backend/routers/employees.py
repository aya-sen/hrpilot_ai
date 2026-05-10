from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import EmployeeResponse
import backend.models as models
from typing import List

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
@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found"
        )
    return employee

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