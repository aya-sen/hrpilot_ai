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
    city = st.session_state.city
    st.title("📊 Tableau de Bord RH")
    st.markdown(f"Données filtrées pour l'agence de **{city}**")
    st.divider()

    # ── KPIs Row 1 ────────────────────────────────────────────────────────────
    kpis        = get_kpis()
    city_stats  = get_city_stats(city)
    turnover    = get_turnover_rate()
    seniority   = get_avg_seniority()
    absenteeism = get_absenteeism_rate(city)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Employés (ville)",   city_stats.get("total_employees", 0))
    col2.metric("✅ Actifs",             city_stats.get("active", 0))
    col3.metric("⏳ Congés en attente",  city_stats.get("pending_leaves", 0))
    col4.metric("📄 Docs en attente",    city_stats.get("pending_docs", 0))
    col5.metric("🏖️ Absentéisme",        f"{absenteeism.get('rate', 0)}%")

    col1, col2, col3 = st.columns(3)
    col1.metric("🔄 Taux de turnover",   f"{turnover.get('turnover_rate', 0)}%")
    col2.metric("📅 Ancienneté moyenne", f"{seniority.get('avg_years', 0)} ans")
    col3.metric("👥 Total entreprise",   kpis.get("total_employees", 0))

    st.divider()

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts_data = get_department_alerts()
    alerts = alerts_data.get("alerts", [])
    if alerts:
        st.subheader("🚨 Alertes de sous-effectif")
        for alert in alerts:
            if alert["alert_level"] == "Critical":
                st.error(alert["message"])
            else:
                st.warning(alert["message"])
        st.divider()

    # ── Charts Row 1 ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Congés par département")
        dept_data = get_leaves_by_department()
        if dept_data:
            df  = pd.DataFrame(dept_data)
            fig = px.bar(df, x="department", y="total_leaves",
                        color="total_leaves", color_continuous_scale="Blues",
                        labels={"department": "Département",
                                "total_leaves": "Total"})
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🥧 Types de congés")
        type_data = get_leaves_by_type()
        if type_data:
            df  = pd.DataFrame(type_data)
            fig = px.pie(df, values="count", names="leave_type", hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── Charts Row 2 ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚤ Répartition Homme / Femme")
        gender_data = get_gender_distribution()
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
        st.subheader("📋 Types de contrats")
        contract_data = get_contract_distribution()
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
        st.subheader("📅 Tendances mensuelles des demandes")
        monthly = get_monthly_trends()
        if monthly:
            df  = pd.DataFrame(monthly)
            fig = px.line(df, x="period", y="count", markers=True,
                         labels={"period": "Période", "count": "Demandes"})
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 Statut des demandes")
        status_data = get_leaves_by_status()
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
    st.subheader("📄 Types de documents demandés")
    doc_data = get_documents_by_type()
    if doc_data:
        df  = pd.DataFrame(doc_data)
        fig = px.bar(df, x="document_type", y="count",
                    color="count", color_continuous_scale="Greens",
                    labels={"document_type": "Type", "count": "Nombre"})
        fig.update_layout(showlegend=False, height=250, xaxis_tickangle=-20)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Predictions ───────────────────────────────────────────────────────────
    st.subheader("🔮 Prédictions d'absences")
    predictions = get_absence_predictions()
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
            st.info(f"📌 {predictions.get('prediction')}")

    st.divider()

    # ── Burnout Risk ──────────────────────────────────────────────────────────
    st.subheader("⚠️ Risque de Burnout")
    burnout  = get_burnout_risk()
    at_risk  = burnout.get("employees", [])
    city_risk = [e for e in at_risk if e["city"] == city]

    if city_risk:
        st.warning(f"**{len(city_risk)} employé(s)** de {city} n'ont pas pris de congé depuis 6+ mois.")
        for emp in city_risk:
            with st.expander(f"👤 {emp['name']} — {emp['department']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Dernier congé:** {emp['last_leave']}")
                    st.markdown(f"**Solde:** {emp['leave_balance']} jours")
                with col2:
                    level = "🔴 Élevé" if emp["risk_level"] == "High" else "🟡 Moyen"
                    st.markdown(f"**Risque:** {level}")
                st.info(emp["recommendation"])
    else:
        st.success(f"✅ Aucun risque de burnout détecté pour {city}.")