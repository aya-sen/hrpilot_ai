from textwrap import dedent

import streamlit as st
from utils.api import login


# --- FontAwesome ---
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)


def show_login():

    st.markdown("""
    <style>

    html, body, [data-testid="stAppViewContainer"] {
        margin: 0;
        padding: 0;
    }
   

    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }


    .left-box,
    .left-box * {
        color: white !important;
    }

    </style>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1.2])

   
    # ── LEFT SIDE — Branding ──────────────────────────────────────────────────
    with left:
    # Utiliser dedent permet de garder ton code propre tout en supprimant 
    # les espaces invisibles qui font bugger Streamlit  

        content = dedent("""
            <div class="left-box" style="
                background: linear-gradient(180deg, #2D5CFE 0%, #1A3FB5 100%);
                height: 100vh;
                padding: 80px 40px;
                color: white !important;
            ">
                <h1 style="color: white !important;">HRPilot AI</h1>
                <p style="color: white !important;">Système de gestion RH intelligent</p>
                <div style="margin-top: 50px;">
                    <div style="font-weight: bold; margin-bottom: 10px;color: white !important;"><i class="fa-solid fa-robot"></i></br> Assistant IA Conversationnel</div>
                    <div style="opacity: 0.8; font-size: 0.9rem;color: white !important;">Posez vos questions RH en langage naturel.</div>
                </div>
                         <div style="margin-top: 50px;">
                    <div style="font-weight: bold; margin-bottom: 10px;color: white !important;"><i class="fa-solid fa-file-lines"></i></br> Documents en un clic</div>
                    <div style="opacity: 0.8; font-size: 0.9rem;color: white !important;">Attestations, bulletins de paie et lettres générés en un clic.</div>
                </div>
                         <div style="margin-top: 50px;">
                    <div style="font-weight: bold; margin-bottom: 10px;color: white !important;"><i class="fa-solid fa-calendar-days"></i></br> Congés & Absences</div>
                    <div style="opacity: 0.8; font-size: 0.9rem;color: white !important;">Consultez votre solde et soumettez vos demandes de congés directement via l'interface.</div>
                </div>
                
            </div>
        """)
        st.markdown(content, unsafe_allow_html=True)


    # ── CÔTÉ DROIT : FORMULAIRE & LOGIQUE ──
    with right:
        _, center_col, _ = st.columns([1, 3, 1])
        with center_col:
            st.markdown("<br><br><br><br>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center;'>Connexion</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Bienvenue sur HRPilot AI</p>", unsafe_allow_html=True)
            
            with st.form("login_form", border=False):
                email = st.text_input("Adresse email", placeholder="prenom.nom@techserv.ma")
                password = st.text_input("Mot de passe", type="password", placeholder="••••••••••")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("Se connecter →", use_container_width=True)

            # --- TA LOGIQUE D'AUTHENTIFICATION INTÉGRÉE ICI ---
            if submit:
                if not email or not password:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    with st.spinner("Vérification en cours..."):
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
            st.info("**Password123!**")
            
            st.markdown("""
                <div style="display: flex; align-items: center; margin: 20px 0;">
                    <div style="flex: 1; height: 1px; background: #eee;"></div>
                </div>
                <p style='text-align: center; font-size: 0.8rem; color: gray;'>
                    © 2026 TechServ Solutions. Tous droits réservés.
                </p>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    show_login()