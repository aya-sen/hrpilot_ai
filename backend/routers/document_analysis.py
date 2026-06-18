import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from datetime import date
import fitz  # PyMuPDF
import json
import os
import shutil
from dotenv import load_dotenv
from sqlalchemy import or_, text as sql_text

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
    system_prompt = """Tu es un assistant spécialisé dans la qualification et l'analyse de documents RH marocains.
    
Analyse le document fourni et réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.

Format de réponse obligatoire:
{
  "document_type": "Type précis du document",
  "confidence": "High/Medium/Low",
  "extracted_data": {
    "employee_name": "nom complet détecté ou null",
    "start_date": "YYYY-MM-DD ou null",
    "end_date": "YYYY-MM-DD ou null", 
    "duration_days": nombre ou null,
    "purpose": "objet, poste cible, ou raison principale ou null",
    "doctor_name": "nom médecin ou null",
    "any_other_relevant_field": "éléments clés textuels extraits ou null"
  },
  "suggested_action": "create_leave_request / read_and_summarize",
  "summary": "résumé clair et métier de ce document (ex: CV de X pour le poste Y)"
}

Règles strictes pour "document_type" :
1. Sois dynamique et précis : Tu n'es pas limité à une liste fixe. Si le document est un accord de confidentialité, écris "Accord de confidentialité". Si c'est un rapport, écris "Rapport".
2. Différence cruciale entre CV et Lettre de Motivation :
   - Si le document est rédigé sous forme de lettre administrative (ex: "Objet: Candidature", "Madame, Monsieur", corps de texte), qualifie-le impérativement de "Lettre de motivation" ou "Lettre de candidature".
   - Ne le qualifie de "Curriculum Vitae (CV)" QUE s'il s'agit d'un profil structuré avec des listes d'expériences et de formations.

Règles pour "suggested_action":
- "create_leave_request" : Uniquement si le document implique directement un arrêt, une absence ou un congé médical (Certificat médical, Lettre de demande de congé).
- "read_and_summarize" : Pour TOUS les autres documents (CV, Lettre de motivation, Contrat, Bulletin de paie, etc.). L'objectif est d'informer le RH sans créer d'absence automatique.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Voici le contenu du document à analyser:\n\n{text[:3000]}")
    ]

    response = llm.invoke(messages)
    
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    return json.loads(content)



def find_employee_by_name(name: str, db: Session):
    if not name:
        return None

    # 1. Nettoyage : Supprimer les titres de civilité et ponctuation
    # On supprime Mme, M., Dr., Madame, Monsieur, etc.
    titles_pattern = r"\b(Mme|M\.|Madame|Monsieur|Dr\.|Mlle|Mr\.|M\b)"
    cleaned_name = re.sub(titles_pattern, "", name, flags=re.IGNORECASE)
    
    # 2. Découpage intelligent
    parts = cleaned_name.strip().split()
    if len(parts) < 2:
        return None

    # 3. Recherche flexible
    # On cherche le prénom et le nom indépendamment pour éviter les problèmes d'ordre
    first, last = parts[0], parts[-1]
    
    employee = db.query(models.Employee).filter(
        or_(
            # Cas 1 : Prénom et Nom dans l'ordre
            (models.Employee.first_name.ilike(f"%{first}%") & models.Employee.last_name.ilike(f"%{last}%")),
            # Cas 2 : Inversion (Nom Prénom)
            (models.Employee.first_name.ilike(f"%{last}%") & models.Employee.last_name.ilike(f"%{first}%"))
        )
    ).first()
    
    return employee
# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Upload and analyze a document (Secured with hr_city parameter) ───────────
@router.post("/upload")
def upload_and_analyze(
    file: UploadFile = File(...), 
    hr_city: str = Query(..., description="The city of the HR managing this profile"), 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    os.makedirs("files/uploads", exist_ok=True)
    temp_path = f"files/uploads/temp_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        text = extract_text_from_pdf(temp_path)
        
        if not text or len(text) < 20:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF. Make sure it's not a scanned image."
            )
        
        analysis = analyze_with_ai(text)

        # Extraction de l'employé si l'IA trouve un nom
        employee_name = analysis.get("extracted_data", {}).get("employee_name")
        matched_employee = find_employee_by_name(employee_name, db)
        
        print(f"DEBUG: Cherché nom: '{employee_name}', Trouvé: {matched_employee}")
        # SÉCURITÉ : Vérification de la restriction par ville si un employé connu est matché
        if matched_employee and matched_employee.city.lower() != hr_city.lower():
            return {
                "status": "security_restricted",
                "message": f"Employee found ('{matched_employee.first_name} {matched_employee.last_name}') but access is restricted. They belong to {matched_employee.city}, while your access scope is restricted to {hr_city}.",
                "document_type": analysis.get("document_type"),
                "suggested_action": "read_and_summarize"
            }

        prefilled_form = None
        # Déclenchement automatique de formulaire UNIQUEMENT pour les congés/certificats
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
        
        # Retour complet et unifié pour l'interface utilisateur
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
        raise HTTPException(status_code=500, detail="AI could not parse the document. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ── Confirm Leave Request ─────────────────────────────────────────────────────
@router.post("/confirm-leave")
def confirm_leave_from_analysis(payload: dict, db: Session = Depends(get_db)):
    employee_id = payload.get("employee_id")
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_leave = models.LeaveRequest(
        employee_id      = employee_id,
        manager_id       = employee.manager_id,
        leave_type       = payload.get("leave_type", "Sick"),
        start_date       = payload.get("start_date"),
        end_date         = payload.get("end_date"),
        duration_days    = int(payload.get("duration_days", 1)),
        status           = "Pending_Manager",
        submission_date  = date.today(),
        employee_comment = payload.get("employee_comment", "Créé via analyse documentaire IA")
    )
    
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    return {"message": "Leave request created successfully", "request_id": new_leave.request_id}

# ── Confirm Document Request ──────────────────────────────────────────────────
@router.post("/confirm-document")
def confirm_document_from_analysis(payload: dict, db: Session = Depends(get_db)):
    employee_id = payload.get("employee_id")
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    new_request = models.DocumentRequest(
        employee_id   = employee_id,
        document_type = payload.get("document_type", "Attestation de travail"),
        purpose       = payload.get("purpose", "Analyse documentaire IA"),
        status        = "Pending",
        request_date  = date.today()
    )
    db.add(new_request)
    db.commit()
    return {"message": "Document request logged successfully"}

# ── Import règlement intérieur ────────────────────────────────────────────────
@router.post("/import-rules")
def import_rules_from_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
    
    import os
    import shutil
    import json
    from sqlalchemy import text
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_groq import ChatGroq
    import time as python_time
    
    
    os.makedirs("files/uploads", exist_ok=True)
    temp_path = f"files/uploads/temp_rules_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extraction du texte du PDF
        text_content = extract_text_from_pdf(temp_path)
        
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
            HumanMessage(content=f"Règlement intérieur:\n\n{text_content[:4000]}")
        ]
        
        # ── INSTANCIATION LOCALE DU LLM POUR ÉVITER TOUT CONFLIT DE STR ──
        # Ici, on utilise un nom de variable unique (groq_llm) pour être sûr qu'aucun 'llm' global ne vienne interférer
        groq_llm = ChatGroq(
            temperature=0, 
            model_name="llama-3.3-70b-versatile"
        )
        
        response = None
        last_error = None
        delays = [1, 2, 4, 8, 16]
        
        for attempt, delay in enumerate(delays):
            try:
                response = groq_llm.invoke(messages)
                break  
            except Exception as e:
                last_error = e
                if attempt < len(delays) - 1:
                    python_time.sleep(delay)
                else:
                    raise HTTPException(
                        status_code=502, 
                        detail=f"Impossible de contacter l'IA après 5 essais. Erreur d'origine : {str(last_error)}"
                    )
        
        raw_content = response.content.strip()
        
        # Nettoyage des backticks Markdown éventuels
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
        
        try:
            rules_data = json.loads(raw_content.strip())
            rules = rules_data.get("rules", [])
        except (json.JSONDecodeError, TypeError, AttributeError):
            raise HTTPException(
                status_code=502, 
                detail="L'IA a renvoyé un format de réponse invalide. Veuillez réessayer."
            )
        
        # Vider la table de manière propre avec le mot-clé d'importation 'text'
        try:
            db.execute(text("TRUNCATE TABLE internal_rules"))
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("TRUNCATE TABLE internal_rule"))
            db.commit()
        
        inserted = 0
        for rule in rules:
            new_rule = models.InternalRule(
                category = rule.get("category", "Autre"),
                title    = rule.get("title", "Sans titre").strip(),
                content  = rule.get("content", "").strip()
            )
            db.add(new_rule)
            inserted += 1
        
        db.commit()
        
        return {
            "message": f"Successfully imported {inserted} rules",
            "rules_imported": inserted,
            "categories": list(set(r.get("category") for r in rules))
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)