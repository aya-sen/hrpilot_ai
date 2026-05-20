import streamlit as st
from utils.api import get_all_employees, get_employee, update_employee_status

def show_employees():
    st.title(":material/group: Gestion des Employés")
    st.divider()

    # ── Load all employees ────────────────────────────────────────────────────
    employees = get_all_employees()

    if not employees:
        st.error("Impossible de charger les employés.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        cities = ["Toutes"] + sorted(set(e["city"] for e in employees if e.get("city")))
        city_filter = st.selectbox(":material/location_on: Ville", cities)
    with col2:
        depts = ["Tous"] + sorted(set(e["department"] for e in employees if e.get("department")))
        dept_filter = st.selectbox(":material/corporate_fare: Département", depts)
    with col3:
        roles = ["Tous", "Employee", "Manager", "HR"]
        role_filter = st.selectbox(":material/badge: Rôle", roles)

    # ── Search ────────────────────────────────────────────────────────────────
    search = st.text_input(":material/search: Rechercher par nom ou email", placeholder="Ex: Youssef...")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = employees
    if city_filter != "Toutes":
        filtered = [e for e in filtered if e.get("city") == city_filter]
    if dept_filter != "Tous":
        filtered = [e for e in filtered if e.get("department") == dept_filter]
    if role_filter != "Tous":
        filtered = [e for e in filtered if e.get("role") == role_filter]
    if search:
        s = search.lower()
        filtered = [e for e in filtered if
                   s in e.get("first_name","").lower() or
                   s in e.get("last_name","").lower() or
                   s in e.get("email","").lower()]

    st.markdown(f"**{len(filtered)} employé(s) trouvé(s)**")
    st.divider()

    # ── Employee list ─────────────────────────────────────────────────────────
    for emp in filtered:
        status_icon = {
            "Active":   ":material/check_circle:",   # A clean checkmark inside a circle
            "On Leave": ":material/schedule:",       # A clock icon indicating they are away/on leave
            "Resigned": ":material/cancel:"          # An 'X' inside a circle for deactivated/resigned
        }.get(emp.get("status"), ":material/help:")

        role_icon = {
            "HR":       ":material/admin_panel_settings:",  # A clean security shield for HR
            "Manager":  ":material/manage_accounts:",       # A profile with a gear/management feel
            "Employee": ":material/person:"                 # A clean user profile icon
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
                
                with st.form(key=f"edit_{emp['employee_id']}"):
                    new_status = st.selectbox(
                        "Statut",
                        ["Active", "On Leave", "Resigned"],
                        index=["Active","On Leave","Resigned"].index(
                            emp.get("status","Active")
                        )
                    )
                    new_phone  = st.text_input("Téléphone",
                                            value=emp.get("phone_number") or "")
                    new_salary = st.number_input("Salaire (MAD)",
                                                value=float(emp.get("salary") or 0),
                                                step=500.0)
                    new_balance = st.number_input("Solde congés (jours)",
                                                value=int(emp.get("leave_balance_days") or 28),
                                                step=1)
                    new_position = st.text_input("Poste",
                                                value=emp.get("position") or "")

                    save = st.form_submit_button(":material/save: Enregistrer",
                                                use_container_width=True)

                if save:
                    from utils.api import update_employee
                    result = update_employee(emp["employee_id"], {
                        "status":             new_status,
                        "phone_number":       new_phone,
                        "salary":             new_salary,
                        "leave_balance_days": new_balance,
                        "position":           new_position
                    })
                    if result:
                        st.success(":material/check_circle: Mis à jour !")
                        st.rerun()
                    else:
                        st.error(":material/error: Erreur lors de la mise à jour.")

    st.divider()

    # ── Add new employee ──────────────────────────────────────────────────────
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

        submit = st.form_submit_button(":material/person_add: Ajouter l'employé",
                                       use_container_width=True)

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