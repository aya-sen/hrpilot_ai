import streamlit as st
from utils.api import get_pending_hr_leaves, hr_approve_leave, manager_decision

def show_leaves():
    # ── 1. GLOBAL NOTIFICATION HANDLING ───────────────────────────────────────
    # Displays top-level feedback messages after page reloads
    if "leave_success_msg" in st.session_state:
        st.success(st.session_state["leave_success_msg"], icon=":material/verified:")
        del st.session_state["leave_success_msg"]

    st.title(":material/beach_access: Gestion des Congés")
    st.subheader("Demandes en attente de validation RH")
    st.divider()

    # ── 2. AUTOMATIC CITY FILTERING ───────────────────────────────────────────
    # Pulls the flat session state key directly saved by your login screen
    hr_city = st.session_state.get("city", "Casablanca")

    # ── 3. DATA ACQUISITION PIPELINE ──────────────────────────────────────────
    # Connects to your backend route passing the filtered city parameter directly
    pending_hr_requests = get_pending_hr_leaves(city=hr_city)
    
    if pending_hr_requests is None:
        st.error("Impossible de charger les demandes de congés.", icon=":material/error:")
        return

    if not pending_hr_requests:
        st.info(f"Aucune demande de congé en attente de validation RH pour la ville de **{hr_city}**.", icon=":material/assignment_turned_in:")
        return

    st.markdown(f"Affichage de **{len(pending_hr_requests)}** demande(s) pour la ville de **{hr_city}**")

    # ── 4. CARD LOOP RENDERING ENGINE ─────────────────────────────────────────
    for req in pending_hr_requests:
        req_id = req.get("request_id")
        
        # Build employee profile context cleanly
        first_name = req.get("first_name", "")
        last_name = req.get("last_name", "")
        emp_name = f"{first_name} {last_name}".strip() or f"Employé #{req.get('employee_id')}"
        dept = req.get("department", "—")
        duration = req.get("duration_days", 0)
        
        # Professional UI layout label using Material Icon formatting
        card_label = f":material/person: {emp_name} ({dept}) — {duration} jours"
        
        with st.expander(card_label):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**:material/info: Détails de l'absence**")
                st.write(f"**Type de congé :** {req.get('leave_type', 'Annual')}")
                st.write(f"**Période :** Du `{req.get('start_date')}` au `{req.get('end_date')}`")
                st.write(f"**Commentaire :** *{req.get('employee_comment') or 'Aucun message.'}*")
                
            with col2:
                st.markdown("**:material/account_balance_wallet: Droits Restants**")
                st.metric(label="Solde actuel", value=f"{req.get('leave_balance_days', '—')} jrs")

            st.markdown("---")
            
            # Action Button Layout Elements
            btn_col1, btn_col2 = st.columns(2)
            
            # Use unique keys combined with the current city scope to avoid component conflicts
            reject_state_key = f"reject_panel_{req_id}_{hr_city}"
            if reject_state_key not in st.session_state:
                st.session_state[reject_state_key] = False

            # Approval Processing Interaction Block
            with btn_col1:
                if st.button(":material/check_circle: Valider la demande", key=f"app_{req_id}_{hr_city}", use_container_width=True, type="primary"):
                    result = hr_approve_leave(request_id=req_id)
                    if result:
                        st.session_state["leave_success_msg"] = f"La demande de {emp_name} a été approuvée avec succès !"
                        st.rerun()
                    else:
                        st.session_state[f"error_{req_id}_{hr_city}"] = "Échec lors de la validation. Vérifiez le solde disponible."

                if f"error_{req_id}_{hr_city}" in st.session_state:
                    st.markdown("")
                    st.error(st.session_state[f"error_{req_id}_{hr_city}"], icon=":material/error:")
                    del st.session_state[f"error_{req_id}_{hr_city}"]

            # Rejection Form Initialization Container Toggle
            with btn_col2:
                if st.button(":material/cancel: Rejeter la demande", key=f"rej_trigger_{req_id}_{hr_city}", use_container_width=True):
                    st.session_state[reject_state_key] = True

            # Form Display Loop for Rejections
            if st.session_state[reject_state_key]:
                st.markdown("")
                with st.container(border=True):
                    st.markdown("**:material/comment_bank: Formulaire de refus**")
                    reason = st.text_area("Motif du rejet *", key=f"text_{req_id}_{hr_city}", placeholder="Saisissez la raison obligatoire du refus...")
                    
                    sub1, sub2 = st.columns(2)
                    with sub1:
                        if st.button("Confirmer le Refus", key=f"confirm_fail_{req_id}_{hr_city}", use_container_width=True, type="primary"):
                            if not reason.strip():
                                st.warning("Veuillez remplir le motif du rejet.", icon=":material/warning:")
                            else:
                                res = manager_decision(request_id=int(req_id), decision="reject", comment=reason.strip())
                                if res:
                                    st.session_state[reject_state_key] = False
                                    st.session_state["leave_success_msg"] = f"La demande de {emp_name} a été rejetée."
                                    st.rerun()
                                else:
                                    st.error("Erreur serveur lors de l'enregistrement.", icon=":material/error:")
                    with sub2:
                        if st.button("Annuler", key=f"close_panel_{req_id}_{hr_city}", use_container_width=True):
                            st.session_state[reject_state_key] = False
                            st.rerun()