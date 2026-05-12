import streamlit as st
from utils.api import get_manager_team

def show_team_profiles():
    # Style Navy Blue et ajustements de taille
    st.markdown("""
        <style>
        h1, h2, h3 { color: #000080 !important; }
        /* Rendre le nom (subheader) plus petit */
        .stMarkdown h3 { font-size: 1.2rem !important; margin-bottom: 0px !important; }
        /* Ajuster la taille du metric */
        [data-testid="stMetricValue"] { color: #000080 !important; font-size: 1.4rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
        /* Réduire l'espacement interne du container */
        [data-testid="stVerticalBlockBorderWrapper"] > div { padding: 5px 15px !important; }
        </style>
    """, unsafe_allow_html=True)

    st.title(":material/groups: Profils de l'équipe")
    st.divider()

    manager_id = st.session_state.employee_id
    team = get_manager_team(manager_id)

    if not team:
        st.info("Vous n'avez aucun membre rattaché à votre équipe actuellement.", icon=":material/info:")
    else:
        for member in team:
            with st.container(border=True):
                # On passe à 2 colonnes seulement (info et metric) pour gagner de la place
                col_info, col_metric = st.columns([4, 2])
                
                with col_info:
                    # Utilisation de subheader comme dans ton code préféré
                    st.subheader(f"{member['first_name']} {member['last_name']}")
                    # Markdown pur pour garantir l'affichage des icônes
                    st.write(f":material/work: **Poste:** {member['position']}")
                    st.write(f":material/mail: **Email:** {member['email']}")
                    st.write(f":material/location_on: **Ville:** {member.get('city', '—')}")

                with col_metric:
                    # Metric aligné à droite
                    st.metric(
                        label="Solde Congés", 
                        value=f"{member['leave_balance_days']} j"
                    )
                    # Statut
                    status_color = "#28a745" if member['status'] == "Active" else "#dc3545"
                    st.markdown(f"Statut: <span style='color:{status_color}; font-weight:bold;'>{member['status']}</span>", unsafe_allow_html=True)