import streamlit as st
from utils.api import send_chat_message, get_chat_history, clear_chat_history

# ── CONFIGURATION DES COULEURS (CSS) ──────────────────────────────────────────
st.markdown("""
    <style>
    /* 1. Titres en Navy Blue */
    h1, h2, h3 { color: #000080 !important; }
    
    /* 2. Couleur de l'icône ROBOT (Assistant) - Fond Navy Blue */
    [data-testid="stChatMessageAvatarCustom"] {
        background-color: #000080 !important; /* Navy Blue */
        color: white !important;
    }

    /* 3. Couleur de l'icône UTILISATEUR - Fond Gris Clair (Light Grey) */
    /* On cible le deuxième type d'avatar pour l'utilisateur */
    div[data-testimonial="stChatMessage"] svg {
        fill: #D3D3D3 !important;
    }
    
    /* Astuce pour forcer le gris sur l'avatar utilisateur (Pic 2) */
    .st-emotion-cache-1c7n2ri { 
        background-color: #D3D3D3 !important; /* Light Grey */
    }

    /* 4. Bordure de l'input chat en Navy Blue */
    .stChatInput:focus-within {
        border-color: #000080 !important;
    }

    /* 5. Bouton Effacer l'historique en Navy Blue */
    div.stButton > button {
        border-color: #000080 !important;
        color: #000080 !important;
        border-radius: 8px;
    }
    div.stButton > button:hover {
        background-color: #000080 !important;
        color: white !important;
    }
    
    /* 6. Fix pour les messages de succès (remplace le vert/cyan) */
    .stSuccess {
        background-color: rgba(0, 0, 128, 0.05) !important;
        color: #000080 !important;
        border: 1px solid #000080 !important;
    }
    </style>
""", unsafe_allow_html=True)


def show_chatbot():
    # Utilisation d'une icône Material pour le titre
    st.title(":material/robot_2: Assistant RH — HRPilot AI")
    st.markdown("Posez vos questions en langage naturel. Je peux aussi soumettre des demandes pour vous.")
    st.divider()

    employee_id = st.session_state.employee_id

    # ── Load history ──────────────────────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        history = get_chat_history(employee_id)
        st.session_state.chat_messages = []
        for h in history:
            st.session_state.chat_messages.append({"role": "user", "content": h["message"]})
            st.session_state.chat_messages.append({"role": "assistant", "content": h["response"]})

    # ── Display messages ──────────────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        # On définit l'avatar en fonction du rôle
        avatar_icon = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # ── Welcome message if empty ──────────────────────────────────────────────
    if not st.session_state.chat_messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(f"""
            Bonjour **{st.session_state.first_name}** ! Je suis votre assistant RH. Comment puis-je vous aider aujourd'hui ?
            
            **Vous pouvez me demander :**
            * :material/beach_access: Votre solde de congés
            * :material/description: Une attestation de travail
            * :material/assignment_ind: Le statut de vos demandes
            * :material/menu_book: Des questions sur le règlement intérieur
            """)

    # ── Chat input ────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Écrivez votre message..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("HRPilot AI analyse votre demande..."):
                result = send_chat_message(employee_id, prompt)

            if result:
                response = result.get("response", "Désolé, une erreur s'est produite.")
                action = result.get("action_taken")
                st.markdown(response)
                if action:
                    st.success(action)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
            else:
                st.error("Erreur de connexion au serveur.")

    # ── Clear button ──────────────────────────────────────────────────────────
    st.divider()
    # Ajout d'une icône Material au bouton pour le look Pro
    if st.button("Effacer l'historique", icon=":material/delete_sweep:"):
        clear_chat_history(employee_id)
        st.session_state.chat_messages = []
        st.rerun()