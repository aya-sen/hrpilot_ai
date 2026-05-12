import streamlit as st
from utils.api import get_pending_manager_leaves, manager_decision

def show_team_requests():
    # Injection du style Navy Blue pour la cohérence
    st.markdown("""
        <style>
        h1, h2, h3 { color: #000080 !important; }
        div.stButton > button:first-child {
            border-radius: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(":material/pending_actions: Demandes de l'équipe")
    st.divider()

    manager_id = st.session_state.employee_id
    # Utilisation de ta fonction pour récupérer les données
    pending_leaves = get_pending_manager_leaves(manager_id)
    #st.write(pending_leaves)

    if not pending_leaves:
        st.info("Aucune demande en attente de validation.", icon=":material/done_all:")
    else:
        for leave in pending_leaves:
            # Titre de l'expander avec le nom de l'employé et le type de congé

            from utils.api import get_employee
            emp_info = get_employee(leave['employee_id'])
            
            # On construit le nom proprement
            if emp_info:
                emp_name = f"{emp_info['first_name']} {emp_info['last_name']}"
            else:
                emp_name = f"Employé #{leave['employee_id']}"


            with st.expander(f":material/person: {emp_name} — {leave['leave_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**:material/calendar_month: Période:** Du {leave['start_date']} au {leave['end_date']}")
                    # Utilisation de request_id au lieu de id car c'est ce que renvoie ton API
                    st.caption(f"ID Demande: {leave['request_id']}") 
                
                with col2:
                    st.markdown(f"**:material/hourglass_empty: Durée:** {leave['duration_days']} jours")

                st.divider()
                
                # Champ pour que le manager puisse laisser un mot (optionnel selon ta fonction)
                manager_note = st.text_input("Commentaire (optionnel)", key=f"note_{leave['request_id']}")

                # Boutons d'action
                btn_approve, btn_reject = st.columns(2)
                
                with btn_approve:
                    # On utilise "Approved" pour le paramètre decision
                    if st.button("Approuver", key=f"app_{leave['request_id']}", icon=":material/check:", use_container_width=True):
                    # Changement ici : "approve" au lieu de "Approved"
                        res = manager_decision(int(leave['request_id']), "approve", manager_note)
                        if res:
                            st.success(f"Demande envoyée aux RH !")
                            st.rerun()

                with btn_reject:
                    # On utilise "Rejected" pour le paramètre decision
                    if st.button("Rejeter", key=f"rej_{leave['request_id']}", icon=":material/close:", use_container_width=True):
                        # Changement ici : "reject" au lieu de "Rejected"
                        res = manager_decision(int(leave['request_id']), "reject", manager_note)
                        if res:
                            st.warning(f"Demande rejetée.")
                            st.rerun()