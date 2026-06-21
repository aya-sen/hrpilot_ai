import streamlit as st
import requests
import json

from utils.api import import_rules

API_URL = "http://127.0.0.1:8000/analysis"

def show_analysis():
    # Notification claire en cas de succès global
    if "analysis_success" in st.session_state:
        st.success(st.session_state["analysis_success"], icon=":material/verified:")
        del st.session_state["analysis_success"]

    st.title(":material/analytics: Analyse de Documents par l'IA")
    st.subheader("Extraction cognitive, classification et traitement assisté")
    st.divider()

    # Récupération du contexte sécurisé de l'utilisateur RH connecté
    hr_city = st.session_state.get("city", "Casablanca")
    st.markdown(f"**Zone d'administration active :** :material/location_on: `{hr_city}`")

    # Vérification des privilèges du Siège Social (Casablanca)
    if hr_city.lower() == "casablanca":
        tab1, tab2 = st.tabs([":material/cloud_upload: Justificatif Unique", ":material/folder_open: Importer Règlement"])
    else:
        tab1 = st.container()
        tab2 = None
        st.info("Les politiques globales de l'entreprise sont gérées centralement par le siège de Casablanca.", icon=":material/hub:")

    # ── TAB 1: RUNNING AI FILE CLASSIFICATION ────────────────────────────────
    with tab1:
        st.markdown("#### Déposer un document externe (Ex: Certificat médical, CV, Contrat...)")
        
        # Initialisation d'une clé d'uploader dynamique en session pour pouvoir le forcer à se vider
        if "uploader_key" not in st.session_state:
            st.session_state["uploader_key"] = 1000

        uploaded_file = st.file_uploader(
            "Fichier PDF cible", 
            type=["pdf"], 
            key=f"analysis_doc_pdf_{st.session_state['uploader_key']}"
        )

        # 🚨 SÉCURITÉ ANTI-FANTÔME : Si l'utilisateur clique sur le "X", on nettoie instantanément l'affichage
        if uploaded_file is None:
            if "active_analysis" in st.session_state:
                del st.session_state["active_analysis"]
            if "analysis_success" in st.session_state:
                del st.session_state["analysis_success"]

        # L'analyse ne se lance que si un fichier est présent ET qu'aucune analyse n'est déjà en mémoire
        if uploaded_file is not None and "active_analysis" not in st.session_state:
            if st.button(":material/robot: Lancer l'analyse cognitive", type="primary", use_container_width=True):
                with st.spinner("Extraction de texte et traitement Llama-3..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                        response = requests.post(f"{API_URL}/upload?hr_city={hr_city}", files=files)
                        
                        if response.status_code == 200:
                            st.session_state["active_analysis"] = response.json()
                            st.rerun()  # On force le rafraîchissement pour afficher le résultat proprement
                        else:
                            st.error(f"Erreur d'analyse : {response.text}")
                    except Exception as e:
                        st.error(f"Le serveur est inaccessible : {str(e)}")

        # ── INTERACTIVE ROUTER REGION ─────────────────────────────────────────
        if "active_analysis" in st.session_state:
            res = st.session_state["active_analysis"]
            
            # Scénario de restriction de sécurité par ville
            if res.get("status") == "security_restricted":
                st.error(res.get("message"), icon=":material/gavel:")
                if st.button("Effacer l'analyse", icon=":material/delete:"):
                    del st.session_state["active_analysis"]
                    st.session_state["uploader_key"] += 1  # Incrémenter la clé vide instantanément le file_uploader
                    st.rerun()
                return

            st.divider()
            
            # Mapping mis à jour avec notre nouvelle logique
            action_mapping = {
                "create_leave_request": "Traitement Automatique (Congé)",
                "read_and_summarize": "Lecture & Analyse Consultative"
            }
            raw_action = res.get("suggested_action")
            clean_action_phrase = action_mapping.get(raw_action, raw_action)

            # Affichage des indicateurs de l'IA
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Type de Document**")
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:#1f77b4;'>{res.get('document_type', 'Inconnu')}</p>", unsafe_allow_html=True)
            with c2:
                confidence_score = res.get("confidence", "Low")
                st.markdown("**Confiance de l'IA**")
                color = "#2ca02c" if confidence_score == "High" else "#d62728"
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:{color};'>{confidence_score}</p>", unsafe_allow_html=True)
            with c3:
                st.markdown("**Orientation Métier**")
                st.markdown(f"<p style='font-size:20px; font-weight:bold; color:#ff7f0e;'>{clean_action_phrase}</p>", unsafe_allow_html=True)

            st.info(f"**Résumé analytique de l'IA :** {res.get('summary')}")

            form_data = res.get("prefilled_form")
            matched_emp = res.get("matched_employee")

            
            
            # ── MODE 1: AUTOMATED AI ROUTING PATH (Certificats Médicaux / Congés) ──
            # 1. Sécurisation immédiate de form_data
            safe_form_data = res.get("prefilled_form") or {} 

            if raw_action == "create_leave_request":
                with st.container(border=True):
                    st.markdown("### :material/edit_note: Formulaire d'Enregistrement")
                    
                    target_emp_id = None

                    # 2. SEUL BLOC D'IDENTIFICATION
                    if matched_emp:
                        st.success(f"Employé détecté : **{matched_emp['name']}**", icon=":material/badge:")
                        target_emp_id = matched_emp['employee_id']
                    else:
                        # Sélecteur manuel
                        emp_res = requests.get(f"{API_URL.replace('/analysis', '')}/employees", headers={"X-City": hr_city})
                        if emp_res.status_code == 200:
                            emp_list = [e for e in emp_res.json() if str(e.get("city", "")).lower() == hr_city.lower()]
                            emp_map = {f"{e['first_name']} {e['last_name']}": e for e in emp_list}
                            
                            selected = st.selectbox("Sélectionner l'employé :", options=[""] + list(emp_map.keys()))
                            if selected:
                                target_emp_id = emp_map[selected]['employee_id']

                    # 3. LE FORMULAIRE N'APPARAÎT QUE SI target_emp_id EST VALIDE
                    if target_emp_id:
                        st.caption("Action : Soumission du formulaire")
                        
                        # Création des inputs
                        val_leave_type = st.selectbox("Catégorie", ["Sick", "Annual", "Maternity", "Unpaid"])
                        
                        # On utilise bien safe_form_data ici
                        val_start = st.text_input("Début", value=safe_form_data.get("start_date", ""))
                        val_end = st.text_input("Fin", value=safe_form_data.get("end_date", ""))
                        val_days = st.number_input("Durée", value=int(safe_form_data.get("duration_days") or 1))
                        val_comment = st.text_area("Note", value=safe_form_data.get("employee_comment", ""))

                        # UN SEUL BOUTON pour tout gérer
                        if st.button("Confirmer et Enregistrer le Congé", use_container_width=True, type="primary"):
                            payload = {
                                "employee_id": target_emp_id,
                                "leave_type": val_leave_type,
                                "start_date": val_start,
                                "end_date": val_end,
                                "duration_days": val_days,
                                "employee_comment": val_comment
                            }
                            
                            try:
                                conf = requests.post(f"{API_URL}/confirm-leave", json=payload)
                                if conf.status_code == 200:
                                    st.session_state["analysis_success"] = "Le congé a été enregistré avec succès !"
                                    del st.session_state["active_analysis"]
                                    st.rerun()
                                else:
                                    st.error(f"Erreur serveur : {conf.text}")
                            except Exception as e:
                                st.error(f"Erreur de connexion : {str(e)}")
                    else:
                        st.info("Veuillez sélectionner un employé pour afficher le formulaire.")
            elif raw_action == "create_document_request":
                st.subheader(":material/description: Génération de document")
                # On réutilise ta logique d'employé identifié
                if matched_emp:
                    st.success(f"Employé détecté : {matched_emp['name']}")
                    doc_type = st.selectbox("Type de document", ["Attestation de travail", "Attestation de salaire", "Bulletin de paie", "Lettre de congé"])
                    if st.button("Générer le document"):
                        # Ton appel API ici
                        st.success("Document généré !")
                        del st.session_state["active_analysis"]
                        st.rerun()
            # ── MODE 2: CONSULTATIVE / ASSISTED WORKFLOW (CV, Contrats, Courriers) ──
            else:
                st.success("Analyse consultative terminée. Aucune action automatisée en base de données n'est requise pour ce type de document.", icon=":material/info:")
                
                with st.expander(":material/content_paste_search: Visualiser les informations extraites par l'IA", expanded=True):
                    extracted = res.get("extracted_data", {})
                    if extracted:
                        # Extraction des clés de manière propre et élégante
                        emp_name = extracted.get("employee_name")
                        purpose_text = extracted.get("purpose")
                        extra_details = extracted.get("any_other_relevant_field")

                        # Affichage structuré en langage naturel avec les icônes Material
                        if emp_name and emp_name != "NULL":
                            st.markdown(f":material/person: **Identité détectée :** {emp_name}")

                        if purpose_text and purpose_text != "NULL":
                            st.markdown(f":material/target: **Objectif / Motif identifié :** {purpose_text}")

                        if extra_details and extra_details != "NULL":
                            st.markdown(f":material/description: **Éléments contextuels clés :** {extra_details}")
                            
                        if not any([emp_name, purpose_text, extra_details]) or all(v == "NULL" for v in [emp_name, purpose_text, extra_details]):
                            st.caption("Aucune entité structurelle spécifique n'a été isolée dans ce document.")
                    else:
                        st.caption("Aucune donnée structurelle spécifique n'a été extraite.")
                if st.checkbox("Afficher la saisie manuelle si nécessaire"):
                    st.markdown("### Action RH Alternative (Saisie Manuelle)")
                    st.caption("Si ce document nécessite tout de même une action administrative, utilisez le sélecteur ci-dessous :")
                    
                    BASE_URL = API_URL.replace("/analysis", "") 
                    employees_list = []
                    
                    try:
                        emp_res = requests.get(f"{BASE_URL}/employees", headers={"X-City": hr_city})
                        if emp_res.status_code == 200:
                            raw_list = emp_res.json()
                            city_key = "city"
                            if raw_list and isinstance(raw_list[0], dict):
                                sample = raw_list[0]
                                if "branch" in sample: city_key = "branch"
                                elif "ville" in sample: city_key = "ville"
                            
                            # Filtre local strict par filiale
                            employees_list = [e for e in raw_list if str(e.get(city_key, "")).strip().lower() == hr_city.strip().lower()]
                            st.caption(f"Filtré localement : {len(employees_list)} employés trouvés pour la zone `{hr_city}`.")
                        else:
                            st.error(f"Erreur backend ({emp_res.status_code}) lors du chargement.", icon=":material/database_error:")
                    except Exception as e:
                        st.error("Impossible de se connecter à la table des employés.", icon=":material/cloud_off:")

                    col_emp, col_doc = st.columns(2)
                    with col_emp:
                        if employees_list:
                            emp_map = {f"{e['first_name']} {e['last_name']} ({e.get('department', 'N/A')})": e for e in employees_list}
                            selected_name = st.selectbox("Rechercher un employé local", options=[""] + list(emp_map.keys()), index=0, placeholder="Saisissez un nom...")
                            chosen_employee = emp_map.get(selected_name)
                        else:
                            st.error(f"Aucun employé disponible pour la filiale {hr_city}.", icon=":material/person_off:")
                            chosen_employee = None
                
                    with col_doc:
                        manual_form_type = st.selectbox("Type de formulaire à ouvrir", options=["Demande de Document", "Demande de Congé"])
                    
                    st.write("---")

                    if chosen_employee:
                        st.success(f"Employé sélectionné : **{chosen_employee['first_name']} {chosen_employee['last_name']}**", icon=":material/badge:")
                        
                        if manual_form_type == "Demande de Document":
                            st.markdown(f"#### Formulaire : Création de Document Administratif")
                            doc_type = st.selectbox("Type de document requis", ["Attestation de travail", "Attestation de salaire", "Bulletin de paie", "Lettre de conge"])
                            purpose = st.text_input("Motif d'édition spécifié", value="Saisie manuelle suite à relecture de pièce")
                            
                            if st.button("Confirmer et Générer le Document", use_container_width=True, icon=":material/description:"):
                                payload = {"employee_id": chosen_employee["employee_id"], "document_type": doc_type, "purpose": purpose}
                                res_doc = requests.post(f"{API_URL}/confirm-document", json=payload)
                                if res_doc.status_code == 200:
                                    st.session_state["analysis_success"] = "Le document requis a été consigné manuellement avec succès !"
                                    del st.session_state["active_analysis"]
                                    st.rerun()
                                else:
                                    st.error(f"Erreur : {res_doc.text}", icon=":material/error:")

                        elif manual_form_type == "Demande de Congé":
                            st.markdown(f"#### Formulaire : Enregistrement d'Absence / Congé")
                            leave_type = st.selectbox("Type de congé", ["Sick", "Annual", "Maternity", "Unpaid"])
                            c_col1, c_col2 = st.columns(2)
                            with c_col1: start_date = st.date_input("Date de début")
                            with c_col2: end_date = st.date_input("Date de fin")
                                
                            duration = st.number_input("Durée (Jours)", min_value=1, value=1, step=1)
                            comment = st.text_area("Commentaire / Justification", value="Enregistré manuellement après analyse de pièce")
                            
                            if st.button("Confirmer et Enregistrer le Congé Manuel", use_container_width=True, icon=":material/edit_calendar:"):
                                payload = {
                                    "employee_id": chosen_employee["employee_id"], "leave_type": leave_type,
                                    "start_date": str(start_date), "end_date": str(end_date),
                                    "duration_days": duration, "employee_comment": comment
                                }
                                res_leave = requests.post(f"{API_URL}/confirm-leave", json=payload)
                                if res_leave.status_code == 200:
                                    st.session_state["analysis_success"] = "La demande de congé manuelle a été enregistrée !"
                                    del st.session_state["active_analysis"]
                                    st.rerun()
                                else:
                                    i = st.error(f"Erreur : {res_leave.text}", icon=":material/error:")

                    # ── BOUTON ANNULER CORRIGÉ ET SÉCURISÉ ───────────────────────────────
                    if st.button("Annuler et rejeter l'analyse actuelle", use_container_width=True, icon=":material/cancel:", type="secondary"):
                        # 1. Suppression des états d'analyse
                        if "active_analysis" in st.session_state:
                            del st.session_state["active_analysis"]
                        if "analysis_success" in st.session_state:
                            del st.session_state["analysis_success"]
                        
                        # 2. Forcer le changement de clé de l'uploader pour tout vider d'un coup
                        if "uploader_key" not in st.session_state:
                            st.session_state["uploader_key"] = 1000
                        st.session_state["uploader_key"] += 1
                        
                        # 3. Rechargement propre de l'interface graphique
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
                        r_res = import_rules(rules_file.name, rules_file.getvalue())
                        if r_res.status_code == 200:
                            st.success("Le règlement global de l'entreprise a été synchronisé !", icon=":material/check_circle:")
                        else:
                            try: error_detail = r_res.json().get("detail", r_res.text)
                            except Exception: error_detail = r_res.text
                            st.error(f"Erreur de communication : {error_detail}", icon=":material/error:")