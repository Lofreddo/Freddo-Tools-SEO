import streamlit as st
from scripts.MyTextGuru import process_text_file

st.title("Analyse des mots et n-grams")

uploaded_file = st.file_uploader("Importer un fichier Excel", type="xlsx")

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    columns = df.columns.tolist()
    column_choice = st.selectbox("Sélectionner la colonne contenant le contenu HTML", columns)

    num_words = st.number_input("Nombre de mots uniques à garder", min_value=1, value=50)
    num_bigrams = st.number_input("Nombre de bigrammes à garder", min_value=1, value=30)
    num_trigrams = st.number_input("Nombre de trigrammes à garder", min_value=1, value=30)

    if st.button("Analyser"):
        output_text = process_text_file(uploaded_file, column_choice, num_words, num_bigrams, num_trigrams)

        st.text_area("Résultats de l'analyse", output_text, height=300)

        st.download_button(
            label="Télécharger le fichier de sortie",
            data=output_text,
            file_name="output.txt",
            mime="text/plain"
        )

st.write("Veuillez importer un fichier Excel pour commencer.")
