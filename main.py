import streamlit as st
import pandas as pd
from scripts.MyTextGuru import clean_html, extract_words_ngrams
from collections import Counter

# Interface Streamlit
st.title("MyTextGuru")

# Étape 1: Importer le fichier
uploaded_file = st.file_uploader("Importer un fichier Excel", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.write("Aperçu du fichier importé:")
    st.dataframe(df)

    # Étape 2: Sélectionner la colonne contenant les contenus HTML
    column_name = st.selectbox("Sélectionner la colonne contenant les contenus HTML", df.columns)
    
    if column_name:
        html_content = df[column_name].tolist()
        
        # Étape 3: Choisir le nombre de mots à garder
        num_words = st.number_input("Nombre de mots uniques à garder", min_value=1, value=50)
        num_bigrams = st.number_input("Nombre de bigrammes à garder", min_value=1, value=30)
        num_trigrams = st.number_input("Nombre de trigrammes à garder", min_value=1, value=30)

        # Nettoyer le texte HTML
        cleaned_text = [clean_html(text) for text in html_content]

        # Extraire les mots et les n-grams
        words = []
        bigrams = []
        trigrams = []
        for text in cleaned_text:
            words.extend(extract_words_ngrams(text, 1))
            bigrams.extend(extract_words_ngrams(text, 2))
            trigrams.extend(extract_words_ngrams(text, 3))

        # Compter les occurrences
        words_counter = Counter(words)
        bigrams_counter = Counter(bigrams)
        trigrams_counter = Counter(trigrams)

        # Prendre les mots/n-grams les plus courants
        most_common_words = [word for word, count in words_counter.most_common(num_words)]
        most_common_bigrams = [bigram for bigram, count in bigrams_counter.most_common(num_bigrams)]
        most_common_trigrams = [trigram for trigram, count in trigrams_counter.most_common(num_trigrams)]

        # Créer le contenu du fichier de sortie
        output_content = "Mots les plus courants:\n" + ', '.join(most_common_words) + "\n\n"
        output_content += "Bigrammes les plus courants:\n" + ', '.join(most_common_bigrams) + "\n\n"
        output_content += "Trigrammes les plus courants:\n" + ', '.join(most_common_trigrams) + "\n\n"

        # Étape 4: Enregistrer le fichier de sortie
        st.download_button(
            label="Télécharger les résultats",
            data=output_content,
            file_name="resultats.txt",
            mime="text/plain"
        )
