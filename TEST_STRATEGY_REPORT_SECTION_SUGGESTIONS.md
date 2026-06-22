# Stratégie de Tests et Validation Fonctionnelle (Backend/Frontend)

## 1. Objectif de la stratégie de test
- Décrire le but : garantir le bon fonctionnement des flux métier (soumission/validation), la cohérence Frontend–Backend, et la fiabilité de la partie IA (classification + extraction).
- Expliquer que les tests combinent validation API (FastAPI) et scénarios UI (Streamlit).

## 2. Périmètre fonctionnel testé
- Backend : routes FastAPI incluant **auth**, **employees**, **leaves**, **documents**, **dashboard**, **chat/chatbot**, et le module **document_analysis** (analyse documentaire).
- Frontend : pages Streamlit, notamment **HR analysis** (upload + routing automatique) et les formulaires de confirmation.

## 3. Environnements et données de test
- Définir l’environnement backend : FastAPI + MySQL (schéma via `Base.metadata.create_all`).
- Définir l’environnement IA : clé `GROQ_API_KEY`, modèle LLM.
- Définir les fichiers de test : PDFs fournis (ex: `files/uploads/`, `files/`, `documents/templates/`) + au moins un PDF par type logique (certificat médical, lettre/cv, attestation, etc.).
- Définir les données d’employés de test : au minimum 2 employés avec villes/branches différentes pour tester `security_restricted`.

## 4. Types de tests retenus
### 4.1 Tests fonctionnels (Black-box API)
- Test par requêtes HTTP : vérification des codes de retour, du schéma JSON, et de l’exécution des actions métier.

### 4.2 Tests d’intégration Frontend ↔ Backend
- Valider les scénarios complets : action UI → appel API → réaction UI.

### 4.3 Validation LLM / extraction documentaire (spécifique)
- Vérifier que l’API renvoie un **JSON valide** et conforme aux champs attendus.
- Vérifier la cohérence : `document_type`, `confidence`, `suggested_action`.

### 4.4 Tests de résilience / gestion d’erreur
- Vérifier les erreurs : PDF invalide, texte non extrait, échec JSON parse, absence d’employé matché, indisponibilité backend.

## 5. Critères de réussite (definition of done)
- **Backend** :
  - status HTTP attendu (200/400/422/500/502/404 selon le cas)
  - réponse JSON conforme (présence des clés attendues)
  - effet métier correct (création `LeaveRequest` / `DocumentRequest`)
- **Frontend** :
  - affichage correct (messages succès/erreur, affichage résumé, affichage du formulaire)
  - comportement correct selon `status` (`success` vs `security_restricted`)
  - téléchargement présent uniquement après génération

## 6. Stratégie de tests Backend (FastAPI) — document analysis
> Inclure un tableau “Scénarios ↔ Résultats attendus”.

### 6.1 Validation des entrées (Upload)
- Cas : upload d’un fichier non-PDF → **400** avec message “Only PDF files are accepted”.
- Cas : PDF dont le texte ne peut pas être extrait (texte < 20 caractères) → **400** avec message d’extraction.

### 6.2 Tests du routage métier via `suggested_action`
- Cas A : document de type congé / certificat médical →
  - API renvoie `suggested_action = create_leave_request`
  - `prefilled_form` contient `start_date`, `end_date`, `duration_days`, `employee_comment`
- Cas B : document de type demande d’attestation →
  - `suggested_action = create_document_request`
- Cas C : CV / lettre / autres →
  - `suggested_action = read_and_summarize`
  - aucune création DB automatique

### 6.3 Tests sécurité par ville (restriction)
- Cas : employé trouvé mais ville ≠ `hr_city` →
  - `status = security_restricted`
  - backend ne pré-remplit pas la soumission

### 6.4 Tests de confirmations DB
- `/analysis/confirm-leave` :
  - employee_id valide → insertion `LeaveRequest` avec `status = Pending_Manager`.
  - employee_id invalide → **404**.
- `/analysis/confirm-document` :
  - employee_id valide → insertion `DocumentRequest` avec `status = Pending`.
  - employee_id invalide → **404**.

### 6.5 Tests résilience IA (JSON invalide / format inattendu)
- Cas : l’IA retourne un format non-parseable → **500** avec message “AI could not parse the document…”.
- Cas : “import-rules” : LLM retourne JSON invalide → **502**.

## 7. Stratégie de tests Frontend (Streamlit) — HR analysis page
> Construire un tableau “Scénarios UI ↔ Résultats attendus”.

### 7.1 Upload & lancement analyse
- Upload PDF + clic “Lancer l’analyse cognitive” → appel `/analysis/upload` et affichage propre après `st.rerun()`.

### 7.2 Gestion des états UI
- Si `status = security_restricted` : message d’erreur + bouton “Effacer l’analyse” qui reset `uploader_key`.
- Si `status = success` : affichage de :
  - type de document
  - confiance (couleur)
  - résumé
  - orientation métier

### 7.3 Workflow “create_leave_request”
- Employé détecté : préremplissage + bouton “Confirmer et Enregistrer le Congé”.
- Employé non détecté : affichage du sélecteur manuel filtré par `hr_city`.
- Cas succès : confirmation UI + suppression `active_analysis`.
- Cas erreur serveur : message d’erreur avec `conf.text`.

### 7.4 Workflow “create_document_request”
- Création demande via `/documents/submit` → récupération `doc_request_id`.
- Génération via `/documents/{id}/generate`.
- Téléchargement via `/documents/{id}/download` et affichage `st.download_button`.

### 7.5 Mode “read_and_summarize” (consultatif)
- Vérifier le rendu de l’expander “Visualiser les informations extraites”.
- Vérifier que le message indique “aucune action automatisée” quand ce n’est pas un congé.

### 7.6 Téléversement des règles (import-rules)
- Upload PDF + clic “Analyser et Indexer le Règlement” → confirmation succès.
- Vérifier le comportement en cas d’erreur (status code non-200).

## 8. Tests d’intégration API complète (exemples de scénarios)
- Scénario 1 : upload certificat médical (ville Casablanca) → création leave → état Pending_Manager.
- Scénario 2 : upload certificat médical (ville différente) → security_restricted.
- Scénario 3 : upload CV/lettre → pas de création DB, affichage consultatif.
- Scénario 4 : demande attestation → création DocumentRequest → génération → download.

## 9. Mesure/validation qualitative de la performance IA
- Déclarer une grille simple (par exemple 5 documents) :
  - JSON structure : Oui/Non
  - `document_type` : Correct/Partiel/Faux (validation manuelle)
  - `suggested_action` : Correct/Incorrect
  - champs extraits : exactitude sur nom + dates (Oui/Non)
- Expliquer que l’IA est non déterministe : utiliser confiance High/Medium/Low + vérification humaine.

## 10. Limites
- Dépendance à : disponibilité du backend, MySQL, et service LLM.
- Extraction PDF dépend du format du PDF (texte vs scan).
- Non déterminisme LLM : tests répétables mais pas strictement identiques.

## 11. Preuves attendues dans le rapport
- Captures d’écran des écrans Streamlit : succès, security_restricted, génération document.
- Exemples de réponses JSON (1 à 2) pour document analysis.
- Tableau final “scénarios → résultats attendus → statut PASS/FAIL”.

---

## (Option) Modèle de tableau à copier-coller
| ID | Scénario | Entrées | Étapes | Résultat attendu | Statut |
|---|---|---|---|---|---|
| 1 | Upload non-PDF | file .docx | POST /analysis/upload | 400 uniquement PDF | PASS |
| 2 | Congé ville autorisée | certificat médical | upload + confirm | leave créée Pending_Manager | PASS |
| 3 | Congé ville restreinte | certificat médical | upload | security_restricted | PASS |
| 4 | CV | CV texte | upload | read_and_summarize, aucun insert | PASS |
| 5 | Attestation | attestation salaire | upload + generate + download | document téléchargé | PASS |

