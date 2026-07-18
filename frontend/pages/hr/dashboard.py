import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from utils.api import (
    get_leaves_by_type,
    get_burnout_risk, get_leaves_monthly_current_year, get_department_alerts,
    get_city_stats, get_gender_distribution, get_contract_distribution,
    get_turnover_rate, get_avg_seniority, get_absenteeism_rate,get_leaves_pressure_summer
)

def show_dashboard():

    st.markdown("""
        <style>
        h1 { color: #000080 !important; }
        [data-testid="stMetricValue"] { color: #000080 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    user_city = st.session_state.city

    # ── 1. TITRE PRINCIPAL DE LA PAGE ─────────────────────────────────────────
    st.title(":material/analytics: Tableau de Bord RH")
    
    # Récupération dynamique du libellé de la ville choisie via le state
    # (Si le sélecteur n'a pas encore été rendu, on prend la ville par défaut du user)
    current_label = st.session_state.get("view_city_selector", user_city)
    
    if current_label == "Toutes les agences":
        st.caption("Statistiques actuelles pour **toutes les agences**")
    else:
        st.caption(f"Statistiques actuelles pour la ville de **{current_label}**")
        
    st.divider()

    # ── 2. BLOC DE SÉLECTION (À sa place d'origine) ───────────────────────────
    if user_city == "Casablanca":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### Direction des Ressources Humaines")
        with col2:
            # On ajoute une 'key' pour pouvoir lire la valeur n'importe où dans le script
            city_filter = st.selectbox(
                "Vue",
                ["Casablanca", "Rabat", "Tanger", "Toutes les agences"],
                index=0,
                key="view_city_selector"
            )
        city = "all" if city_filter == "Toutes les agences" else city_filter
    else:
        city = user_city
        st.markdown(f"#### Agence de **{user_city}**")

    st.divider()

    # ── KPIs Row 1 ────────────────────────────────────────────────────────────

    city_stats    = get_city_stats(city) 
    turnover      = get_turnover_rate(city)
    seniority     = get_avg_seniority(city)
    absenteeism   = get_absenteeism_rate(city) 
    alerts_response   = get_department_alerts(city)
    pressure_response     = get_leaves_pressure_summer(city)
    type_data     = get_leaves_by_type(city)
    burnout       = get_burnout_risk(city)
    yearly_data = get_leaves_monthly_current_year(city)
    gender_data   = get_gender_distribution(city)
    contract_data = get_contract_distribution(city)


    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label=":material/location_city: Employés (ville)",
            value=f"{city_stats.get("total_employees", 0)}"
        )

    with col2:
        st.metric(
            label=":material/check_circle: Actifs",
            value=f"{city_stats.get("active", 0)}"
        )

    with col3:
        st.metric(
            label=":material/hourglass_empty: Congés en attente",
            value=f"{city_stats.get("pending_leaves", 0)}"
        )

    with col4:
        st.metric(
            label=":material/description: Docs en attente",
            value=f"{city_stats.get("pending_docs", 0)}"
        )

    with col5:
        st.metric(
            label=":material/person_off: Absentéisme",
            value=f"{absenteeism.get('rate', 0)} %"
        )
  
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=":material/sync_alt: Taux de turnover",
            value=f"{turnover.get('turnover_rate', 0)} %"
        )
        
        by_department = turnover.get("by_department", [])
        if by_department:
            with st.expander("Voir le détail par département"):
                df_turnover = pd.DataFrame(by_department)
                df_turnover = df_turnover.rename(columns={
                    "department": "Département",
                    "total": "Effectif",
                    "resigned": "Départs",
                    "turnover_rate": "Taux (%)"
                })
                
                df_turnover["Taux (%)"] = df_turnover["Taux (%)"].round(1)
                
                def highlight_rate(val):
                    if val >= 20:
                        return "color: #d32f2f; font-weight: bold;"
                    elif val >= 10:
                        return "color: #f57c00; font-weight: bold;"
                    else:
                        return "color: #388e3c;"
                
                styled_df = df_turnover.style.map(
                    highlight_rate, subset=["Taux (%)"]
                ).format({"Taux (%)": "{:.1f}"})
                
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.metric(
            label=":material/history: Ancienneté moyenne",
            value=f"{seniority.get('avg_years', 0)} ans"
        )

        by_department = seniority.get("by_department", [])
        if by_department:
            with st.expander("Voir le détail par département"):
                df_sen = pd.DataFrame(by_department)
                df_sen = df_sen.rename(columns={
                    "department": "Département",
                    "total": "Effectif",
                    "avg_years": "Ancienneté moyenne (ans)"
                })

                # Affichage simple (valeurs déjà arrondies côté backend)
                st.dataframe(df_sen, hide_index=True, use_container_width=True)

    

    st.divider()

    # ── Alerts ──────────────────────────────────────

    # On vérifie si la réponse contient bien la clé "alerts"
    if alerts_response and "alerts" in alerts_response:
        alerts = alerts_response["alerts"]
        
        if alerts:
            st.subheader(":material/report_problem: Alertes de sous-effectif")
            for alert in alerts:
                
                # On affiche un message différent selon le niveau (Critical ou Warning)
                if alert.get("alert_level") == "Critical":
                    st.error(alert["message"])
                else:
                    st.warning(alert["message"])
            st.divider()
        else:
            # Optionnel : décommenter pour débugger et voir si la liste est juste vide
            # st.write("Aucune alerte de sous-effectif pour le moment.")
            pass


    # ── Charts Row 1 (Attentes vs Types) ──────────────────────────────────────
    col1, col2 = st.columns(2)
    
    with col1:
        # Titre court avec icône native
        st.subheader(":material/hourglass_empty: Attentes Été 2026")
        
        if pressure_response:
            df_pressure = pd.DataFrame(pressure_response)
            
            # Pivotement des données
            df_pivot = df_pressure.pivot(
                index="Département", 
                columns="Mois", 
                values="Demandes en Attente"
            )
            
            # Tri chronologique et nettoyage
            df_pivot = df_pivot.reindex(columns=["Juin", "Juillet", "Août"]).fillna(0).astype(int)
            
            st.dataframe(
                df_pivot.style.background_gradient(cmap="Oranges", vmin=0, vmax=5),
                use_container_width=True
            )
        else:
            st.info("Aucune demande en attente pour la période estivale.")

    with col2:
        # Titre court avec icône native, parfaitement aligné à col1
        st.subheader(":material/pie_chart: Répartition Congés")
        
        # On s'assure que la récupération de données et le graphique restent bien dans col2
        type_data = get_leaves_by_type(city)
        
        if type_data and len(type_data) > 0:
            df = pd.DataFrame(type_data)
            fig = px.pie(df, values="count", names="leave_type", hole=0.4)
            # Taille compacte (height=250) et marges réduites
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée disponible.")

    # ── Charts Row 2 ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚤ Répartition Homme / Femme")
        gender_data = get_gender_distribution(city)
        if gender_data:
            df  = pd.DataFrame(gender_data)
            fig = px.pie(df, values="count", names="gender",
                        color="gender",
                        color_discrete_map={"Male": "#3498db",
                                            "Female": "#e91e8c"},
                        hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(":material/assignment: Types de contrats")
        contract_data = get_contract_distribution(city)
        if contract_data:
            df  = pd.DataFrame(contract_data)
            fig = px.pie(df, values="count", names="contract_type",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                        hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── Section : Suivi Absences Année En Cours ───────────────────────────────
    st.subheader(":material/calendar_month: Absences de l'Année")
    
    if yearly_data and yearly_data.get("monthly_distribution"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            df_year = pd.DataFrame(yearly_data["monthly_distribution"])
            
            # Graphique en barres propre
            fig_year = px.bar(
                df_year, 
                x="month", 
                y="absences",
                labels={"month": "Mois", "absences": "Absences"}
            )
            fig_year.update_layout(height=230, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_year, use_container_width=True)
            
        with col2:
            # On affiche le message d'information de l'année en cours
            st.info(yearly_data.get("info_message", "Aucune donnée pour cette période."))
    else:
        st.info("Aucune donnée disponible pour l'année en cours.")
        
    st.divider()

    # ── Burnout Risk ──────────────────────────────────────────────────────────
    st.subheader(":material/psychology_alt: Risque de Burnout")
    burnout = get_burnout_risk(city)
    at_risk = burnout.get("employees", [])

    # CORRECTION ICI : Si city est "all", on prend tout le monde. 
    # Sinon, on filtre par ville.
    if city == "all":
        city_risk = at_risk
        display_name = "toutes les agences"
    else:
        city_risk = [e for e in at_risk if e["city"] == city]
        display_name = city

    if city_risk:
        st.warning(f"**{len(city_risk)} employé(s)** au total ({display_name}) n'ont pas pris de congé depuis 6+ mois.")
        for emp in city_risk:
            # On ajoute la ville dans le titre de l'expander pour la vue globale
            title_city = f" ({emp['city']})" if city == "all" else ""
            with st.expander(f"👤 {emp['name']} — {emp['department']}{title_city}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Dernier congé:** {emp['last_leave']}")
                    st.markdown(f"**Solde:** {emp['leave_balance']} jours")
                with col2:
                    level = "🔴 Élevé" if emp["risk_level"] == "High" else "🟡 Moyen"
                    st.markdown(f"**Risque:** {level}")
                st.info(emp["recommendation"])
    else:
        st.success(f"Aucun risque de burnout détecté pour {display_name}.")