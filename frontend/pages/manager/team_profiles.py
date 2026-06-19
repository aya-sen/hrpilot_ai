import streamlit as st
import pandas as pd
from utils.api import get_manager_team

def show_team_profiles():
    # Style Navy Blue et ajustements de taille
    st.markdown("""
        <style>
        h1, h2, h3 { color: #000080 !important; }
        /* Rendre le titre de l'expander propre */
        .stExpander details summary p { font-weight: 500 !important; }
        /* Ajuster la taille du metric */
        [data-testid="stMetricValue"] { color: #000080 !important; font-size: 1.4rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
        </style>
    """, unsafe_allow_html=True)

    st.title(":material/groups: Profils de l'équipe")
    st.divider()

    manager_id = st.session_state.employee_id
    team = get_manager_team(manager_id)

    if not team:
        st.info("Vous n'avez aucun membre rattaché à votre équipe actuellement.", icon=":material/info:")
        return

    # ── 1. BARRE DE RECHERCHE PAR NOM ─────────────────────────────────────────
    search = st.text_input(
        ":material/search: Rechercher un collaborateur",
        placeholder="Entrez un nom ou un prénom..."
    )

    # Application du filtre de recherche si du texte est saisi
    filtered_team = team
    if search:
        s = search.lower()
        filtered_team = [
            m for m in team if
            s in m.get("first_name", "").lower() or
            s in m.get("last_name", "").lower()
        ]

    # ── 2. CALCUL DYNAMIQUE DES STATUTS (Sur l'équipe filtrée) ────────────────
    total_team = len(filtered_team)
    count_active = sum(1 for m in filtered_team if m.get("status") == "Active")
    count_leave = sum(1 for m in filtered_team if m.get("status") == "On Leave")
    count_resigned = sum(1 for m in filtered_team if m.get("status") == "Resigned")

    # Ligne d'info globale avec icônes (Remise au propre ici)
    stats_text = (
        f":material/group: **{total_team}** trouvé(s)    "
    )
    st.markdown(stats_text)
    st.divider()

    # ── 3. SÉPARATION DES LISTES FILTRÉES PAR CATÉGORIE ───────────────────────
    active_members = [m for m in filtered_team if m.get("status") == "Active"]
    leave_members = [m for m in filtered_team if m.get("status") == "On Leave"]
    resigned_members = [m for m in filtered_team if m.get("status") == "Resigned"]

    # ── 4. CRÉATION DES ONGLETS (TABS) ────────────────────────────────────────
    tab_active, tab_leave, tab_resigned = st.tabs([
        f"Actifs ({len(active_members)})", 
        f"En Congé ({len(leave_members)})", 
        f"Démissionnés ({len(resigned_members)})"
    ])

    # ── FONCTION INTERNE POUR RECRÉER LE DESIGN COMPACT ───────────────────────
    def render_member_list(member_list, icon_status):
        if not member_list:
            st.write("Aucun collaborateur ne correspond à ce statut ou à cette recherche.")
            return
            
        for member in member_list:
            label = f"{icon_status} {member['first_name']} {member['last_name']} — {member['position']}"
            
            with st.expander(label):
                col_info, col_metric = st.columns([4, 2])
                with col_info:
                    st.write(f":material/mail: **Email:** {member['email']}")
                    st.write(f":material/location_on: **Ville:** {member.get('city', '—')}")
                with col_metric:
                    st.metric(
                        label="Solde Congés", 
                        value=f"{member['leave_balance_days']} j"
                    )

    # ── 5. INJECTION DES DONNÉES DANS CHAQUE ONGLET (CORRIGÉ SANS ST.ICON) ────
    with tab_active:
        render_member_list(active_members, ":material/check_circle:")

    with tab_leave:
        render_member_list(leave_members, ":material/schedule:")

    with tab_resigned:
        render_member_list(resigned_members, ":material/cancel:")