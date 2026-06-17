import streamlit as st
from datetime import date, timedelta
from utils.api import (download_document, submit_leave, submit_document_request,
                       get_my_leaves, get_my_documents,
                       get_employee, upload_certificate)

def show_requests():

    st.markdown("""
        <style>
        /* 1. Titres principaux */
        h1, h2, h3 { color: #000080 !important; }

        /* 2. Style général des onglets (Police et taille) */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem;
            font-weight: bold;
        }

        /* 3. Onglet ACTIF (Texte et Icône) */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] p,
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] span {
            color: #000080 !important;
        }

        /* 4. Barre de sélection sous l'onglet (Navy Blue) */
        .stTabs [data-baseweb="tab-list"] [data-baseweb="tab-highlight-border"] {
            background-color: #000080 !important;
        }

        /* 5. GESTION DU SURVOL (HOVER) - Pour enlever le rouge au passage de la souris */
        .stTabs [data-baseweb="tab-list"] button:hover p {
            color: #000080 !important;
        }
        
        /* Change la couleur de la bordure basse lors du survol
        .stTabs [data-baseweb="tab-list"] button:hover {
            border-bottom-color: #000080 !important;
        } */

        /* 6. Forcer la couleur Navy sur tous les éléments interactifs des onglets */
        .stTabs [data-baseweb="tab"] div {
            color: #000080 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(":material/edit_document: Soumettre une demande")
    st.divider()

    employee_id = st.session_state.employee_id
    employee    = get_employee(employee_id)

    tab1, tab2 = st.tabs([":material/beach_access: Demande de congé", ":material/description: Demande de document"])

    # ── TAB 1: Leave Request ──────────────────────────────────────────────────
    with tab1:
        st.subheader("Nouvelle demande de congé")

        if employee:
            st.info(f"Solde de congés disponible : **{employee['leave_balance_days']} jours**", icon=":material/info:")

        with st.form("leave_form"):
            leave_type = st.selectbox("Type de congé", [
                "Annual", "Sick", "Maternity", "Emergency"
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
                    st.success("Demande de congé soumise avec succès !")
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
                st.success("Demande de document soumise. Le service RH la traitera sous 48h.")
            else:
                st.error("Erreur lors de la soumission.")


def show_my_requests():
    
    st.markdown("""
        <style>
        /* Couleurs des titres */
        h1, h2, h3 { color: #000080 !important; }

        /* Texte des onglets et icônes */
        .stTabs [data-baseweb="tab-list"] button p, 
        .stTabs [data-baseweb="tab-list"] button span {
            color: #000080 !important;
        }


        /* Couleur au survol (Hover) */
        .stTabs [data-baseweb="tab-list"] button:hover {
            border-bottom-color: #000080 !important;
        }
        </style>
    """, unsafe_allow_html=True)


    st.title(":material/history: Suivi de mes demandes")
    st.divider()

    employee_id = st.session_state.employee_id

    tab1, tab2 = st.tabs([":material/beach_access: Congés", ":material/description: Documents"])

    # ── TAB 1: My leaves ──────────────────────────────────────────────────────
    with tab1:
        st.subheader("Mes demandes de congé")
        leaves = get_my_leaves(employee_id)

        if not leaves:
            st.info("Aucune demande de congé.", icon=":material/info:")
        else:
            for leave in reversed(leaves):
                status_map = {
                    "Approved":        (":material/check_circle:", "Approuvée", "#28a745"),
                    "Rejected":        (":material/cancel:", "Rejetée", "#dc3545"),
                    "Pending_Manager": (":material/schedule:", "En attente du manager", "#ffc107"),
                    "Pending_HR":      (":material/pending:", "En attente RH", "#fd7e14")
                }
                icon, label, color = status_map.get(leave["status"], (":material/help:", leave["status"], "grey"))

                # Intégration de l'icône dans le titre de l'expander
                with st.expander(f"{icon} {leave['leave_type']} — {leave['start_date']} au {leave['end_date']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        # Affichage du statut avec la couleur correspondante
                        st.markdown(f"**Statut:** <span style='color:{color};'>{icon} {label}</span>", unsafe_allow_html=True)
                        st.markdown(f"**:material/event: Durée:** {leave['duration_days']} jours")
                        st.markdown(f"**:material/today: Soumis le:** {leave['submission_date']}")
                    with col2:
                        if leave.get("employee_comment"):
                            st.markdown(f"**:material/chat: Mon commentaire:** {leave['employee_comment']}")
                        if leave.get("manager_comment"):
                            st.markdown(f"**:material/reply: Réponse du manager:** {leave['manager_comment']}")

    # ── TAB 2: My documents ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Mes demandes de document")
        docs = get_my_documents(employee_id)

        if not docs:
            st.info("Aucune demande de document.", icon=":material/info:")
        else:
            for doc in reversed(docs):
                status_map = {
                    "Pending":   (":material/schedule:",        "En attente",  "#ffc107"),
                    "Generated": (":material/settings_suggest:","Généré",      "#17a2b8"),
                    "Delivered": (":material/task_alt:",        "Livré",       "#28a745")
                }
                icon, label, color = status_map.get(
                    doc["status"], (":material/help:", doc["status"], "grey")
                )

                with st.expander(
                    f"{icon} {doc['document_type']} — {doc['request_date']}"
                ):
                    st.markdown(
                        f"**Statut:** <span style='color:{color};'>"
                        f"{icon} {label}</span>",
                        unsafe_allow_html=True
                    )
                    if doc.get("purpose"):
                        st.markdown(f"**:material/flag: Objet:** {doc['purpose']}")

                    # ── Download button ───────────────────────────────────────
                    if doc.get("generated_file_path"):
                        file_bytes = download_document(doc["doc_request_id"])
                        if file_bytes:
                            import os
                            filename = os.path.basename(doc["generated_file_path"])
                            st.download_button(
                                label    = ":material/download: Télécharger le document",
                                data     = file_bytes,
                                file_name = filename,
                                mime     = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key      = f"dl_{doc['doc_request_id']}"
                            )
                        else:
                            st.warning("Fichier temporairement indisponible.")