import streamlit as st

from utils.api import change_password


def _logout_and_rerun():
    # Clear whole session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def show_first_login_change_password():
    st.markdown(
        """
        <style>
        h1, h2, h3 { color: #000080 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title(":material/lock: Changement obligatoire du mot de passe")
    st.divider()

    # Guard: if not logged in, go back
    if not st.session_state.get("logged_in"):
        st.warning("Session expirée. Veuillez vous reconnecter.")
        st.rerun()

    employee_id = st.session_state.get("employee_id")
    if not employee_id:
        st.error("Employé introuvable dans la session.")
        st.rerun()

    st.info(
        "Votre compte nécessite un changement de mot de passe avant l'accès aux fonctionnalités.",
        icon=":material/info:",
    )

    st.markdown(
        """
        <style>
        /* Force the exact Streamlit form submit button selector you inspected */
        button[kind="primaryFormSubmit"] {
            background-color: #000080 !important;
            color: white !important;
            border: none !important;
        }
        button[kind="primaryFormSubmit"]:hover {
            background-color: #0000a0 !important;
            color: white !important;
            border: none !important;
        }

        /* Fallbacks (other button variants) */
        div.stButton > button[kind="primary"] {
            background-color: #000080 !important;
            color: white !important;
            border: none !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #0000a0 !important;
            border: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("first_login_password_form"):
        old_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm = st.text_input("Confirmer le nouveau mot de passe", type="password")
        submit = st.form_submit_button(
            "Mettre à jour le mot de passe",
            use_container_width=True,
            type="primary",
        )

    if submit:
        if not old_password or not new_password or not confirm:
            st.error("Veuillez remplir tous les champs.", icon=":material/warning:")
            return

        if new_password != confirm:
            st.error("Les mots de passe ne correspondent pas.", icon=":material/block:")
            return

        if len(new_password) < 6:
            st.error("Le mot de passe doit contenir au moins 6 caractères.", icon=":material/gpp_maybe:")
            return

        with st.spinner("Mise à jour en cours..."):
            result = change_password(employee_id, old_password, new_password)

        if result:
            st.success("Mot de passe mis à jour. Merci !")
            _logout_and_rerun()
        else:
            st.error("Mot de passe actuel incorrect ou erreur serveur.", icon=":material/cancel:")

