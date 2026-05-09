from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from datetime import date
import fitz  # PyMuPDF
import json
import os
import shutil
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

router = APIRouter(
    prefix="/analysis",
    tags=["Document Analysis"]
)

# ── Initialize LLM ────────────────────────────────────────────────────────────
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    temperature=0.1  # Low temperature for precise extraction
)

# ── Extract text from PDF ─────────────────────────────────────────────────────
def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()

# ── Analyze document with AI ──────────────────────────────────────────────────
def analyze_with_ai(text: str) -> dict:
    system_prompt = """Tu es un assistant spécialisé dans l'analyse de documents RH marocains.
    
Analyse le document fourni et réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.

Format de réponse obligatoire:
{
  "document_type": "type du document",
  "confidence": "High/Medium/Low",
  "extracted_data": {
    "employee_name": "nom complet ou null",
    "start_date": "YYYY-MM-DD ou null",
    "end_date": "YYYY-MM-DD ou null", 
    "duration_days": nombre ou null,
    "purpose": "objet/raison ou null",
    "doctor_name": "nom médecin ou null",
    "salary_amount": nombre ou null,
    "any_other_relevant_field": "valeur ou null"
  },
  "suggested_action": "create_leave_request / create_document_request / manual_handling",
  "summary": "résumé en 2 phrases de ce document"
}

Types de documents possibles:
- Certificat médical
- Demande de congé
- Attestation de travail
- Attestation de salaire  
- Contrat de travail
- Document juridique
- Formulaire RH
- Document non reconnu
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Voici le contenu du document à analyser:\n\n{text[:3000]}")
    ]

    response = llm.invoke(messages)
    
    # Clean response and parse JSON
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    return json.loads(content)

# ── Find employee by name ─────────────────────────────────────────────────────
def find_employee_by_name(name: str, db: Session):
    if not name:
        return None
    
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    
    # Try different combinations
    employee = db.query(models.Employee).filter(
        models.Employee.first_name.ilike(f"%{parts[0]}%"),
        models.Employee.last_name.ilike(f"%{parts[-1]}%")
    ).first()
    
    if not employee:
        # Try reversed (last name first)
        employee = db.query(models.Employee).filter(
            models.Employee.first_name.ilike(f"%{parts[-1]}%"),
            models.Employee.last_name.ilike(f"%{parts[0]}%")
        ).first()
    
    return employee

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Upload and analyze a document ─────────────────────────────────────────────
@router.post("/upload")
def upload_and_analyze(file: UploadFile = File(...), db: Session = Depends(get_db)):
    
    # Check file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Save uploaded file temporarily
    os.makedirs("files/uploads", exist_ok=True)
    temp_path = f"files/uploads/temp_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(temp_path)
        
        if not text or len(text) < 20:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. Make sure it's not a scanned image."
            )
        
        # Analyze with AI
        analysis = analyze_with_ai(text)
        
        # Try to find matching employee
        employee_name = analysis.get("extracted_data", {}).get("employee_name")
        matched_employee = find_employee_by_name(employee_name, db)
        
        # Build pre-filled form based on suggested action
        prefilled_form = None
        
        if analysis.get("suggested_action") == "create_leave_request" and matched_employee:
            prefilled_form = {
                "type": "leave_request",
                "employee_id": matched_employee.employee_id,
                "employee_name": f"{matched_employee.first_name} {matched_employee.last_name}",
                "leave_type": "Sick" if "médical" in analysis.get("document_type","").lower() else "Annual",
                "start_date": analysis["extracted_data"].get("start_date"),
                "end_date": analysis["extracted_data"].get("end_date"),
                "duration_days": analysis["extracted_data"].get("duration_days"),
                "employee_comment": analysis["extracted_data"].get("purpose", "Document analysé par IA")
            }
        
        elif analysis.get("suggested_action") == "create_document_request" and matched_employee:
            prefilled_form = {
                "type": "document_request",
                "employee_id": matched_employee.employee_id,
                "employee_name": f"{matched_employee.first_name} {matched_employee.last_name}",
                "document_type": analysis.get("document_type"),
                "purpose": analysis["extracted_data"].get("purpose", "Extrait depuis document")
            }
        
        return {
            "status": "success",
            "document_type": analysis.get("document_type"),
            "confidence": analysis.get("confidence"),
            "summary": analysis.get("summary"),
            "extracted_data": analysis.get("extracted_data"),
            "matched_employee": {
                "employee_id": matched_employee.employee_id,
                "name": f"{matched_employee.first_name} {matched_employee.last_name}",
                "department": matched_employee.department,
                "city": matched_employee.city
            } if matched_employee else None,
            "suggested_action": analysis.get("suggested_action"),
            "prefilled_form": prefilled_form
        }
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="AI could not parse the document. Please try again."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ── Confirm and save extracted data ───────────────────────────────────────────
@router.post("/confirm-leave")
def confirm_leave_from_analysis(
    employee_id: int,
    leave_type: str,
    start_date: str,
    end_date: str,
    duration_days: int,
    employee_comment: str = None,
    db: Session = Depends(get_db)
):
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_leave = models.LeaveRequest(
        employee_id      = employee_id,
        manager_id       = employee.manager_id,
        leave_type       = leave_type,
        start_date       = start_date,
        end_date         = end_date,
        duration_days    = duration_days,
        status           = "Pending_HR",  # Sick cert goes straight to HR
        submission_date  = date.today(),
        employee_comment = employee_comment or "Créé via analyse documentaire IA"
    )
    
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    
    return {
        "message": "Leave request created from document analysis",
        "request_id": new_leave.request_id,
        "employee": f"{employee.first_name} {employee.last_name}",
        "status": "Pending_HR"
    }

# ── Import règlement intérieur ────────────────────────────────────────────────
@router.post("/import-rules")
def import_rules_from_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")
    
    os.makedirs("files/uploads", exist_ok=True)
    temp_path = f"files/uploads/temp_rules_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract text
        text = extract_text_from_pdf(temp_path)
        
        # Ask AI to extract rules
        system_prompt = """Tu es un expert RH. Extrait les règles du règlement intérieur fourni.
Réponds UNIQUEMENT avec un JSON valide:
{
  "rules": [
    {
      "category": "Congés/Absences/Horaires/Télétravail/Documents/Autre",
      "title": "titre court de la règle",
      "content": "contenu complet de la règle"
    }
  ]
}
Extrait maximum 20 règles les plus importantes."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Règlement intérieur:\n\n{text[:4000]}")
        ]
        
        response = llm.invoke(messages)
        content = response.content.strip()
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        rules_data = json.loads(content.strip())
        rules = rules_data.get("rules", [])
        
        # Clear existing rules and insert new ones
        db.query(models.InternalRule).delete()
        
        inserted = 0
        for rule in rules:
            new_rule = models.InternalRule(
                category = rule.get("category", "Autre"),
                title    = rule.get("title", "Sans titre"),
                content  = rule.get("content", "")
            )
            db.add(new_rule)
            inserted += 1
        
        db.commit()
        
        return {
            "message": f"Successfully imported {inserted} rules",
            "rules_imported": inserted,
            "categories": list(set(r.get("category") for r in rules))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)