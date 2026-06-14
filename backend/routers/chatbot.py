import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from datetime import datetime, timedelta
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

    # ── 🛠️ QUICK PROTOTYPE FIX FOR CHATBOT BALANCE ──
    from datetime import datetime
    current_year = datetime.now().year
    
    # Calculate approved days taken ONLY in 2026
    approved_leaves_this_year = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date >= f"{current_year}-01-01",
        models.LeaveRequest.end_date <= f"{current_year}-12-31"
    ).all()
    
    days_taken_this_year = sum(int(l.duration_days or 0) for l in approved_leaves_this_year)
    
    # Force the baseline allocation to 18 to match home/profile interfaces
    LEGAL_BASE_ALLOCATION = 18
    solde_current_year = max(LEGAL_BASE_ALLOCATION - days_taken_this_year, 0)
    # ────────────────────────────────────────────────

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
- Solde de congés disponible: {solde_current_year} jours
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
def check_team_availability(department: str, city: str, db: Session) -> str:
    
    # Count approved absences in same dept AND same city
    approved_absences = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.department == department,
        models.Employee.city       == city,        # ← ADD THIS
        models.LeaveRequest.status == "Approved"
    ).count()

    team_size = db.query(models.Employee).filter(
        models.Employee.department == department,
        models.Employee.city       == city          # ← ADD THIS
    ).count()

    if team_size == 0:
        return f"Vous êtes le seul membre de {department} à {city}."

    return (
        f"Département {department} à {city} : "
        f"{team_size} membres, "
        f"{approved_absences} absence(s) approuvée(s) actuellement."
    )
# ── Main chat endpoint ────────────────────────────────────────────────────────
@router.post("/message")
def chat(employee_id: int, message: str, db: Session = Depends(get_db)):
    # 1 à 4. Récupération du contexte (Garde ton code actuel)
    employee_context = get_employee_context(employee_id, db)
    relevant_rules = get_relevant_rules(message, db)
    employee = db.query(models.Employee).filter(models.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    team_info = check_team_availability(employee.department, employee.city, db)

    # Récupérer la date du jour de manière dynamique
    today_str = datetime.now().strftime("%A %d %B %Y")  # ex: "Tuesday 02 June 2026"
    today_iso = datetime.now().date().isoformat()       # ex: "2026-06-02"
    # 5. Build system prompt
    system_prompt = f"""Tu es HRPilot, un assistant RH expert pour la société TechServ Solutions.
            Tu réponds en français, de manière professionnelle, chaleureuse et pédagogique.

            CONTEXTE TEMPOREL ACTUEL (CRUCIAL) :
            - Aujourd'hui nous sommes le : {today_str}
            - Date actuelle au format ISO : {today_iso}
            - Tu dois utiliser cette date actuelle comme unique base de référence pour calculer TOUTES les dates relatives mentionnées par l'employé (ex: "demain", "la semaine prochaine" , ...). Convertis-les toujours en dates réelles au format 'YYYY-MM-DD' calculées par rapport à {today_iso}.
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
            - CAS SPÉCIFIQUE CONGÉ MALADIE (Sick Leave) : Précise obligatoirement à l'employé qu'un certificat est requis en disant : "Je peux préparer votre demande de congé maladie. Cependant, n'oubliez pas qu'un certificat médical est obligatoire, n'oubliez pas de l'envoyer à votre manager."
            2. PROTOCOLE DE DEMANDE :
            - Pour une nouvelle demande : donne ton analyse, affiche un résumé clair (dates, durée).
            - NE GÉNÈRE LE BLOC JSON qu'après une confirmation explicite de l'utilisateur (ex: "Oui", "Fais-le").

            
            3. DISCRÉTION TECHNIQUE ET VOCABULAIRE INTERDIT (STRICT) :
            - Tu es une application grand public : tu ne dois JAMAIS utiliser de jargon de programmation ou d'informatique avec l'utilisateur.
            - Il est STRICTEMENT INTERDIT de prononcer les mots : "JSON", "bloc", "code", "action", "format", "backend" ou "générer".
            - Ne parle jamais de ton fonctionnement interne ou des étapes de traitement de ta base de données.
            - Reste concentré uniquement sur la conversation humaine (demander les dates, valider, conseiller).
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
    match_doc = re.search(r'(\{.*"action":\s*"create_document_request".*?\})', ai_response, re.DOTALL)

    if match_doc:
        try:
            action_data = json.loads(match_doc.group(1))

            new_request = models.DocumentRequest(
                employee_id=employee_id,
                document_type=action_data.get("document_type", "Attestation de travail"),
                purpose=action_data.get("purpose", "Analyse documentaire IA"),
                status="Pending",
                request_date=datetime.now().date(),
            )

            db.add(new_request)
            db.commit()
            db.refresh(new_request)

            action_result = "Demande de document créée avec succès"
            clean_ai_response = ai_response.replace(match_doc.group(1), "").strip()
            ai_response = clean_ai_response + f"\n\n ✅ **Système :** {action_result}"
        except Exception as e:
            print(f"Erreur DB (document request): {e}")

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

            # ── DEBUT DE LA SÉCURITÉ DES DATES (COLLE LE BLOC ICI) ───────────
            try:
                start_date_final = datetime.strptime(action_data.get("start_date"), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                start_date_final = datetime.now().date() + timedelta(days=1)

            try:
                end_date_final = datetime.strptime(action_data.get("end_date"), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                duration = int(action_data.get("duration_days", 1))
                end_date_final = start_date_final + timedelta(days=duration)
            # ── FIN DE LA SÉCURITÉ DES DATES ──────────────────────────────────

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

