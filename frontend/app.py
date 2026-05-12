import os

import streamlit as st

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Change la couleur du bouton de type 'primary' */
    div.stButton > button[kind="primary"] {
        background-color: #000080 !important; /* Navy Blue */
        color: white !important;
        border: none;
    }

    /* Optionnel : Change la couleur au survol (hover) */
    div.stButton > button[kind="primary"]:hover {
        background-color: #0000a0 !important; /* Un bleu un peu plus clair au survol */
        border: none;
    }
    
    /* Centrer le texte du bouton s'il y a des icônes */
    div.stButton > button p {
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)


st.set_page_config(
    page_title="HRPilot AI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit's automatic page navigation
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# ── Session state initialization ──────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in    = False
if "employee_id" not in st.session_state:
    st.session_state.employee_id  = None
if "role" not in st.session_state:
    st.session_state.role         = None
if "first_name" not in st.session_state:
    st.session_state.first_name   = None
if "last_name" not in st.session_state:
    st.session_state.last_name    = None
if "city" not in st.session_state:
    st.session_state.city         = None
if "department" not in st.session_state:
    st.session_state.department   = None

# ── Routing ───────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    from login import show_login
    show_login()
else:
    role = st.session_state.role

    # ── Sidebar navigation ────────────────────────────────────────────────────
    with st.sidebar:
        BASE_DIR = os.path.dirname(__file__)
        logo_path = os.path.join(BASE_DIR, "logo.png")

        col1, col2, col3 = st.columns([0.5,4,0.5])

        with col2:
             st.image(logo_path, width=240)
        #st.title("HRPilot AI")
        st.markdown(
                f"<h3 style='text-align: center; margin-bottom: 0;'>{st.session_state.first_name} {st.session_state.last_name}</h3>", 
                unsafe_allow_html=True
        )
            
            # Centrage du Rôle (en gris pour un look plus pro)
        st.markdown(
                f"<p style='text-align: center; color: gray; font-weight: bold;'>{role}</p>", 
                unsafe_allow_html=True
        )
        st.divider()

        if role == "Employee":
            pages = {
                "home": {"label": "Accueil", "icon": "home"},
                "chatbot": {"label": "Chatbot", "icon": "smart_toy"},
                "requests": {"label": "Soumettre demande", "icon": "edit_note"},
                "my_requests": {"label": "Mes demandes", "icon": "checklist"},
                "profile": {"label": "Mon profil", "icon": "person"}
            }
        elif role == "Manager":
            pages = {
                "home": {"label": "Accueil", "icon": "home"},
                "team_requests": {"label": "Demandes équipe", "icon": "groups_2"},
                "team_profiles": {"label": "Profils équipe", "icon": "badge"},
                "chatbot": {"label": "Chatbot", "icon": "smart_toy"},
                "requests": {"label": "Soumettre demande", "icon": "edit_note"},
                "my_requests": {"label": "Mes demandes", "icon": "checklist"},
                "profile": {"label": "Mon profil", "icon": "person"}
            }
        else:  # HR
            pages = {
                 # ── HR specific ──
                "dashboard": {"label": "Dashboard", "icon": "dashboard"},
                "hr_employees": {"label": "Employés", "icon": "groups"},
                "hr_leaves": {"label": "Congés", "icon": "beach_access"},
                "hr_documents": {"label": "Documents", "icon": "description"},
                "hr_analysis": {"label": "Analyse document", "icon": "manage_search"},
                "chatbot": {"label": "Chatbot", "icon": "smart_toy"},
                "requests": {"label": "Soumettre demande", "icon": "edit_note"},
                "my_requests": {"label": "Mes demandes", "icon": "checklist"},
                "profile": {"label": "Mon profil", "icon": "person"}
            }

        # Initialisation de la page par défaut
        if "current_page" not in st.session_state:
            st.session_state.current_page = "dashboard" if role == "HR" else "home"

        # Affichage des boutons de navigation
        for page_id, info in pages.items():
            # Style du bouton : 'primary' pour la page active, 'secondary' pour les autres
            is_active = st.session_state.current_page == page_id
            
            if st.button(
                info["label"], 
                key=f"btn_{page_id}", 
                use_container_width=True, 
                icon=f":material/{info['icon']}:",
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_page = page_id
                st.rerun()

        st.divider()

        if st.button("Déconnexion", use_container_width=True, icon=":material/logout:"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── Page routing ──────────────────────────────────────────────────────────
    # On utilise la page stockée dans le session_state
    page = st.session_state.current_page
    if page == "home":
        from pages.employee.home import show_home
        show_home()
    elif page == "chatbot":
        from pages.employee.chatbot import show_chatbot
        show_chatbot()
    elif page == "requests":
        from pages.employee.requests import show_requests
        show_requests()
    elif page == "my_requests":
        from pages.employee.requests import show_my_requests
        show_my_requests()
    elif page == "profile":
        if role == "Employee":
            from pages.employee.profile import show_profile
        elif role == "Manager":
            from pages.employee.profile import show_profile
        else:
            from pages.employee.profile import show_profile
        show_profile()
    elif page == "team_requests":
        from pages.manager.team_requests import show_team_requests
        show_team_requests()
    elif page == "team_profiles":
        from pages.manager.team_profiles import show_team_profiles
        show_team_profiles()
    elif page == "dashboard":
        from pages.hr.dashboard import show_dashboard
        show_dashboard()
    elif page == "hr_employees":
        from pages.hr.employees import show_employees
        show_employees()
    elif page == "hr_leaves":
        from pages.hr.leaves import show_leaves
        show_leaves()
    elif page == "hr_documents":
        from pages.hr.documents import show_documents
        show_documents()
    elif page == "hr_analysis":
        from pages.hr.analysis import show_analysis
        show_analysis()