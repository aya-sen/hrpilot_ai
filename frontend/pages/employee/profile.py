import streamlit as st
from utils.api import get_employee

def show_profile():
    # Injection du style CSS pour le Navy Blue et la cohérence visuelle
    st.markdown("""
        <style>
        h1, h2, h3 { color: #000080 !important; }
        
       
        </style>
    """, unsafe_allow_html=True)

    st.title(":material/person: Mon Profil")
    st.divider()

    employee_id = st.session_state.employee_id
    employee    = get_employee(employee_id)

    if not employee:
        st.error("Impossible de charger le profil.", icon=":material/error:")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(":material/badge: Informations personnelles")
        st.markdown(f"**:material/person: Prénom:** {employee['first_name']}")
        st.markdown(f"**:material/person_outline: Nom:** {employee['last_name']}")
        st.markdown(f"**:material/mail: Email:** {employee['email']}")
        st.markdown(f"**:material/call: Téléphone:** {employee.get('phone_number', '—')}")
        st.markdown(f"**:material/wc: Genre:** {employee.get('gender', '—')}")
        st.markdown(f"**:material/cake: Date de naissance:** {employee.get('birth_date', '—')}")
        st.markdown(f"**:material/location_on: Ville:** {employee['city']}")

    with col2:
        st.subheader(":material/work: Informations professionnelles")
        st.markdown(f"**:material/domain: Département:** {employee['department']}")
        st.markdown(f"**:material/psychology: Poste:** {employee['position']}")
        st.markdown(f"**:material/description: Contrat:** {employee['contract_type']}")
        st.markdown(f"**:material/calendar_today: Date d'embauche:** {employee.get('hire_date', '—')}")
        st.markdown(f"**:material/beach_access: Solde congés:** {employee['leave_balance_days']} jours")
        st.markdown(f"**:material/verified_user: Statut:** {employee['status']}")
        st.markdown(f"**:material/admin_panel_settings: Rôle:** {employee['role']}")

    st.divider()
    st.subheader(":material/lock: Changer le mot de passe")

    with st.form("password_form"):
        old_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm      = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit_pwd   = st.form_submit_button("Modifier le mot de passe",
                                            use_container_width=True)

    if submit_pwd:
        if not old_password or not new_password or not confirm:
            st.error("Veuillez remplir tous les champs.", icon=":material/warning:")
        elif new_password != confirm:
            st.error("Les mots de passe ne correspondent pas.", icon=":material/block:")
        elif len(new_password) < 6:
            st.error("Le mot de passe doit contenir au moins 6 caractères.", icon=":material/gpp_maybe:")
        else:
            from utils.api import change_password
            result = change_password(st.session_state.employee_id,
                                    old_password, new_password)
            if result:
                st.success("Mot de passe modifié avec succès !", icon=":material/check_circle:")
            else:
                st.error("Mot de passe actuel incorrect.", icon=":material/cancel:")