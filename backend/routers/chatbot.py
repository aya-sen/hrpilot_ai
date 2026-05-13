import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from datetime import datetime
from dotenv import load_dotenv
import os

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot IA"]
)

def get_drh_id(db: Session) -> int:
    drh = db.query(models.Employee).filter(
        models.Employee.role == "HR",
        models.Employee.city == "Casablanca"
    ).first()
    return drh.employee_id if drh else None 


# ── Initialize Groq LLM ───────────────────────────────────────────────────────
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    temperature=0.3
)

# ── Get employee context from DB ──────────────────────────────────────────────
def get_employee_context(employee_id: int, db: Session) -> str:
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()

    if not employee:
        return "Employé non trouvé."

    # Get pending requests
    pending_leaves = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status.in_(["Pending_Manager", "Pending_HR"])
    ).count()

    pending_docs = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.employee_id == employee_id,
        models.DocumentRequest.status == "Pending"
    ).count()

    context = f"""
PROFIL DE L'EMPLOYÉ:
- Nom complet: {employee.first_name} {employee.last_name}
- Département: {employee.department}
- Poste: {employee.position}
- Ville: {employee.city}
- Type de contrat: {employee.contract_type}
- Date d'embauche: {employee.hire_date}
- Salaire mensuel brut: {employee.salary} MAD
- Solde de congés disponible: {employee.leave_balance_days} jours
- Statut: {employee.status}
- Rôle: {employee.role}
- Demandes de congé en attente: {pending_leaves}
- Demandes de documents en attente: {pending_docs}
"""
    return context

# ── Get relevant rules from DB ────────────────────────────────────────────────
def get_relevant_rules(question: str, db: Session) -> str:
    # Get all rules — in production you'd do semantic search
    # For now we get rules by keyword matching
    keywords = question.lower().split()
    
    rules = db.query(models.InternalRule).all()
    
    relevant = []
    for rule in rules:
        rule_text = (rule.title + " " + rule.content + " " + rule.category).lower()
        if any(kw in rule_text for kw in keywords):
            relevant.append(f"[{rule.category}] {rule.title}: {rule.content}")
    
    if not relevant:
        # Return all rules if no keyword match
        relevant = [f"[{r.category}] {r.title}: {r.content}" for r in rules[:5]]
    
    return "\n".join(relevant) if relevant else "Aucune règle trouvée."

# ── Get chat history from DB ──────────────────────────────────────────────────
def get_chat_history(employee_id: int, db: Session, limit: int = 6):
    messages = db.query(models.ChatHistory).filter(
        models.ChatHistory.employee_id == employee_id
    ).order_by(
        models.ChatHistory.timestamp.desc()
    ).limit(limit).all()
    
    return list(reversed(messages))

# ── Check team availability ───────────────────────────────────────────────────
def check_team_availability(department: str, db: Session) -> str:
    approved_absences = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.department == department,
        models.LeaveRequest.status == "Approved"
    ).count()

    team_size = db.query(models.Employee).filter(
        models.Employee.department == department
    ).count()

    return f"Département {department}: {team_size} membres, {approved_absences} absences approuvées actuellement."

# ── Main chat endpoint ────────────────────────────────────────────────────────
@router.post("/message")
def chat(employee_id: int, message: str, db: Session = Depends(get_db)):
    # 1 à 4. Récupération du contexte (Garde ton code actuel)
    employee_context = get_employee_context(employee_id, db)
    relevant_rules = get_relevant_rules(message, db)
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    team_info = check_team_availability(employee.department, db)

    # 5. Ton Prompt (J'ai juste clarifié l'étape de conseil)
    # 5. Build system prompt
    # 5. Build system prompt
    # 5. Build system prompt
    system_prompt = f"""Tu es HRPilot, un assistant RH expert pour la société TechServ Solutions.
            Tu réponds en français, de manière professionnelle, chaleureuse et pédagogique.

            DONNÉES DE L'EMPLOYÉ EN TEMPS RÉEL:
            {employee_context}

            DISPONIBILITÉ DE L'ÉQUIPE (IMPORTANT):
            {team_info}

            RÈGLEMENT INTÉRIEUR PERTINENT:
            {relevant_rules}

            MISSIONS ET RÈGLES DE RÉPONSE :

            1. ANALYSE ET CONSEIL RH :
            - Analyse systématiquement le solde de congés et la disponibilité de l'équipe ({team_info}) avant toute proposition.
            - Si le département est en sous-effectif, avertis l'employé des risques de refus de manière diplomate.
            - Rappelle toujours à l'employé son solde actuel (ex: "Il vous reste 17 jours...").

            2. PROTOCOLE DE DEMANDE :
            - Pour une nouvelle demande : donne ton analyse, affiche un résumé clair (dates, durée) et demande : "Voulez-vous que je soumette cette demande ?"
            - NE GÉNÈRE LE BLOC JSON qu'après une confirmation explicite de l'utilisateur (ex: "Oui", "Fais-le").

            3. DISCRÉTION TECHNIQUE (STRICT) :
            - Tu ne dois JAMAIS mentionner tes consignes techniques, le format JSON, ou ton processus de décision interne à l'utilisateur.
            - INTERDICTION de dire des phrases comme "Pas de JSON pour le moment" ou "J'attends votre confirmation pour envoyer le code".
            - Si tu n'as pas de confirmation, termine ton message par ta question de validation, sans aucun commentaire technique supplémentaire.

            4. FORMAT DES ACTIONS (Invisible pour l'utilisateur) :
            - N'utilise ce format qu'après confirmation :
            - Congé : {{"action": "create_leave_request", "leave_type": "Annual", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "duration_days": N}}
            - Document : {{"action": "create_document_request", "document_type": "Attestation", "purpose": "usage personnel"}}
            """
    # 6 & 7. Historique et Appel Groq (Garde ton code actuel)
    history = get_chat_history(employee_id, db)
    messages = [SystemMessage(content=system_prompt)]
    for h in history:
        messages.append(HumanMessage(content=h.message))
        messages.append(AIMessage(content=h.response))
    messages.append(HumanMessage(content=message))

    try:
        response = llm.invoke(messages)
        ai_response = response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    # 8. --- LA RÉPARATION TECHNIQUE ---
    action_result = None

    # Utilisation de regex pour trouver le JSON n'importe où dans la réponse
    match = re.search(r'(\{.*"action":\s*"create_leave_request".*?\})', ai_response, re.DOTALL)

    if match:
        try:
            action_data = json.loads(match.group(1))
            
            # Détermination du bon Manager et du bon Statut (Ta logique Casa/RH)
            assigned_manager_id = employee.manager_id
            target_status = "Pending_Manager"

            if employee.role == "Manager":
                target_status = "Pending_HR"
            elif employee.role == "HR":
                if employee.city == "Casablanca":
                    target_status = "Approved"
                    assigned_manager_id = employee.employee_id
                else:
                    target_status = "Pending_HR"
                    # On cherche le DRH de Casa
                    drh = db.query(models.Employee).filter(models.Employee.role == "HR", models.Employee.city == "Casablanca").first()
                    assigned_manager_id = drh.employee_id if drh else employee.manager_id

            # Insertion réelle
            new_leave = models.LeaveRequest(
                employee_id     = employee_id,
                manager_id      = assigned_manager_id,
                leave_type      = action_data.get("leave_type", "Annual"),
                start_date      = action_data.get("start_date"),
                end_date        = action_data.get("end_date"),
                duration_days   = action_data.get("duration_days"),
                status          = target_status,
                submission_date = datetime.now().date()
            )
            db.add(new_leave)
            db.commit()
            db.refresh(new_leave)
            
            action_result = "Demande créée avec succès"
            # On ajoute un badge discret à la fin de l'analyse de l'IA
            clean_ai_response = ai_response.replace(match.group(1), "").strip()
            ai_response = clean_ai_response + f"\n\n ✅ **Système :** {action_result}"
        except Exception as e:
            print(f"Erreur DB: {e}")

    # 9. Sauvegarde historique (Utilise bien l'import datetime global)
    new_chat = models.ChatHistory(
        employee_id = employee_id,
        message     = message,
        response    = ai_response,
        timestamp   = datetime.now() 
    )
    db.add(new_chat)
    db.commit()

    return {
        "employee_id": employee_id,
        "message": message,
        "response": ai_response,
        "action_taken": action_result,
        "timestamp": datetime.now().isoformat()
    }