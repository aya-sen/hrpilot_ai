import streamlit as st
from utils.api import get_employee

def show_profile():
    st.title("👤 Mon Profil")
    st.divider()

    employee_id = st.session_state.employee_id
    employee    = get_employee(employee_id)

    if not employee:
        st.error("Impossible de charger le profil.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Informations personnelles")
        st.markdown(f"**Prénom:** {employee['first_name']}")
        st.markdown(f"**Nom:** {employee['last_name']}")
        st.markdown(f"**Email:** {employee['email']}")
        st.markdown(f"**Téléphone:** {employee.get('phone_number', '—')}")
        st.markdown(f"**Genre:** {employee.get('gender', '—')}")
        st.markdown(f"**Date de naissance:** {employee.get('birth_date', '—')}")
        st.markdown(f"**Ville:** {employee['city']}")

    with col2:
        st.subheader("💼 Informations professionnelles")
        st.markdown(f"**Département:** {employee['department']}")
        st.markdown(f"**Poste:** {employee['position']}")
        st.markdown(f"**Contrat:** {employee['contract_type']}")
        st.markdown(f"**Date d'embauche:** {employee.get('hire_date', '—')}")
        st.markdown(f"**Solde congés:** {employee['leave_balance_days']} jours")
        st.markdown(f"**Statut:** {employee['status']}")
        st.markdown(f"**Rôle:** {employee['role']}")

    st.divider()
    st.subheader("🔒 Changer le mot de passe")

    with st.form("password_form"):
        old_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm      = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit_pwd   = st.form_submit_button("Modifier le mot de passe",
                                            use_container_width=True)

    if submit_pwd:
        if not old_password or not new_password or not confirm:
            st.error("Veuillez remplir tous les champs.")
        elif new_password != confirm:
            st.error("Les mots de passe ne correspondent pas.")
        elif len(new_password) < 6:
            st.error("Le mot de passe doit contenir au moins 6 caractères.")
        else:
            from utils.api import change_password
            result = change_password(st.session_state.employee_id,
                                    old_password, new_password)
            if result:
                st.success("✅ Mot de passe modifié avec succès !")
            else:
                st.error("❌ Mot de passe actuel incorrect.")