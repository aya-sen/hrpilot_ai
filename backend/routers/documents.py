import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import DocumentRequestCreate, DocumentRequestResponse
import backend.models as models
from typing import List
from datetime import date

from backend.document_generator import (
    generate_attestation_travail,
    generate_attestation_salaire,
    generate_lettre_conge,
    generate_bulletin_paie,
    generate_certificat_travail
)

router = APIRouter(
    prefix="/documents",
    tags=["Document Requests"]
)

# ── Submit a document request (Employee) ──────────────────────────────────────
@router.post("/submit", response_model=DocumentRequestResponse)
def submit_document_request(employee_id: int, request: DocumentRequestCreate, db: Session = Depends(get_db)):
    
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_request = models.DocumentRequest(
        employee_id   = employee_id,
        document_type = request.document_type,
        purpose       = request.purpose,
        status        = "Pending",
        request_date  = date.today()
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

# ── Get my document requests (Employee) ───────────────────────────────────────
@router.get("/my-requests/{employee_id}", response_model=List[DocumentRequestResponse])
def get_my_doc_requests(employee_id: int, db: Session = Depends(get_db)):
    requests = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.employee_id == employee_id
    ).all()
    return requests

# ── Get all pending document requests (HR) ────────────────────────────────────
@router.get("/pending/{city}", response_model=List[DocumentRequestResponse])
def get_pending_documents(city: str, db: Session = Depends(get_db)):
    # On fait une jointure avec Employee pour filtrer par ville
    requests = db.query(models.DocumentRequest).join(models.Employee).filter(
        models.DocumentRequest.status == "Pending",
        models.Employee.city == city
    ).all()
    return requests

# ── Get all document requests for a specific city (HR) ────────────────────────
@router.get("/all/{city}", response_model=List[DocumentRequestResponse])
def get_all_documents(city: str, db: Session = Depends(get_db)):
    # On lie les deux tables pour filtrer par la ville de l'employé
    requests = db.query(models.DocumentRequest).join(models.Employee).filter(
        models.Employee.city == city
    ).all()
    
    return requests

# ── Generate document (HR) ────────────────────────────────────────────────────
@router.put("/{doc_request_id}/generate")
def generate_document(doc_request_id: int, db: Session = Depends(get_db)):
    
    doc_request = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.doc_request_id == doc_request_id
    ).first()
    
    if not doc_request:
        raise HTTPException(status_code=404, detail="Document request not found")
    
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == doc_request.employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Convert employee to dict
    emp_dict = {
        "employee_id":  employee.employee_id,
        "first_name":   employee.first_name,
        "last_name":    employee.last_name,
        "gender":       employee.gender,
        "birth_date":   employee.birth_date,
        "department":   employee.department,
        "position":     employee.position,
        "contract_type": employee.contract_type,
        "hire_date":    employee.hire_date,
        "salary":       float(employee.salary),
        "leave_balance_days": employee.leave_balance_days,
        "city":         employee.city,
    }
    
    # Generate based on document type
    doc_type = doc_request.document_type
    
    try:
        if doc_type == "Attestation de travail":
            file_path = generate_attestation_travail(emp_dict)
            
        elif doc_type == "Attestation de salaire":
            file_path = generate_attestation_salaire(
                emp_dict,
                objet=doc_request.purpose or "usage personnel"
            )
            
        elif doc_type == "Lettre de congé":
            # Find the related approved leave request
            leave = db.query(models.LeaveRequest).filter(
                models.LeaveRequest.employee_id == employee.employee_id,
                models.LeaveRequest.status == "Approved"
            ).order_by(models.LeaveRequest.request_id.desc()).first()
            
            if not leave:
                raise HTTPException(status_code=404, detail="No approved leave found")
            
            leave_dict = {
                "leave_type":    leave.leave_type,
                "start_date":    leave.start_date,
                "end_date":      leave.end_date,
                "duration_days": leave.duration_days,
            }
            file_path = generate_lettre_conge(emp_dict, leave_dict)
            
        elif doc_type == "Bulletin de paie":
            
            today = date.today()
            months = ['Janvier','Février','Mars','Avril','Mai','Juin',
                     'Juillet','Août','Septembre','Octobre','Novembre','Décembre']
            file_path = generate_bulletin_paie(
                emp_dict,
                month=months[today.month - 1],
                year=today.year
            )
            
        elif doc_type == "Certificat de travail":
            
            file_path = generate_certificat_travail(
                emp_dict,
                end_date=str(date.today())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{doc_type}' not supported"
            )
            
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Update DB
    doc_request.status              = "Generated"
    doc_request.generated_file_path = file_path
    doc_request.delivery_date       = date.today()
    
    db.commit()
    
    return {
        "message":       "Document generated successfully",
        "document_type": doc_type,
        "employee":      f"{employee.first_name} {employee.last_name}",
        "file_path":     file_path,
        "status":        "Generated"
    }

# ── Update status to Delivered ────────────────────────────────────────────────
@router.put("/{doc_request_id}/deliver")
def deliver_document(doc_request_id: int, db: Session = Depends(get_db)):
    
    doc_request = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.doc_request_id == doc_request_id
    ).first()
    
    if not doc_request:
        raise HTTPException(status_code=404, detail="Document request not found")
    
    doc_request.status        = "Delivered"
    doc_request.delivery_date = date.today()
    
    db.commit()
    return {"message": "Document marked as delivered", "doc_request_id": doc_request_id}

@router.get("/{doc_request_id}/download")
def download_document(doc_request_id: int, db: Session = Depends(get_db)):
    
    doc_request = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.doc_request_id == doc_request_id
    ).first()
    
    if not doc_request:
        raise HTTPException(status_code=404, detail="Document request not found")
    
    if not doc_request.generated_file_path:
        raise HTTPException(status_code=404, detail="Document not generated yet")
    
    file_path = doc_request.generated_file_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path        = file_path,
        filename    = os.path.basename(file_path),
        media_type  = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )