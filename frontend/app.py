import streamlit as st

st.set_page_config(
    page_title="HRPilot AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    from pages.login import show_login
    show_login()
else:
    role = st.session_state.role

    # ── Sidebar navigation ────────────────────────────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/artificial-intelligence.png",
                 width=80)
        st.title("HRPilot AI")
        st.markdown(f"👤 **{st.session_state.first_name} {st.session_state.last_name}**")
        st.markdown(f"🏢 **{role}**")
        st.divider()

        if role == "Employee":
            pages = {
                "🏠 Accueil":           "home",
                "🤖 Chatbot RH":        "chatbot",
                "📝 Soumettre demande":  "requests",
                "📋 Mes demandes":       "my_requests",
                "👤 Mon profil":         "profile"
            }
        elif role == "Manager":
            pages = {
                "📋 Demandes équipe":    "team_requests",
                "👥 Profils équipe":     "team_profiles",
                "🤖 Chatbot RH":        "chatbot",
                "👤 Mon profil":         "profile"
            }
        else:  # HR
            pages = {
                "📊 Dashboard":          "dashboard",
                "👥 Employés":           "hr_employees",
                "🏖️ Congés":            "hr_leaves",
                "📄 Documents":          "hr_documents",
                "🔍 Analyse document":   "hr_analysis",
                "🤖 Chatbot RH":        "chatbot",
                "👤 Mon profil":         "profile"
            }

        selected = st.radio("Navigation", list(pages.keys()),
                           label_visibility="collapsed")
        st.divider()

        if st.button("🚪 Déconnexion", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── Page routing ──────────────────────────────────────────────────────────
    page = pages[selected]

    if page == "home":
        from frontend.pages.employee.home import show_home
        show_home()
    elif page == "chatbot":
        from frontend.pages.employee.chatbot import show_chatbot
        show_chatbot()
    elif page == "requests":
        from frontend.pages.employee.requests import show_requests
        show_requests()
    elif page == "my_requests":
        from frontend.pages.employee.requests import show_my_requests
        show_my_requests()
    elif page == "profile":
        if role == "Employee":
            from frontend.pages.employee.profile import show_profile
        elif role == "Manager":
            from frontend.pages.manager.profile import show_profile
        else:
            from frontend.pages.hr.profile import show_profile
        show_profile()
    elif page == "team_requests":
        from frontend.pages.manager.team_requests import show_team_requests
        show_team_requests()
    elif page == "team_profiles":
        from frontend.pages.manager.team_profiles import show_team_profiles
        show_team_profiles()
    elif page == "dashboard":
        from frontend.pages.hr.dashboard import show_dashboard
        show_dashboard()
    elif page == "hr_employees":
        from frontend.pages.hr.employees import show_employees
        show_employees()
    elif page == "hr_leaves":
        from frontend.pages.hr.leaves import show_leaves
        show_leaves()
    elif page == "hr_documents":
        from frontend.pages.hr.documents import show_documents
        show_documents()
    elif page == "hr_analysis":
        from frontend.pages.hr.analysis import show_analysis
        show_analysis()