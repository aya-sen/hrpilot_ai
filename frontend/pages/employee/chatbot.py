import streamlit as st
from utils.api import send_chat_message, get_chat_history, clear_chat_history

def show_chatbot():
    st.title("🤖 Assistant RH — HRPilot AI")
    st.markdown("Posez vos questions en langage naturel. Je peux aussi soumettre des demandes pour vous.")
    st.divider()

    employee_id = st.session_state.employee_id

    # ── Load history ──────────────────────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        history = get_chat_history(employee_id)
        st.session_state.chat_messages = []
        for h in history:
            st.session_state.chat_messages.append({"role": "user",    "content": h["message"]})
            st.session_state.chat_messages.append({"role": "assistant","content": h["response"]})

    # ── Display messages ──────────────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Welcome message if empty ──────────────────────────────────────────────
    if not st.session_state.chat_messages:
        with st.chat_message("assistant"):
            st.markdown(f"Bonjour **{st.session_state.first_name}** ! 👋 Je suis votre assistant RH. Comment puis-je vous aider aujourd'hui ?\n\n"
                       "Vous pouvez me demander :\n"
                       "- 🏖️ Votre solde de congés\n"
                       "- 📄 Une attestation de travail\n"
                       "- 📋 Le statut de vos demandes\n"
                       "- 📖 Des questions sur le règlement intérieur")

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Écrivez votre message..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("En train de réfléchir..."):
                result = send_chat_message(employee_id, prompt)

            if result:
                response = result.get("response", "Désolé, une erreur s'est produite.")
                action   = result.get("action_taken")
                st.markdown(response)
                if action:
                    st.success(action)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
            else:
                st.error("Erreur de connexion au serveur.")

    # ── Clear button ──────────────────────────────────────────────────────────
    st.divider()
    if st.button("🗑️ Effacer l'historique", use_container_width=False):
        clear_chat_history(employee_id)
        st.session_state.chat_messages = []
        st.rerun()