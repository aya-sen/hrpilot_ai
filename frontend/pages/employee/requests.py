import streamlit as st
from datetime import date, timedelta
from utils.api import (submit_leave, submit_document_request,
                       get_my_leaves, get_my_documents,
                       get_employee, upload_certificate)

def show_requests():
    st.title("📝 Soumettre une demande")
    st.divider()

    employee_id = st.session_state.employee_id
    employee    = get_employee(employee_id)

    tab1, tab2 = st.tabs(["🏖️ Demande de congé", "📄 Demande de document"])

    # ── TAB 1: Leave Request ──────────────────────────────────────────────────
    with tab1:
        st.subheader("Nouvelle demande de congé")

        if employee:
            st.info(f"💡 Solde de congés disponible : **{employee['leave_balance_days']} jours**")

        with st.form("leave_form"):
            leave_type = st.selectbox("Type de congé", [
                "Annual", "Sick", "Maternity", "Paternity", "Emergency"
            ])
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Date de début",
                                          min_value=date.today())
            with col2:
                end_date = st.date_input("Date de fin",
                                        min_value=date.today() + timedelta(days=1))

            comment = st.text_area("Commentaire (optionnel)",
                                  placeholder="Ex: Voyage prévu, rendez-vous médical...")

            certificate = st.file_uploader("📎 Certificat médical (si congé maladie)",
                                          type=["pdf"])

            submit = st.form_submit_button("Soumettre la demande",
                                          use_container_width=True)

        if submit:
            if end_date <= start_date:
                st.error("La date de fin doit être après la date de début.")
            else:
                duration = (end_date - start_date).days
                result = submit_leave(
                    employee_id = employee_id,
                    leave_type  = leave_type,
                    start_date  = str(start_date),
                    end_date    = str(end_date),
                    duration_days = duration,
                    comment     = comment
                )
                if result:
                    st.success("✅ Demande de congé soumise avec succès !")
                    if certificate and result.get("request_id"):
                        upload_certificate(result["request_id"],
                                         certificate.read(),
                                         certificate.name)
                        st.success("📎 Certificat médical uploadé.")
                else:
                    st.error("Erreur lors de la soumission.")

    # ── TAB 2: Document Request ───────────────────────────────────────────────
    with tab2:
        st.subheader("Nouvelle demande de document")

        with st.form("doc_form"):
            doc_type = st.selectbox("Type de document", [
                "Attestation de travail",
                "Attestation de salaire",
                "Lettre de congé",
                "Bulletin de paie",
                "Certificat de travail"
            ])
            purpose = st.text_input("Objet / Raison",
                                   placeholder="Ex: Dossier bancaire, demande de visa...")
            submit_doc = st.form_submit_button("Soumettre la demande",
                                             use_container_width=True)

        if submit_doc:
            result = submit_document_request(employee_id, doc_type, purpose)
            if result:
                st.success("✅ Demande de document soumise. Le service RH la traitera sous 48h.")
            else:
                st.error("Erreur lors de la soumission.")


def show_my_requests():
    st.title("📋 Mes demandes")
    st.divider()

    employee_id = st.session_state.employee_id

    tab1, tab2 = st.tabs(["🏖️ Congés", "📄 Documents"])

    # ── TAB 1: My leaves ──────────────────────────────────────────────────────
    with tab1:
        st.subheader("Mes demandes de congé")
        leaves = get_my_leaves(employee_id)

        if not leaves:
            st.info("Aucune demande de congé.")
        else:
            for leave in reversed(leaves):
                status_map = {
                    "Approved":        ("🟢", "Approuvée"),
                    "Rejected":        ("🔴", "Rejetée"),
                    "Pending_Manager": ("🟡", "En attente du manager"),
                    "Pending_HR":      ("🟠", "En attente RH")
                }
                icon, label = status_map.get(leave["status"], ("⚪", leave["status"]))

                with st.expander(f"{icon} {leave['leave_type']} — {leave['start_date']} au {leave['end_date']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Statut:** {label}")
                        st.markdown(f"**Durée:** {leave['duration_days']} jours")
                        st.markdown(f"**Soumis le:** {leave['submission_date']}")
                    with col2:
                        if leave.get("employee_comment"):
                            st.markdown(f"**Mon commentaire:** {leave['employee_comment']}")
                        if leave.get("manager_comment"):
                            st.markdown(f"**Réponse du manager:** {leave['manager_comment']}")

    # ── TAB 2: My documents ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Mes demandes de document")
        docs = get_my_documents(employee_id)

        if not docs:
            st.info("Aucune demande de document.")
        else:
            for doc in reversed(docs):
                status_map = {
                    "Pending":   ("🟡", "En attente"),
                    "Generated": ("🟢", "Généré"),
                    "Delivered": ("✅", "Livré")
                }
                icon, label = status_map.get(doc["status"], ("⚪", doc["status"]))

                with st.expander(f"{icon} {doc['document_type']} — {doc['request_date']}"):
                    st.markdown(f"**Statut:** {label}")
                    if doc.get("purpose"):
                        st.markdown(f"**Objet:** {doc['purpose']}")
                    if doc.get("generated_file_path"):
                        st.success("📥 Document disponible au téléchargement.")
                        st.markdown(f"**Fichier:** `{doc['generated_file_path']}`")