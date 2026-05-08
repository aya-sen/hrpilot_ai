from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
import bcrypt

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    
    # 1. Find employee by email
    employee = db.query(models.Employee).filter(
        models.Employee.email == email
    ).first()
    
    # 2. Check if employee exists
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    # 3. Check password
    password_correct = bcrypt.checkpw(
        password.encode('utf-8'),
        employee.password_hash.encode('utf-8')
    )
    
    if not password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # 4. Return employee info
    return {
        "message": "Login successful",
        "employee_id": employee.employee_id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "role": employee.role,
        "city": employee.city,
        "department": employee.department,
        "position": employee.position
    }



 