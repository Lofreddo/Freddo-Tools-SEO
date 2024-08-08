import streamlit as st
import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
import treetaggerwrapper
import string
import io

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')

# Liste de mots d'arrêt
french_stopwords_list = nltk.corpus.stopwords.words('french')

# Liste de lettres de l'alphabet
alphabet_list = list(string.ascii_lowercase)

# Fonction pour nettoyer le texte HTML
def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

# Fonction pour extraire les mots et les n-grams
def extract_words_ngrams(text, n, tagger):
    tokens = nltk.word_tokenize(text)
    pos_tokens = treetaggerwrapper.make_tags(tagger.tag_text(text))

    # Ignore les mots vides, non alphabétiques, les verbes, les auxiliaires et les lettres seules
    filtered_tokens = []
    for token, pos_token in zip(tokens, pos_tokens):
        if token not in french_stopwords_list and token.isalpha() and isinstance(pos_token, treetaggerwrapper.Tag) and not (pos_token.pos.startswith('VER') or pos_token.pos.startswith('AUX')) and token not in alphabet_list:
            filtered_tokens.append(token)

    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens
    def app():
    st.title("MyTextGuru")

    # Upload du fichier Excel
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        # Sélection de la colonne contenant "hn_content"
        column = st.selectbox("Sélectionnez la colonne contenant 'hn_content'", df.columns)
        
        if st.button("Exécuter le script"):
            # Initialisation du tagger (à adapter selon votre configuration)
            tagger = treetaggerwrapper.TreeTagger(TAGDIR='C:/TreeTagger', TAGLANG='fr')
            
            html_content = df[column].tolist()
            
            # Nettoyer le texte HTML
            cleaned_text = [clean_html(text) for text in html_content]
            
            # Nombre de mots/n-grams pour chaque colonne
            num_words = 50
            num_bigrams = 30
            num_trigrams = 30

            # Extraire les mots et les n-grams
            words = []
            bigrams = []
            trigrams = []
            for text in cleaned_text:
                words.extend(extract_words_ngrams(text, 1, tagger))
                bigrams.extend(extract_words_ngrams(text, 2, tagger))
                trigrams.extend(extract_words_ngrams(text, 3, tagger))

            # Compter les occurrences
            words_counter = Counter(words)
            bigrams_counter = Counter(bigrams)
            trigrams_counter = Counter(trigrams)

            # Prendre les mots/n-grams les plus courants
            most_common_words = [word for word, count in words_counter.most_common(num_words)]
            most_common_bigrams = [bigram for bigram, count in bigrams_counter.most_common(num_bigrams)]
            most_common_trigrams = [trigram for trigram, count in trigrams_counter.most_common(num_trigrams)]

            # Ajouter les mots/n-grams les plus courants au DataFrame
            df['Mots les plus courants'] = ', '.join(most_common_words)
            df['Bigrammes les plus courants'] = ', '.join(most_common_bigrams)
            df['Trigrammes les plus courants'] = ', '.join(most_common_trigrams)

            # Afficher les résultats
            st.write(df)

            # Export des résultats en Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            
            st.download_button(
                label="Télécharger les résultats en Excel",
                data=output,
                file_name="resultats_mytextguru.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
