import streamlit as st
import os
from utils.api import get_pending_documents, generate_document

def show_documents():
    # ── 1. GLOBAL NOTIFICATION HANDLING ───────────────────────────────────────
    if "doc_success_msg" in st.session_state:
        st.success(st.session_state["doc_success_msg"], icon=":material/verified:")
        del st.session_state["doc_success_msg"]

    st.title(":material/description: Gestion des Documents")
    st.subheader("Demandes de documents administratifs en attente")
    st.divider()

    # ── 2. AUTOMATIC CITY FILTERING ───────────────────────────────────────────
    hr_city = st.session_state.get("city", "Casablanca")

    # ── 3. DATA ACQUISITION PIPELINE ──────────────────────────────────────────
    pending_docs = get_pending_documents(city=hr_city)

    if pending_docs is None:
        st.error("Impossible de charger les demandes de documents.", icon=":material/error:")
        return

    if not pending_docs:
        st.info(f"Aucune demande de document en attente pour la ville de **{hr_city}**.", icon=":material/folder_managed:")
        return

    st.markdown(f"Affichage de **{len(pending_docs)}** document(s) administratif(s) pour la ville de **{hr_city}**")

    # ── 4. CARD LOOP RENDERING ENGINE ─────────────────────────────────────────
    for doc in pending_docs:
        doc_request_id = doc.get("doc_request_id")
        emp_id = doc.get("employee_id")
        doc_type = doc.get("document_type", "Document")
        
        # Pull dynamic employee profile properties using your utility module
        from utils.api import get_employee
        emp_info = get_employee(emp_id)
        emp_name = f"{emp_info['first_name']} {emp_info['last_name']}" if emp_info else f"Employé #{emp_id}"
        
        # Design asset routing: Assign clean Material Icons based on category parameters
        doc_icon = ":material/payments:" if "salaire" in doc_type.lower() or "paie" in doc_type.lower() else ":material/badge:"
        
        # Component state keys bound to current city parameters to prevent visual duplication bugs
        ready_key = f"ready_path_{doc_request_id}_{hr_city}"
        is_generated = doc.get("status") == "Generated" or ready_key in st.session_state
        
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"#### {doc_icon} {doc_type}")
                st.markdown(f"**:material/person: Employé :** {emp_name} `(ID: {emp_id})` &nbsp;|&nbsp; **:material/fingerprint: Demande :** `{doc_request_id}`")
                st.markdown(f"**:material/calendar_today: Date Soumission :** {doc.get('request_date', '—')}")
                st.markdown(f"**:material/ads_click: Motif Spécifié :** *{doc.get('purpose') or 'Non spécifié.'}*")
                
                status_label = "Prêt pour téléchargement" if is_generated else "En attente de compilation"
                status_icon = ":material/check_circle:" if is_generated else ":material/hourglass_empty:"
                status_color = "green" if is_generated else "orange"
                st.markdown(f"**Statut :** {status_icon} :{status_color}[`{status_label}`]")

            with col2:
                st.markdown("<div style='padding-top: 25px;'>", unsafe_allow_html=True)
                
                # Setup a flag to check if HR generated it in this specific click action
                download_ready = False
                file_target_path = doc.get("generated_file_path") or st.session_state.get(ready_key)
                
                # EXECUTION ROUTE A: Handle primary document assembly
                if not is_generated:
                    if st.button(":material/settings_applications: Générer le fichier", key=f"gen_{doc_request_id}_{hr_city}", use_container_width=True, type="primary"):
                        with st.spinner("Génération du document Word..."):
                            res = generate_document(doc_request_id=doc_request_id)
                            
                        if res and (res.get("status") == "Generated" or "file_path" in res or "generated_file_path" in res):
                            file_target_path = res.get("file_path") or res.get("generated_file_path")
                            st.session_state[ready_key] = file_target_path
                            st.session_state["doc_success_msg"] = f"Le document '{doc_type}' pour {emp_name} a été généré avec succès !"
                            
                            # Toggle flag true so the download button presents itself immediately on click
                            download_ready = True 
                        else:
                            st.error("Échec du traitement du fichier.", icon=":material/gavel:")
                
                # EXECUTION ROUTE B: Expose compiled artifact download mechanics
                if is_generated or download_ready:
                    if file_target_path and os.path.exists(file_target_path):
                        try:
                            with open(file_target_path, "rb") as word_file:
                                binary_contents = word_file.read()
                            
                            st.download_button(
                                label=":material/download: Télécharger (.docx)",
                                data=binary_contents,
                                file_name=os.path.basename(file_target_path),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_{doc_request_id}_{hr_city}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error("Erreur de lecture.", icon=":material/error:")
                    else:
                        st.error("Fichier introuvable.", icon=":material/folder_off:")
                        
                st.markdown("</div>", unsafe_allow_html=True)