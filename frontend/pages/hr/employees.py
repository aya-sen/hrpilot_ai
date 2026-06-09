import streamlit as st
from utils.api import get_all_employees, get_employee, update_employee_status

# ── 1. DIALOG MODAL FUNCTION ──────────────────────────────────────────────────
# This decorator creates a clean popup window when the user clicks "Modifier"
@st.dialog("Modifier l'employé")
def edit_employee_dialog(emp):
    st.markdown(f"⚙️ Modification de **{emp['first_name']} {emp['last_name']}**")
    st.divider()
    
    new_status = st.selectbox(
        "Statut",
        ["Active", "On leave", "Resigned"],
        index=["Active", "On leave", "Resigned"].index(emp.get("status", "Active"))
    )
    new_phone = st.text_input("Téléphone", value=emp.get("phone_number") or "")
    new_salary = st.number_input("Salaire (MAD)", value=float(emp.get("salary") or 0), step=500.0)
    new_balance = st.number_input("Solde congés (jours)", value=int(emp.get("leave_balance_days") or 28), step=1)
    new_position = st.text_input("Poste", value=emp.get("position") or "")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(":material/save: Enregistrer", use_container_width=True, type="primary"):
            from utils.api import update_employee
            result = update_employee(emp["employee_id"], {
                "status":             new_status,
                "phone_number":       new_phone,
                "salary":             new_salary,
                "leave_balance_days": new_balance,
                "position":           new_position
            })
            if result:
                st.success("Mis à jour avec succès !")
                st.rerun()
            else:
                st.error("Erreur lors de la mise à jour.")
    with col2:
        if st.button(":material/close: Annuler", use_container_width=True):
            st.rerun()


# ── 2. MAIN INTERFACE FUNCTION ────────────────────────────────────────────────
def show_employees():
    st.title(":material/group: Gestion des Employés")
    st.divider()

    # ── Load all employees ────────────────────────────────────────────────────
    employees = get_all_employees()

    if not employees:
        st.error("Impossible de charger les employés.")
        return

    user_city = st.session_state.city

    # ── City filter — only DRH (Casablanca) can switch cities ────────────────
    if user_city == "Casablanca":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            cities = ["Toutes"] + sorted(
                set(e["city"] for e in employees if e.get("city"))
            )
            city_filter = st.selectbox(":material/location_on: Ville", cities)
    else:
        # Rabat/Tanger HR — locked to their city, no selector shown
        city_filter = user_city
        col1, col2, col3 = st.columns(3)
        st.info(
            f"Vous consultez les employés de l'agence de **{user_city}**.",
            icon=":material/info:"
        )

    # ── Other filters ─────────────────────────────────────────────────────────
    if user_city == "Casablanca":
        with col2:
            depts = ["Tous"] + sorted(
                set(e["department"] for e in employees if e.get("department"))
            )
            dept_filter = st.selectbox(":material/corporate_fare: Département", depts)
        with col3:
            role_filter = st.selectbox(":material/badge: Rôle",
                                       ["Tous","Employee","Manager","HR"])
        with col4:
            search = st.text_input(":material/search: Rechercher",
                                   placeholder="Nom")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            depts = ["Tous"] + sorted(
                set(e["department"] for e in employees if e.get("department"))
            )
            dept_filter = st.selectbox(":material/corporate_fare: Département", depts)
        with col2:
            role_filter = st.selectbox(":material/badge: Rôle",
                                       ["Tous","Employee","Manager","HR"])
        with col3:
            search = st.text_input(":material/search: Rechercher",
                                   placeholder="Nom")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = employees

    # City filter
    if city_filter != "Toutes":
        filtered = [e for e in filtered if e.get("city") == city_filter]

    # Department filter
    if dept_filter != "Tous":
        filtered = [e for e in filtered if e.get("department") == dept_filter]

    # Role filter
    if role_filter != "Tous":
        filtered = [e for e in filtered if e.get("role") == role_filter]

    # Search
    if search:
        s = search.lower()
        filtered = [e for e in filtered if
                   s in e.get("first_name","").lower() or
                   s in e.get("last_name","").lower() or
                   s in e.get("email","").lower()]

    total_found = len(filtered)
    
    # (Adapte "On Leave" ou "Active" si les mots exacts dans ta base sont différents)
    count_active = sum(1 for e in filtered if e.get("status") == "Active")
    count_leave = sum(1 for e in filtered if e.get("status") == "On leave")
    
    # Construction de la ligne d'information avec les icônes Streamlit
    status_text = (
        f":material/group: **{total_found}** au total  |  "
        f":material/check_circle: **{count_active}** présents  |  "
        f":material/schedule: **{count_leave}** en congé"
    )
    
    # Affichage de la ligne d'information stylisée
    st.markdown(status_text)
    st.divider()

    # ── 3. PAGINATION CALCULATION ─────────────────────────────────────────────
    ITEMS_PER_PAGE = 10
    total_pages = max(1, -(-len(filtered) // ITEMS_PER_PAGE))  # Ceiling division
    
    # Initialize the page state if it doesn't exist
    if "emp_page" not in st.session_state:
        st.session_state.emp_page = 1
        
    # Safety reset if filters shrink the list drastically
    if st.session_state.emp_page > total_pages:
        st.session_state.emp_page = 1
        
    # Extract only the 10 elements belonging to the current active page
    start_idx = (st.session_state.emp_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = filtered[start_idx:end_idx]

    # ── 4. RENDER CURRENT PAGE EMPLOYEES ──────────────────────────────────────
    for emp in page_items:
        status_icon = {
            "Active":   ":material/check_circle:",   
            "On Leave": ":material/schedule:",       
            "Resigned": ":material/cancel:"          
        }.get(emp.get("status"), ":material/help:")

        role_icon = {
            "HR":       ":material/admin_panel_settings:",  
            "Manager":  ":material/manage_accounts:",       
            "Employee": ":material/person:"                 
        }.get(emp.get("role"), ":material/person:")

        with st.expander(
            f"{status_icon} {role_icon} {emp['first_name']} {emp['last_name']} "
            f"— {emp.get('position','—')} | {emp.get('department','—')} | {emp.get('city','—')}"
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**:material/badge: Informations personnelles**")
                st.markdown(f"**Email:** {emp.get('email','—')}")
                st.markdown(f"**Téléphone:** {emp.get('phone_number','—')}")
                st.markdown(f"**Genre:** {emp.get('gender','—')}")
                st.markdown(f"**Ville:** {emp.get('city','—')}")
                st.markdown(f"**Date de naissance:** {emp.get('birth_date','—')}")

            with col2:
                st.markdown("**:material/business_center: Informations professionnelles**")
                st.markdown(f"**Département:** {emp.get('department','—')}")
                st.markdown(f"**Poste:** {emp.get('position','—')}")
                st.markdown(f"**Contrat:** {emp.get('contract_type','—')}")
                st.markdown(f"**Date d'embauche:** {emp.get('hire_date','—')}")
                st.markdown(f"**Salaire:** {emp.get('salary','—')} MAD")

            with col3:
                st.markdown("**:material/settings: Actions**")
                st.markdown(f"**Rôle:** {emp.get('role','—')}")
                st.markdown(f"**Statut:** {status_icon} {emp.get('status','—')}")
                st.markdown(f"**Solde congés:** {emp.get('leave_balance_days','—')} jours")

                st.markdown("---")
                
                # Clean Action Trigger: Triggers the popup modal instead of crowding the screen
                if st.button(":material/edit: Modifier", key=f"edit_btn_{emp['employee_id']}", use_container_width=True):
                    edit_employee_dialog(emp)

    # ── 5. PAGINATION NAVIGATION WIDGETS ──────────────────────────────────────
    st.divider()
    p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
    
    with p_col1:
        if st.button(":material/arrow_back: Précédent", disabled=st.session_state.emp_page == 1, use_container_width=True):
            st.session_state.emp_page -= 1
            st.rerun()
            
    with p_col2:
        st.markdown(
            f"<p style='text-align:center; padding-top:6px;'>Page "
            f"**{st.session_state.emp_page}** / **{total_pages}** "
            f"({len(filtered)} employés)</p>",
            unsafe_allow_html=True
        )
        
    with p_col3:
        if st.button("Suivant :material/arrow_forward:", disabled=st.session_state.emp_page == total_pages, use_container_width=True):
            st.session_state.emp_page += 1
            st.rerun()

    st.divider()

    # ── 6. ADD NEW EMPLOYEE FORM ──────────────────────────────────────────────
    st.subheader(":material/person_add: Ajouter un nouvel employé")
    st.info("Le mot de passe par défaut sera **Password123!** — l'employé devra le changer à sa première connexion.", icon=":material/lightbulb:")

    with st.form("add_employee_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name    = st.text_input("Prénom *")
            last_name     = st.text_input("Nom *")
            email         = st.text_input("Email *", placeholder="prenom.nom@techserv.ma")
            phone         = st.text_input("Téléphone")
            gender        = st.selectbox("Genre", ["Male", "Female"])
            birth_date    = st.date_input("Date de naissance")
        with col2:
            city          = st.selectbox("Ville *", ["Casablanca", "Rabat", "Tanger"])
            department    = st.selectbox("Département *", [
                "IT","Finance","HR","Marketing",
                "Sales","Operations","Support","R&D"
            ])
            position      = st.text_input("Poste *")
            contract_type = st.selectbox("Type de contrat", ["CDI","CDD","Stage"])
            hire_date     = st.date_input("Date d'embauche")
            salary        = st.number_input("Salaire (MAD)", min_value=0.0, step=500.0)
            role          = st.selectbox("Rôle", ["Employee","Manager","HR"])

        submit = st.form_submit_button(":material/person_add: Ajouter l'employé", use_container_width=True)

    if submit:
        if not first_name or not last_name or not email:
            st.error("Prénom, nom et email sont obligatoires.", icon=":material/warning:")
        else:
            from utils.api import add_employee
            result = add_employee({
                "first_name":    first_name,
                "last_name":     last_name,
                "email":         email,
                "phone_number":  phone,
                "gender":        gender,
                "birth_date":    str(birth_date),
                "city":          city,
                "department":    department,
                "position":      position,
                "contract_type": contract_type,
                "hire_date":     str(hire_date),
                "salary":        salary,
                "role":          role
            })
            if result:
                st.success(f"Employé {first_name} {last_name} ajouté avec succès !", icon=":material/check_circle:")
                st.rerun()
            else:
                st.error("Erreur — email déjà existant ou données invalides.", icon=":material/error:")