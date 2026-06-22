- [ ] Fix Streamlit HR “Générer le document” -> create request -> generate -> show download button
- [ ] Ensure correct backend routes are used (document create endpoint + PUT /documents/{id}/generate)
- [ ] Implement local “Télécharger” button using st.download_button with generated file bytes
- [ ] Validate by running Streamlit and clicking generate
- [ ] If backend download returns FileResponse, switch to GET /documents/{id}/download for bytes

