from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import DocumentRequestCreate, DocumentRequestResponse
import backend.models as models
from typing import List
from datetime import date

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
@router.get("/pending", response_model=List[DocumentRequestResponse])
def get_pending_documents(db: Session = Depends(get_db)):
    requests = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.status == "Pending"
    ).all()
    return requests

# ── Get all document requests (HR) ───────────────────────────────────────────
@router.get("/all", response_model=List[DocumentRequestResponse])
def get_all_documents(db: Session = Depends(get_db)):
    requests = db.query(models.DocumentRequest).all()
    return requests

# ── Generate document (HR) ────────────────────────────────────────────────────
@router.put("/{doc_request_id}/generate")
def generate_document(doc_request_id: int, db: Session = Depends(get_db)):
    
    doc_request = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.doc_request_id == doc_request_id
    ).first()
    
    if not doc_request:
        raise HTTPException(status_code=404, detail="Document request not found")
    
    # Get employee data
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == doc_request.employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Generate file path (actual generation comes in Week 3)
    file_name = f"files/{doc_request.document_type.replace(' ', '_')}_{employee.employee_id}_{date.today()}.docx"
    
    # Update request status and file path
    doc_request.status               = "Generated"
    doc_request.generated_file_path  = file_name
    doc_request.delivery_date        = date.today()
    
    db.commit()
    db.refresh(doc_request)
    
    return {
        "message": "Document generated successfully",
        "doc_request_id": doc_request_id,
        "employee": f"{employee.first_name} {employee.last_name}",
        "document_type": doc_request.document_type,
        "file_path": file_name,
        "status": "Generated"
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