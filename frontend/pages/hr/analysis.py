import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/analysis"

def show_analysis():
    # Global verification clear notification 
    if "analysis_success" in st.session_state:
        st.success(st.session_state["analysis_success"], icon=":material/verified:")
        del st.session_state["analysis_success"]

    st.title(":material/analytics: Analyse de Documents par l'IA")
    st.subheader("Extraction intelligente et routage automatique d'actions")
    st.divider()

    # Get secure context from current HR login profile
    hr_city = st.session_state.get("city", "Casablanca")
    st.markdown(f"**Zone d'administration active :** :material/location_on: `{hr_city}`")

    # Check if the logged-in HR is from the main headquarters (Casablanca)
    if hr_city.lower() == "casablanca":
        tab1, tab2 = st.tabs([":material/cloud_upload: Justificatif Unique", ":material/folder_open: Importer Règlement"])
    else:
        # Non-HQ cities only see the document analysis tool
        tab1 = st.container()
        tab2 = None
        st.info("Les politiques globales de l'entreprise sont gérées centralement par le siège de Casablanca.", icon=":material/hub:")

    # ── TAB 1: RUNNING AI FILE CLASSIFICATION ────────────────────────────────
    with tab1:
        st.markdown("#### Déposer un justificatif externe ou un formulaire administratif (.pdf)")
        uploaded_file = st.file_uploader("Fichier PDF cible", type=["pdf"], key="analysis_doc_pdf")

        if uploaded_file is not None:
            if st.button(":material/robot: Lancer l'analyse cognitive", type="primary", use_container_width=True):
                with st.spinner("Extraction OCR et traitement Llama-3..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                        # Pass HR city via URL query string to enforce backend security isolation
                        response = requests.post(f"{API_URL}/upload?hr_city={hr_city}", files=files)
                        
                        if response.status_code == 200:
                            st.session_state["active_analysis"] = response.json()
                        else:
                            st.error(f"Erreur d'analyse : {response.text}")
                    except Exception as e:
                        st.error(f"Le serveur est inaccessible : {str(e)}")

        # ── INTERACTIVE ROUTER REGION ─────────────────────────────────────────
        if "active_analysis" in st.session_state:
            res = st.session_state["active_analysis"]
            
            # Scenario A: Security violation returned by backend
            if res.get("status") == "security_restricted":
                st.error(res.get("message"), icon=":material/gavel:")
                if st.button("Effacer l'analyse"):
                    del st.session_state["active_analysis"]
                    st.rerun()
                return

            st.divider()
            
            # Create a dictionary to map code strings to clean text
            action_mapping = {
                "create_leave_request": "Demande de Congé",
                "create_document_request": "Demande de Document",
                "manual_handling": "Traitement Manuel Recommandé"
            }
            raw_action = res.get("suggested_action")
            clean_action_phrase = action_mapping.get(raw_action, raw_action)

            # Render descriptive payload items safely using Markdown to prevent text clipping (...)
            # Render descriptive payload items safely using Markdown to prevent text clipping (...)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Type Détecté**")
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:#1f77b4;'>{res.get('document_type', 'Inconnu')}</p>", unsafe_allow_html=True)
            with c2:
                confidence_score = res.get("confidence", "Low")
                st.markdown("**Confiance de l'IA**")
                color = "#2ca02c" if confidence_score == "High" else "#d62728"
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:{color};'>{confidence_score}</p>", unsafe_allow_html=True)
            with c3:
                st.markdown("**Action Proposée**")
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:#1f77b4;'>{clean_action_phrase}</p>", unsafe_allow_html=True)

            st.info(f"**Résumé de l'IA :** {res.get('summary')}")

            # Splitting structural forms dynamically based on prefilled values
            form_data = res.get("prefilled_form")
            matched_emp = res.get("matched_employee")

            # ── CASE 1 & 2: AUTOMATED AI ROUTING PATHS ───────────────────────
            if clean_action_phrase != "Traitement Manuel Recommandé":
                with st.container(border=True):
                    st.markdown("### :material/edit_note: Formulaire de validation")
                    
                    if not matched_emp:
                        st.warning("L'IA n'a trouvé aucun profil d'employé correspondant dans votre base de données locale. Veuillez saisir l'ID manuellement.", icon=":material/person_search:")
                        target_emp_id = st.number_input("ID de l'employé concerné", value=0, step=1)
                    else:
                        st.success(f"Employé Identifié : **{matched_emp['name']}** `(ID: {matched_emp['employee_id']} - {matched_emp['department']})`", icon=":material/badge:")
                        target_emp_id = matched_emp['employee_id']

                    # ACTION TYPE A: LEAVE PROCESSING
                    if form_data and form_data.get("type") == "leave_request":
                        st.caption("Action : Création automatisée d'une demande de congé d'absence")
                        
                        val_leave_type = st.selectbox("Catégorie de congé", ["Sick", "Annual", "Maternity", "Unpaid"], index=0 if form_data.get("leave_type") == "Sick" else 1)
                        val_start = st.text_input("Date de début (AAAA-MM-JJ)", value=form_data.get("start_date") or "")
                        val_end = st.text_input("Date de fin (AAAA-MM-JJ)", value=form_data.get("end_date") or "")
                        val_days = st.number_input("Durée du congé (jours)", value=int(form_data.get("duration_days") or 1), step=1)
                        val_comment = st.text_area("Note de validation administrative", value=form_data.get("employee_comment") or "")

                        if st.button("Confirmer et Enregistrer le Congé (Pending_HR)", use_container_width=True, type="primary", icon=":material/edit_calendar:"):
                            payload = {
                                "employee_id": target_emp_id,
                                "leave_type": val_leave_type,
                                "start_date": val_start,
                                "end_date": val_end,
                                "duration_days": val_days,
                                "employee_comment": val_comment
                            }
                            conf = requests.post(f"{API_URL}/confirm-leave", json=payload)
                            if conf.status_code == 200:
                                st.session_state["analysis_success"] = "La demande de congé a été insérée directement dans le circuit de validation !"
                                del st.session_state["active_analysis"]
                                st.rerun()
                            else:
                                st.error(conf.text, icon=":material/error:")

                    # ACTION TYPE B: DOCUMENT REQUEST LOGGING
                    elif form_data and form_data.get("type") == "document_request":
                        st.caption("Action : Création automatisée d'une demande de pièce administrative")
                        
                        val_doc_type = st.text_input("Intitulé du document requis", value=form_data.get("document_type") or "Attestation de travail")
                        val_purpose = st.text_input("Motif d'édition spécifié", value=form_data.get("purpose") or "Usage Personnel")

                        if st.button("Confirmer et Ouvrir la Demande de Document", use_container_width=True, type="primary", icon=":material/description:"):
                            payload = {
                                "employee_id": target_emp_id,
                                "document_type": val_doc_type,
                                "purpose": val_purpose
                            }
                            conf = requests.post(f"{API_URL}/confirm-document", json=payload)
                            if conf.status_code == 200:
                                st.session_state["analysis_success"] = "La demande de document a été ajoutée et générée avec succès !"
                                del st.session_state["active_analysis"]
                                st.rerun()
                            else:
                                st.error(conf.text, icon=":material/error:")

           # ── CASE 3: FALLBACK MANUAL SEARCH & DROPDOWN WORKFLOW ───────────
            else:
                st.warning("L'IA n'a pas pu automatiser ce document. Veuillez utiliser la saisie manuelle ci-dessous.", icon=":material/gavel:")
                st.markdown("### Saisie Manuelle Administrative")
                
                BASE_URL = API_URL.replace("/analysis", "") 
                employees_list = []
                
                try:
                    emp_res = requests.get(f"{BASE_URL}/employees", headers={"X-City": hr_city})
                    if emp_res.status_code == 200:
                        raw_list = emp_res.json()
                        
                        # Let's inspect the first employee safely to see what the city key actually is
                        city_key = "city"
                        if raw_list and isinstance(raw_list[0], dict):
                            sample = raw_list[0]
                            if "branch" in sample:
                                city_key = "branch"
                            elif "ville" in sample:
                                city_key = "ville"
                        
                        # STRICT LOCAL FILTER: Keep only workers in the logged-in HR manager's city
                        employees_list = [
                            e for e in raw_list 
                            if str(e.get(city_key, "")).strip().lower() == hr_city.strip().lower()
                        ]
                        
                        # Micro-debug note to confirm filtering is working live
                        st.caption(f"Filtré localement : {len(employees_list)} employés trouvés pour la zone `{hr_city}` (sur {len(raw_list)} au total).")
                    else:
                        st.error(f"Erreur backend ({emp_res.status_code}) lors du chargement des employés.", icon=":material/database_error:")
                except Exception as e:
                    st.error("Impossible de se connecter à la table des employés.", icon=":material/cloud_off:")

                # ── RENDER FILTERED DROPDOWN ─────────────────────────────────
                col_emp, col_doc = st.columns(2)
                
                with col_emp:
                    if employees_list:
                        emp_map = {
                            f"{e['first_name']} {e['last_name']} (ID: {e['employee_id']} - {e.get('department', 'N/A')})": e 
                            for e in employees_list
                        }
                        
                        selected_name = st.selectbox(
                            "Rechercher un employé (Tapez pour filtrer)",
                            options=[""] + list(emp_map.keys()),
                            index=0,
                            placeholder="Saisissez un prénom ou nom..."
                        )
                        chosen_employee = emp_map.get(selected_name)
                    else:
                        st.error(f"Aucun employé disponible pour la filiale {hr_city}.", icon=":material/person_off:")
                        chosen_employee = None
                
                with col_doc:
                    manual_form_type = st.selectbox("Type de formulaire à ouvrir", options=["Demande de Document", "Demande de Congé"])
                    
                st.write("---")

                # Show visual confirmation if an employee is selected from the filter
                if chosen_employee:
                    st.success(f"Employé sélectionné : **{chosen_employee['first_name']} {chosen_employee['last_name']}** `(ID: {chosen_employee['employee_id']} - {chosen_employee['department']})`", icon=":material/badge:")

                # 3. DYNAMICALLY RENDER THE SPECIFIC FORM
                if chosen_employee:
                    if manual_form_type == "Demande de Document":
                        st.markdown(f"#### Formulaire : Création de Document Administratif")
                        doc_type = st.selectbox("Type de document requis", ["Attestation de travail", "Attestation de salaire", "Bulletin de paie", "Lettre de conge"])
                        purpose = st.text_input("Motif d'édition spécifié", value="Saisie manuelle RH")
                        
                        if st.button("Confirmer et Ouvrir la Demande de Document", use_container_width=True, icon=":material/description:"):
                            payload = {"employee_id": chosen_employee["employee_id"], "document_type": doc_type, "purpose": purpose}
                            with st.spinner("Génération..."):
                                res = requests.post(f"{API_URL}/confirm-document", json=payload)
                                if res.status_code == 200:
                                    st.session_state["analysis_success"] = "Le document a été généré manuellement avec succès !"
                                    del st.session_state["active_analysis"]
                                    st.rerun()
                                else:
                                    st.error(f"Erreur : {res.text}", icon=":material/error:")

                    elif manual_form_type == "Demande de Congé":
                        st.markdown(f"#### Formulaire : Enregistrement d'Absence / Congé")
                        leave_type = st.selectbox("Type de congé", ["Sick", "Annual", "Maternity", "Unpaid"])
                        c_col1, c_col2 = st.columns(2)
                        with c_col1:
                            start_date = st.date_input("Date de début")
                        with c_col2:
                            end_date = st.date_input("Date de fin")
                            
                        duration = st.number_input("Durée (Jours)", min_value=1, value=1, step=1)
                        comment = st.text_area("Commentaire / Justification", value="Saisie manuelle suite à absence")
                        
                        if st.button("Confirmer et Enregistrer le Congé", use_container_width=True, icon=":material/edit_calendar:"):
                            payload = {
                                "employee_id": chosen_employee["employee_id"], "leave_type": leave_type,
                                "start_date": str(start_date), "end_date": str(end_date),
                                "duration_days": duration, "employee_comment": comment
                            }
                            with st.spinner("Enregistrement..."):
                                res = requests.post(f"{API_URL}/confirm-leave", json=payload)
                                if res.status_code == 200:
                                    st.session_state["analysis_success"] = "La demande de congé manuelle a été enregistrée !"
                                    del st.session_state["active_analysis"]
                                    st.rerun()
                                else:
                                    st.error(f"Erreur : {res.text}", icon=":material/error:")
                else:
                    if employees_list:
                        st.info("Veuillez sélectionner le nom d'un employé dans la barre de recherche pour faire apparaître le formulaire associé.", icon=":material/arrow_upward:")

            if st.button("Annuler et rejeter l'analyse", use_container_width=True):
                del st.session_state["active_analysis"]
                st.rerun()

    # ── TAB 2: BULK COMPANY POLICIES UPLOADER ────────────────────────────────
    if tab2 is not None:
        with tab2:
            st.markdown("#### Entraîner la mémoire de l'assistant virtuel (Règlement Intérieur)")
            st.caption("Réservé au Siège Social : Mettez à jour la politique globale s'appliquant à l'ensemble des filiales.")
            
            rules_file = st.file_uploader("Fichier Règlement Intérieur (.pdf)", type=["pdf"], key="rules_uploader_key")
            
            if rules_file is not None:
                if st.button(":material/gavel: Analyser et Indexer le Règlement", use_container_width=True):
                    with st.spinner("Mise à jour du règlement général..."):
                        files = {"file": (rules_file.name, rules_file.getvalue(), "application/pdf")}
                        r_res = requests.post(f"{API_URL}/import-rules", files=files)
                        if r_res.status_code == 200:
                            st.success("Le règlement global de l'entreprise a été re-compilé et synchronisé !", icon=":material/check_circle:")
                        else:
                            st.error(f"Erreur : {r_res.text}", icon=":material/error:")