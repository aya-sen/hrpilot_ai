import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
import backend.models as models
from datetime import datetime, timedelta
from backend.routers.employees import get_real_solde 
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


def get_employee_context(employee_id: int, db: Session) -> str:
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()

    if not employee:
        return "Employé non trouvé."

    from datetime import datetime
    current_year = datetime.now().year
    
    # --- CHANGEMENT ICI ---
    # Utilise ta nouvelle fonction centralisée au lieu de refaire le calcul ici
    solde_current_year = get_real_solde(employee_id, current_year, db)
    # ----------------------

    pending_leaves = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status.in_(["Pending_Manager", "Pending_HR"])
    ).count()

    pending_docs = db.query(models.DocumentRequest).filter(
        models.DocumentRequest.employee_id == employee_id,
        models.DocumentRequest.status == "Pending"
    ).count()

    # 1. Infos privées de l'utilisateur connecté (Toujours incluses)
    context = f"""
            PROFIL DE L'EMPLOYÉ CONNECTÉ:
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

    # 2. SEULEMENT POUR RH ET MANAGER : Extraction de TOUTE la liste des effectifs de sa zone
    if employee.role in ["HR", "Manager"]:
        drh_id = get_drh_id(db)  # ID du vrai DRH trouvé dans la DB
        is_drh_global = (employee.employee_id == drh_id)

        query_staff = db.query(models.Employee)
        if not is_drh_global:
            # sinon, il ne voit que les employés de sa ville
            query_staff = query_staff.filter(models.Employee.city == employee.city)

        all_staff = query_staff.all()
        
        # Construction d'un tableau texte brut de TOUS les employés pour que l'IA puisse répondre à TOUT
        staff_list_text = ""
        for emp in all_staff:
            staff_list_text += f"- {emp.first_name} {emp.last_name} | Poste: {emp.position} | Dept: {emp.department} | Contrat: {emp.contract_type} | Ville: {emp.city} | Salaire: {emp.salary} MAD | Statut: {emp.status}\n"

        context += f"""
                    [ACCÈS AUTORISÉ RH/MANAGER - LISTE COMPLÈTE DES EFFECTIFS SOUS VOTRE GESTION]
                    {staff_list_text}
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

# ── Check team availability (Sécurisée et flexible) ───────────────────────────
def check_team_availability(department: str, city: str, db: Session, start_date: str = None, end_date: str = None) -> str:
    
    # 1. On prépare la requête de base
    query = db.query(models.LeaveRequest).join(
        models.Employee,
        models.LeaveRequest.employee_id == models.Employee.employee_id
    ).filter(
        models.Employee.department == department,
        models.Employee.city       == city,
        models.LeaveRequest.status == "Approved"
    )
    
    # 2. On applique le filtre de dates UNIQUEMENT si elles sont fournies
    if start_date and end_date:
        query = query.filter(
            models.LeaveRequest.start_date <= end_date,
            models.LeaveRequest.end_date   >= start_date
        )
        period_text = "en cours sur cette période"
    else:
        # Si pas de dates (comme au premier message), on regarde le jour même en 2026
        from datetime import date
        today_str = date.today().isoformat()
        query = query.filter(
            models.LeaveRequest.start_date <= today_str,
            models.LeaveRequest.end_date   >= today_str
        )
        # 💡 REMPLACE "aujourd'hui" PAR "actuellement" ou "sur la période en cours"
        period_text = "sur la période en cours"

    approved_absences = query.count()

    team_size = db.query(models.Employee).filter(
        models.Employee.department == department,
        models.Employee.city       == city
    ).count()

    if team_size == 0:
        return f"Vous êtes le seul membre de {department} à {city}."

    return (
        f"Le département {department} à {city} compte actuellement {team_size} membres, "
        f"avec {approved_absences} absence(s) approuvée(s) {period_text}."
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
    team_info = check_team_availability(
        department=employee.department, 
        city=employee.city, 
        db=db
    )

    # Récupérer la date du jour de manière dynamique
    today_str = datetime.now().strftime("%A %d %B %Y")  # ex: "Tuesday 02 June 2026"
    today_iso = datetime.now().date().isoformat()       # ex: "2026-06-02"
    # 5. Build system prompt
    role_security_instruction = ""
    if employee.role not in ["HR", "Manager"]:
        role_security_instruction = """
        [CONSIGNE DE CONFIDENTIALITÉ STRICTE] : Tu t'adresses à un employé standard. Tu as interdiction absolue de lui parler des autres employés, de donner leurs noms, leurs contrats, ou de confirmer qui travaille dans l'entreprise. S'il te demande des informations générales sur les effectifs ou sur d'autres personnes, refuse poliment en disant que tu es son assistant personnel et que ces données sont confidentielles.
        """
    else:
        role_security_instruction = """
        [ACCÈS AUTORISÉ DIRECTION/RH] : Tu t'adresses à un gestionnaire (RH ou Manager). Tu es son outil d'aide à la décision. Utilise la "LISTE COMPLÈTE DES EFFECTIFS" fournie dans le contexte pour répondre à toutes ses questions (statistiques, listes, conseils de management, salaires, profils).
        """

    system_prompt = f"""{role_security_instruction}
    Tu es HRPilot, un assistant RH expert pour la société TechServ Solutions.
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
            - Si l'employé connecté parle de sa propre situation, rappelle-lui toujours son solde actuel (ex: "Il vous reste 17 jours..."). S'il s'agit d'un RH/Manager qui demande des informations sur un tiers, ne mentionne pas le solde de l'interlocuteur connecté.
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
            - Document : {{"action": "create_document_request", "document_type": "Attestation de travail", "purpose": "usage personnel"}}
            - Document de salaire : {{"action": "create_document_request", "document_type": "Attestation de salaire", "purpose": "usage personnel"}}
            - Bulletin de paie : {{"action": "create_document_request", "document_type": "Bulletin de paie", "purpose": "usage personnel"}}
            - Certificat de travail : {{"action": "create_document_request", "document_type": "Certificat de travail", "purpose": "usage personnel"}}

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
        error_message = str(e)
        if "429" in error_message or "rate limit" in error_message.lower():
            print(f"GROQ RATE LIMIT DETAIL: {error_message}")  # ← ajoute cette ligne temporairement
            raise HTTPException(
                status_code=429,
                detail="Le service est temporairement surchargé, veuillez réessayer dans quelques instants."
            )
        raise HTTPException(status_code=500, detail=f"AI error: {error_message}")
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
                document_type=action_data.get("document_type", "Attestation de travail").strip(),
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
                    drh_id = get_drh_id(db)
                    assigned_manager_id = drh_id if drh_id else employee.manager_id

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
                start_date      = start_date_final,  
                end_date        = end_date_final,
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

