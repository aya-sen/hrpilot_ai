import streamlit as st
from utils.api import get_pending_manager_leaves, manager_decision, get_employee, get_team_availability

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

    if not pending_leaves:
        st.info("Aucune demande en attente de validation.", icon=":material/done_all:")
    else:
        for leave in pending_leaves:
            # Récupération des infos de l'employé
            emp_info = get_employee(leave['employee_id'])
            
            # On construit le nom proprement
            if emp_info:
                emp_name = f"{emp_info['first_name']} {emp_info['last_name']}"
                emp_dept = emp_info.get('department')
                emp_city = emp_info.get('city')
            else:
                emp_name = f"Employé #{leave['employee_id']}"
                emp_dept = None
                emp_city = None

            with st.expander(f":material/person: {emp_name} — {leave['leave_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**:material/calendar_month: Période:** Du {leave['start_date']} au {leave['end_date']}")
                    st.caption(f"ID Demande: {leave['request_id']}") 
                
                with col2:
                    st.markdown(f"**:material/hourglass_empty: Durée:** {leave['duration_days']} jours")

                # ─── 📊 INJECTION : INDICATEUR DE CHARGE & CAPACITÉ ───
                if emp_dept and emp_city:
                    availability_data = get_team_availability(
                        department=emp_dept,
                        city=emp_city,
                        start_date=str(leave['start_date']),
                        end_date=str(leave['end_date'])
                    )
                    
                    if availability_data:
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("##### :material/analytics: Indicateur de Charge de l'Équipe")
                        
                        team_size = availability_data.get("team_size", 1)
                        absent_count = availability_data.get("absent_during_period", 0)
                        available_count = availability_data.get("available", 1)
                        absence_rate = (absent_count / team_size * 100) if team_size > 0 else 0
                        
                        # Affichage des indicateurs chiffrés
                        m_col1, m_col2, m_col3 = st.columns(3)
                        m_col1.metric("Effectif Total", f"{team_size} pers.")
                        m_col2.metric("Absences Clés", f"{absent_count} pers.", delta=f"{absence_rate:.0f}% indispo.", delta_color="inverse")
                        m_col3.metric("Disponibles", f"{available_count} pers.")
                        
                        # Affichage de l'alerte d'aide à la décision
                        if availability_data.get("warning"):
                            st.error(
                                f"Le seuil d'absences simultanées est dépassé pour le département **{emp_dept}** à **{emp_city}** sur cette période !",
                                icon=":material/gavel:"
                            )
                        elif absence_rate >= 50:
                            st.warning(
                                "Moins de 50% de l'équipe locale est disponible. Risque de surcharge.",
                                icon=":material/warning:"
                            )
                        else:
                            st.success(
                                "L'effectif disponible est suffisant pour couvrir la charge de travail.",
                                icon=":material/check_circle:"
                            )
                st.divider()
                
                # Champ pour que le manager puisse laisser un mot
                manager_note = st.text_input("Commentaire (optionnel)", key=f"note_{leave['request_id']}")

                # Boutons d'action
                btn_approve, btn_reject = st.columns(2)
                
                with btn_approve:
                    if st.button("Approuver", key=f"app_{leave['request_id']}", icon=":material/check:", use_container_width=True):
                        res = manager_decision(int(leave['request_id']), "approve", manager_note)
                        if res:
                            st.success(f"Demande envoyée aux RH !")
                            st.rerun()

                with btn_reject:
                    if st.button("Rejeter", key=f"rej_{leave['request_id']}", icon=":material/close:", use_container_width=True):
                        res = manager_decision(int(leave['request_id']), "reject", manager_note)
                        if res:
                            st.warning(f"Demande rejetée.")
                            st.rerun()