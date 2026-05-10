import os

import streamlit as st

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
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
        logo_path = os.path.join(BASE_DIR, "hrpilot_log.png")

        st.image(logo_path, width=220)
        #st.title("HRPilot AI")
        st.markdown(f"👤 **{st.session_state.first_name} {st.session_state.last_name}**")
        st.markdown(f"🏢 **{role}**")
        st.divider()

        if role == "Employee":
            pages = {
                "🏠 Accueil":           "home",
                "💬 Chatbot RH":        "chatbot",
                "📝 Soumettre demande":  "requests",
                "📋 Mes demandes":       "my_requests",
                "👤 Mon profil":         "profile"
            }
        elif role == "Manager":
            pages = {
                "📋 Demandes équipe":    "team_requests",
                "👥 Profils équipe":     "team_profiles",
                "💬 Chatbot RH":        "chatbot",
                "👤 Mon profil":         "profile"
            }
        else:  # HR
            pages = {
                "📊 Dashboard":          "dashboard",
                "👥 Employés":           "hr_employees",
                "🏖️ Congés":            "hr_leaves",
                "📄 Documents":          "hr_documents",
                "🔍 Analyse document":   "hr_analysis",
                "💬 Chatbot RH":        "chatbot",
                "👤 Mon profil":         "profile"
            }

        selected = st.radio("Navigation", list(pages.keys()),
                           label_visibility="collapsed")
        st.divider()

        if st.button("Déconnexion", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── Page routing ──────────────────────────────────────────────────────────
    page = pages[selected]

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
            from pages.manager.profile import show_profile
        else:
            from pages.hr.profile import show_profile
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