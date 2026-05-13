import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.api import (
    get_kpis, get_leaves_by_department, get_leaves_by_type,
    get_leaves_by_status, get_monthly_trends, get_documents_by_type,
    get_burnout_risk, get_absence_predictions, get_department_alerts,
    get_city_stats, get_gender_distribution, get_contract_distribution,
    get_turnover_rate, get_avg_seniority, get_absenteeism_rate
)

def show_dashboard():

    st.markdown("""
        <style>
        h1 { color: #000080 !important; }
        [data-testid="stMetricValue"] { color: #000080 !important; }
        </style>
    """, unsafe_allow_html=True)
    
    user_city = st.session_state.city
    st.title(":material/analytics: Tableau de Bord RH")
    st.caption(f"Statistiques actuelles pour la ville de **{user_city}**")
    st.divider()
    # ── City selector — only for Casablanca (DRH) ─────────────────────────
    if user_city == "Casablanca":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### Direction des Ressources Humaines")
        with col2:
            city_filter = st.selectbox(
                "Vue",
                ["Casablanca", "Rabat", "Tanger", "Toutes les agences"],
                index=0
            )
        city = "all" if city_filter == "Toutes les agences" else city_filter
        label = city_filter
    else:
        city  = user_city
        label = user_city
        st.markdown(f"#### Agence de **{label}**")

    st.divider()

    # ── KPIs Row 1 ────────────────────────────────────────────────────────────
    kpis          = get_kpis(city)
    city_stats    = get_city_stats(city) 
    turnover      = get_turnover_rate(city)
    seniority     = get_avg_seniority(city)
    absenteeism   = get_absenteeism_rate(city) 
    alerts_response   = get_department_alerts(city)
    dept_data     = get_leaves_by_department(city)
    type_data     = get_leaves_by_type(city)
    status_data   = get_leaves_by_status(city)
    monthly       = get_monthly_trends(city)
    doc_data      = get_documents_by_type(city)
    burnout       = get_burnout_risk(city)
    predictions   = get_absence_predictions(city)
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
    
    with col2:
        st.metric(
            label=":material/history: Ancienneté moyenne",
            value=f"{seniority.get('avg_years', 0)} ans"
        )
    with col3:
        st.metric(
            label=":material/corporate_fare: Total entreprise",
            value=f"{kpis.get('total_employees', 0)}"
        )

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

    # ── Charts Row 1 ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(":material/leaderboard: Congés par département")
        dept_data = get_leaves_by_department(city)
        if dept_data:
            df  = pd.DataFrame(dept_data)
            fig = px.bar(df, x="department", y="total_leaves",
                        color="total_leaves", color_continuous_scale="Blues",
                        labels={"department": "Département",
                                "total_leaves": "Total"})
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(":material/pie_chart: Types de congés")

        type_data = get_leaves_by_type(city)
        
        if type_data and len(type_data) > 0: # Vérifie que la liste n'est pas vide
            df = pd.DataFrame(type_data)
            fig = px.pie(df, values="count", names="leave_type", hole=0.4)
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
            # REMPLACER use_container_width PAR width="stretch"
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Aucune donnée de congé disponible pour cette sélection.")

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

    # ── Charts Row 3 ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(":material/show_chart: Tendances mensuelles des demandes")
        monthly = get_monthly_trends(city)
        if monthly:
            df  = pd.DataFrame(monthly)
            fig = px.line(df, x="period", y="count", markers=True,
                         labels={"period": "Période", "count": "Demandes"})
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(":material/donut_large: Statut des demandes")
        status_data = get_leaves_by_status(city)
        if status_data:
            df = pd.DataFrame(status_data)
            colors = {"Approved": "#2ecc71", "Rejected": "#e74c3c",
                     "Pending_Manager": "#f39c12", "Pending_HR": "#3498db"}
            fig = px.bar(df, x="status", y="count", color="status",
                        color_discrete_map=colors,
                        labels={"status": "Statut", "count": "Nombre"})
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── Documents ─────────────────────────────────────────────────────────────
    st.subheader(":material/folder_open: Types de documents demandés")
    doc_data = get_documents_by_type(city)
    if doc_data:
        df  = pd.DataFrame(doc_data)
        fig = px.bar(df, x="document_type", y="count",
                    color="count", color_continuous_scale="Greens",
                    labels={"document_type": "Type", "count": "Nombre"})
        fig.update_layout(showlegend=False, height=250, xaxis_tickangle=-20)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Predictions ───────────────────────────────────────────────────────────
    st.subheader(":material/auto_graph: Prédictions d'absences")
    predictions = get_absence_predictions(city)
    if predictions.get("peak_month"):
        col1, col2 = st.columns([2, 1])
        with col1:
            monthly_dist = predictions.get("monthly_distribution", [])
            if monthly_dist:
                df  = pd.DataFrame(monthly_dist)
                fig = px.bar(df, x="month", y="absences",
                            labels={"month": "Mois",
                                    "absences": "Absences"})
                fig.update_layout(height=250)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.info(f" {predictions.get('prediction')}")

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