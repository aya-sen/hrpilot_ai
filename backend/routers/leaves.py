from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.routers.employees import get_real_solde
from backend.schemas import LeaveRequestCreate, LeaveRequestResponse
import backend.models as models
from typing import List
from datetime import date, datetime
from fastapi import UploadFile, File
import shutil
import os
from backend.document_generator import generate_lettre_conge


router = APIRouter(
    prefix="/leaves",
    tags=["Leave Requests"]
)
# 1. Place la fonction utilitaire juste avant ta route
def get_drh_id(db: Session) -> int:
    drh = db.query(models.Employee).filter(
        models.Employee.role == "HR",
        models.Employee.city == "Casablanca"
    ).first()
    return drh.employee_id if drh else None


# ── Submit a leave request (Employee) ────────────────────────────────────────
@router.post("/submit", response_model=LeaveRequestResponse)
def submit_leave(employee_id: int, request: LeaveRequestCreate, db: Session = Depends(get_db)):
    
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # --- NOUVELLE LOGIQUE DE WORKFLOW ---
    if employee.role == "Employee":
        initial_status = "Pending_Manager"
        assigned_manager = employee.manager_id

    elif employee.role == "Manager":
        initial_status = "Pending_HR"
        assigned_manager = employee.manager_id # Souvent NULL pour un Manager

    elif employee.role == "HR" and employee.city != "Casablanca":
        # HR de Rabat/Tanger -> Envoyé au DRH de Casa
        initial_status = "Pending_HR"
        assigned_manager = get_drh_id(db)

    elif employee.role == "HR" and employee.city == "Casablanca":
        # Le DRH de Casa s'auto-approuve
        initial_status = "Approved"
        assigned_manager = employee_id
    else:
        # Cas par défaut au cas où
        initial_status = "Pending_HR"
        assigned_manager = None

    # --- CRÉATION DE LA REQUÊTE ---
    new_request = models.LeaveRequest(
        employee_id      = employee_id,
        manager_id       = assigned_manager, # On utilise notre nouvelle variable
        leave_type       = request.leave_type,
        start_date       = request.start_date,
        end_date         = request.end_date,
        duration_days    = request.duration_days,
        status           = initial_status,
        submission_date  = date.today(),
        employee_comment = request.employee_comment 
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request
# ── Get my requests (Employee) ────────────────────────────────────────────────
@router.get("/my-requests/{employee_id}", response_model=List[LeaveRequestResponse])
def get_my_requests(employee_id: int, db: Session = Depends(get_db)):
    # Récupère l'année en cours de manière dynamique (2026)
    current_year = datetime.now().year
    
    # Filtre les requêtes de l'employé pour l'année en cours uniquement
    requests = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.start_date >= f"{current_year}-01-01",
        models.LeaveRequest.start_date <= f"{current_year}-12-31"
    ).all()
    
    return requests

# ── Get pending requests for manager ─────────────────────────────────────────
@router.get("/pending-manager/{manager_id}", response_model=List[LeaveRequestResponse])
def get_pending_for_manager(manager_id: int, db: Session = Depends(get_db)):
    requests = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.manager_id == manager_id,
        models.LeaveRequest.status == "Pending_Manager"
    ).all()
    return requests


from sqlalchemy import func
from datetime import datetime

# Assure-toi d'importer ta fonction : from .employees import get_real_solde

@router.get("/pending-hr/{city}")
def get_pending_for_hr(city: str, db: Session = Depends(get_db)):
    # 1. On récupère les demandes ET l'ID de l'employé
    results = db.query(
        models.LeaveRequest,
        models.Employee
    ).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.LeaveRequest.status == "Pending_HR",
        models.Employee.city == city
    ).all()
    
    formatted_requests = []
    current_year = datetime.now().year

    for leave, emp in results:
        # 2. Utilisation de la fonction centralisée ! 
        # Plus besoin de requête SQL ici, tout est dans get_real_solde
        solde_calcule = get_real_solde(emp.employee_id, current_year, db)

        # 3. Construction de la réponse
        formatted_requests.append({
            "request_id": leave.request_id,
            "employee_id": leave.employee_id,
            "leave_type": leave.leave_type,
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "duration_days": leave.duration_days,
            "status": leave.status,
            "submission_date": str(leave.submission_date) if leave.submission_date else "—",
            "employee_comment": leave.employee_comment if hasattr(leave, 'employee_comment') else "",
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "department": emp.department,
            "city": emp.city,
            "leave_balance_days": solde_calcule # ✅ Maintenant cohérent avec le reste
        })
        
    return formatted_requests

# ── Manager approves or rejects ───────────────────────────────────────────────
@router.put("/{request_id}/manager-decision")
def manager_decision(request_id: int, decision: str, comment: str = None, db: Session = Depends(get_db)):
    
    leave = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.request_id == request_id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if decision == "approve":
        leave.status = "Pending_HR"
    elif decision == "reject":
        leave.status = "Rejected"
    else:
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")
    
    if comment:
        leave.manager_comment = comment
    
    db.commit()
    db.refresh(leave)
    return {"message": f"Request {decision}d", "new_status": leave.status}

# ── HR final approval ─────────────────────────────────────────────────────────
@router.put("/{request_id}/hr-approve")
def hr_approve(request_id: int, db: Session = Depends(get_db)):
    
    leave = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.request_id == request_id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Update status to Approved
    leave.status = "Approved"

    # Deduct leave balance from employee (sync with AnnualBalance reality)
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == leave.employee_id
    ).first()

    if employee and leave.duration_days:

        # 1) Recalculate the real balance for the current year
        current_year = date.today().year
        real_balance = get_real_solde(leave.employee_id, current_year, db)

        # 2) Validate using the real balance
        if real_balance < int(leave.duration_days):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient leave balance. Available: {real_balance} days"
                )
            )

        # 3) Update employees table with the correct remaining balance
        employee.leave_balance_days = real_balance 

    # Génération automatique de la lettre de congé (après approbation HR)
    try:
        # dict employé (structure attendue par generate_lettre_conge)
        if employee:
            emp_dict = {
                "employee_id": employee.employee_id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "gender": employee.gender,
                "birth_date": employee.birth_date,
                "department": employee.department,
                "position": employee.position,
                "contract_type": employee.contract_type,
                "hire_date": employee.hire_date,
                "salary": float(employee.salary),
                "leave_balance_days": employee.leave_balance_days,
                "city": employee.city,
            }
        else:
            # sécurité: si employee est absent (normalement impossible)
            emp_dict = None

        leave_dict = {
            "leave_type": leave.leave_type,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "duration_days": leave.duration_days,
        }

        if emp_dict:
            file_path = generate_lettre_conge(emp_dict, leave_dict)
            leave.leave_file_path = file_path
    except Exception:
        # On ne bloque pas l'approbation si la génération échoue
        # (important pour un workflow simple et robuste)
        pass

    db.commit()
    db.refresh(leave)
    return {
        "message": "Leave request approved by HR",
        "request_id": request_id,
        "new_balance": employee.leave_balance_days if employee else None,
        "leave_file_path": leave.leave_file_path
    }


# ── Check team availability (for chatbot & UI) ────────────────────────────────────
@router.get("/team-availability/{department}")
def check_team_availability(
    department: str, 
    city: str,  
    start_date: date, 
    end_date: date, 
    db: Session = Depends(get_db)
):
    
    # Count how many people from this department AND city are on approved leave during these dates
    conflicts = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.department == department,
        models.Employee.city == city,  # 🏢 ADD THIS: Filter leaves by city
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= end_date,
        models.LeaveRequest.end_date >= start_date
    ).count()
    
    # Get total team size for this department AND city
    team_size = db.query(models.Employee).filter(
        models.Employee.department == department,
        models.Employee.city == city  # 🏢 ADD THIS: Filter total size by city
    ).count()
    
    return {
        "department": department,
        "city": city,
        "team_size": team_size,
        "absent_during_period": conflicts,
        "available": team_size - conflicts,
        "warning": conflicts >= 3
    }


# ── Upload medical certificate (Employee) ─────────────────────────────────
@router.get("/{request_id}/download-letter")
def download_letter(request_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    leave = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.request_id == request_id
    ).first()

    if not leave:
        raise HTTPException(status_code=404, detail="Request not found")

    if not leave.leave_file_path:
        raise HTTPException(status_code=404, detail="Leave letter not generated yet")

    file_path = leave.leave_file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/{request_id}/upload-certificate")
def upload_certificate(request_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):

    
    leave = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.request_id == request_id
    ).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Save file to files/certificates/ folder
    os.makedirs("files/certificates", exist_ok=True)
    file_path = f"files/certificates/certificate_{request_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update DB
    leave.certificate_file_path = file_path
    db.commit()
    
    return {
        "message": "Certificate uploaded successfully",
        "request_id": request_id,
        "file_path": file_path
    }