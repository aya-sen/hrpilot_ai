import streamlit as st
from utils.api import login

def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/color/96/artificial-intelligence.png",
                 width=80)
        st.title("HRPilot AI")
        st.markdown("#### Système de gestion RH intelligent")
        st.divider()

        with st.form("login_form"):
            st.subheader("Connexion")
            email    = st.text_input("📧 Email", placeholder="prenom.nom@techserv.ma")
            password = st.text_input("🔒 Mot de passe", type="password",
                                     placeholder="Password123!")
            submit   = st.form_submit_button("Se connecter", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                with st.spinner("Connexion en cours..."):
                    result = login(email, password)

                if result:
                    st.session_state.logged_in   = True
                    st.session_state.employee_id = result["employee_id"]
                    st.session_state.role        = result["role"]
                    st.session_state.first_name  = result["first_name"]
                    st.session_state.last_name   = result["last_name"]
                    st.session_state.city        = result["city"]
                    st.session_state.department  = result["department"]
                    st.success(f"Bienvenue {result['first_name']} !")
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.info("💡 Mot de passe par défaut: **Password123!**")