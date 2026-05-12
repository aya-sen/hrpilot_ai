import streamlit as st
from utils.api import get_employee, get_my_leaves, get_my_documents

def show_home():
    employee_id = st.session_state.employee_id
    first_name  = st.session_state.first_name

    # ── CSS pour les couleurs et le style ──────────────────────────────────────
    st.markdown("""
        <style>
        /* Titre en Navy Blue */
        h1, h2, h3 { color: #000080 !important; }
        
        /* Styliser les métriques (KPI cards) */
        [data-testid="stMetricLabel"] {
            font-weight: bold;
            color: #555555;
        }
        
        /* Icônes de statut dans la liste des demandes */
        .status-icon {
            font-size: 1.2rem;
            margin-right: 10px;
            vertical-align: middle;
        }
        </style>
    """, unsafe_allow_html=True)

    # Titre avec icône Material
    st.title(f":material/waving_hand: Bonjour, {first_name} !")
    st.divider()

    # ── Get data ──────────────────────────────────────────────────────────────
    employee = get_employee(employee_id)
    my_leaves = get_my_leaves(employee_id)
    my_docs   = get_my_documents(employee_id)

    # ── KPI Cards avec Material Icons ─────────────────────────────────────────
    # ── KPI Cards avec Material Icons intégrés ─────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label=":material/beach_access: Solde de congés",
            value=f"{employee['leave_balance_days']} jours" if employee else "—",
            help="Nombre de jours restants"
        )

    with col2:
        pending = sum(1 for l in my_leaves if l["status"] in ["Pending_Manager", "Pending_HR"])
        st.metric(
            label=":material/hourglass_empty: Demandes en attente", 
            value=pending
        )

    with col3:
        approved = sum(1 for l in my_leaves if l["status"] == "Approved")
        st.metric(
            label=":material/check_circle: Congés approuvés", 
            value=approved
        )

    with col4:
        docs_pending = sum(1 for d in my_docs if d["status"] == "Pending")
        st.metric(
            label=":material/description: Documents en attente", 
            value=docs_pending
        )

    st.divider()

    # ── Profile Summary ───────────────────────────────────────────────────────
    if employee:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(":material/account_circle: Mon profil")
            st.markdown(f"**:material/person: Nom complet:** {employee['first_name']} {employee['last_name']}")
            st.markdown(f"**:material/domain: Département:** {employee['department']}")
            st.markdown(f"**:material/work: Poste:** {employee['position']}")
            st.markdown(f"**:material/location_on: Ville:** {employee['city']}")
            st.markdown(f"**:material/description: Contrat:** {employee['contract_type']}")
            st.markdown(f"**:material/calendar_today: Date d'embauche:** {employee['hire_date']}")

        with col2:
            st.subheader(":material/history: Mes dernières demandes")
            if my_leaves:
                # On prend les 3 dernières et on inverse pour avoir la plus récente en haut
                for leave in reversed(my_leaves[-3:]):
                    # Mapping des statuts vers des icônes Material
                    status_info = {
                        "Approved":        (":material/check_circle:", "#28a745"), # Vert pro
                        "Rejected":        (":material/cancel:", "#dc3545"),       # Rouge pro
                        "Pending_Manager": (":material/schedule:", "#ffc107"),      # Jaune/Orange
                        "Pending_HR":      (":material/pending:", "#fd7e14")        # Orange
                    }.get(leave["status"], (":material/help:", "grey"))

                    icon, color = status_info
                    
                    st.markdown(
                        f"<span style='color:{color}; font-weight:bold;'>{icon}</span> "
                        f"**{leave['leave_type']}** — "
                        f"{leave['start_date']} au {leave['end_date']} "
                        f"({leave['duration_days']} jours)",
                        unsafe_allow_html=True
                    )
            else:
                st.info("Aucune demande de congé pour le moment.")

    st.divider()