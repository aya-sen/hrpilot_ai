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

    # 1. Get employee context
    employee_context = get_employee_context(employee_id, db)

    # 2. Get relevant rules
    relevant_rules = get_relevant_rules(message, db)

    # 3. Get employee info for department check
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # 4. Check team availability
    team_info = check_team_availability(employee.department, db)

    # 5. Build system prompt
    system_prompt = f"""Tu es HRPilot, un assistant RH intelligent pour la société TechServ Solutions.
Tu réponds en français, de manière professionnelle mais accessible.

DONNÉES DE L'EMPLOYÉ EN TEMPS RÉEL:
{employee_context}

DISPONIBILITÉ DE L'ÉQUIPE:
{team_info}

RÈGLEMENT INTÉRIEUR PERTINENT:
{relevant_rules}

INSTRUCTIONS IMPORTANTES:
1. Réponds uniquement en français
2. Base tes réponses sur les données réelles de l'employé ci-dessus
3. Si l'employé veut soumettre une demande de congé, réponds avec exactement ce format JSON:
   {{"action": "create_leave_request", "leave_type": "Annual", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "duration_days": N}}
4. Si l'employé veut une attestation ou document, réponds avec exactement ce format JSON:
   {{"action": "create_document_request", "document_type": "Attestation de travail", "purpose": "usage personnel"}}
5. Si tu détectes un risque de conflit d'équipe (beaucoup d'absences), avertis l'employé
6. Pour les questions simples, réponds directement en texte normal
7. Ne donne jamais d'informations sur d'autres employés
"""

    # 6. Build conversation history
    history = get_chat_history(employee_id, db)
    
    messages = [SystemMessage(content=system_prompt)]
    
    for h in history:
        messages.append(HumanMessage(content=h.message))
        messages.append(AIMessage(content=h.response))
    
    messages.append(HumanMessage(content=message))

    # 7. Call Groq API
    try:
        response = llm.invoke(messages)
        ai_response = response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")

    # 8. Check if response contains an action
    action_result = None
    import json

    if ai_response.strip().startswith("{") and '"action"' in ai_response:
        try:
            action_data = json.loads(ai_response.strip())
            action = action_data.get("action")

            if action == "create_leave_request":
                from datetime import date as date_type
                new_leave = models.LeaveRequest(
                    employee_id     = employee_id,
                    manager_id      = employee.manager_id,
                    leave_type      = action_data.get("leave_type", "Annual"),
                    start_date      = action_data.get("start_date"),
                    end_date        = action_data.get("end_date"),
                    duration_days   = action_data.get("duration_days"),
                    status          = "Pending_HR" if employee.role in ["Manager", "HR"] else "Pending_Manager",
                    submission_date = date_type.today()
                )
                db.add(new_leave)
                db.commit()
                action_result = "✅ Demande de congé soumise avec succès!"
                ai_response = f"Votre demande de congé a été soumise. {action_result}"

            elif action == "create_document_request":
                from datetime import date as date_type
                new_doc = models.DocumentRequest(
                    employee_id   = employee_id,
                    document_type = action_data.get("document_type"),
                    purpose       = action_data.get("purpose"),
                    status        = "Pending",
                    request_date  = date_type.today()
                )
                db.add(new_doc)
                db.commit()
                action_result = "✅ Demande de document soumise avec succès!"
                ai_response = f"Votre demande de document a été soumise. {action_result}"

        except json.JSONDecodeError:
            pass

    # 9. Save to chat history
    new_chat = models.ChatHistory(
        employee_id = employee_id,
        message     = message,
        response    = ai_response,
        timestamp   = datetime.now()
    )
    db.add(new_chat)
    db.commit()

    return {
        "employee_id":   employee_id,
        "message":       message,
        "response":      ai_response,
        "action_taken":  action_result,
        "timestamp":     datetime.now().isoformat()
    }