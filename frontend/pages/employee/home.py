import streamlit as st
from utils.api import get_employee, get_my_leaves, get_my_documents

def show_home():
    employee_id = st.session_state.employee_id
    first_name  = st.session_state.first_name

    st.title(f"Bonjour, {first_name} !")
    #st.markdown("Voici un aperçu de votre espace personnel.")
    st.divider()

    # ── Get data ──────────────────────────────────────────────────────────────
    employee = get_employee(employee_id)
    my_leaves = get_my_leaves(employee_id)
    my_docs   = get_my_documents(employee_id)

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🏖️ Solde de congés",
            value=f"{employee['leave_balance_days']} jours" if employee else "—"
        )
    with col2:
        pending = sum(1 for l in my_leaves
                     if l["status"] in ["Pending_Manager", "Pending_HR"])
        st.metric(label="⏳ Demandes en attente", value=pending)

    with col3:
        approved = sum(1 for l in my_leaves if l["status"] == "Approved")
        st.metric(label="✅ Congés approuvés", value=approved)

    with col4:
        docs_pending = sum(1 for d in my_docs if d["status"] == "Pending")
        st.metric(label="📄 Documents en attente", value=docs_pending)

    st.divider()

    # ── Profile Summary ───────────────────────────────────────────────────────
    if employee:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("👤 Mon profil")
            st.markdown(f"**Nom complet:** {employee['first_name']} {employee['last_name']}")
            st.markdown(f"**Département:** {employee['department']}")
            st.markdown(f"**Poste:** {employee['position']}")
            st.markdown(f"**Ville:** {employee['city']}")
            st.markdown(f"**Contrat:** {employee['contract_type']}")
            st.markdown(f"**Date d'embauche:** {employee['hire_date']}")

        with col2:
            st.subheader("📋 Mes dernières demandes")
            if my_leaves:
                for leave in my_leaves[-3:]:
                    status_color = {
                        "Approved":       "🟢",
                        "Rejected":       "🔴",
                        "Pending_Manager":"🟡",
                        "Pending_HR":     "🟠"
                    }.get(leave["status"], "⚪")

                    st.markdown(
                        f"{status_color} **{leave['leave_type']}** — "
                        f"{leave['start_date']} au {leave['end_date']} "
                        f"({leave['duration_days']} jours)"
                    )
            else:
                st.info("Aucune demande de congé pour le moment.")

    st.divider()

    # ── Quick Actions ─────────────────────────────────────────────────────────
    st.subheader("⚡ Actions rapides")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💬 Ouvrir le chatbot", use_container_width=True):
            st.info("Allez dans '💬 Chatbot RH' dans le menu de gauche.")

    with col2:
        if st.button("📝 Soumettre une demande", use_container_width=True):
            st.info("Allez dans '📝 Soumettre demande' dans le menu de gauche.")

    with col3:
        if st.button("📋 Voir mes demandes", use_container_width=True):
            st.info("Allez dans '📋 Mes demandes' dans le menu de gauche.")