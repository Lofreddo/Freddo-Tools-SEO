import streamlit as st
import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords
import spacy
import string
from io import BytesIO

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')

# Liste de mots d'arrêt
french_stopwords_list = set(nltk.corpus.stopwords.words('french'))
# Liste de lettres de l'alphabet
alphabet_list = set(string.ascii_lowercase)

# Charger le modèle de langue français de spacy
nlp = spacy.load('fr_core_news_sm')

def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

def extract_words_ngrams(text, n):
    doc = nlp(text)
    filtered_tokens = [
        token.text for token in doc 
        if token.text not in french_stopwords_list 
        and token.is_alpha 
        and token.pos_ not in ['VERB', 'AUX'] 
        and token.text not in alphabet_list
    ]

    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens

def app():
    st.title("MyTextGuru")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        column = st.selectbox("Sélectionnez la colonne contenant 'hn_content'", df.columns)
        
        if st.button("Exécuter le script"):
            html_content = df[column].tolist()
            
            cleaned_text = [clean_html(text) for text in html_content]
            
            num_words = 50
            num_bigrams = 30
            num_trigrams = 30

            words = []
            bigrams = []
            trigrams = []
            for text in cleaned_text:
                words.extend(extract_words_ngrams(text, 1))
                bigrams.extend(extract_words_ngrams(text, 2))
                trigrams.extend(extract_words_ngrams(text, 3))

            words_counter = Counter(words)
            bigrams_counter = Counter(bigrams)
            trigrams_counter = Counter(trigrams)

            most_common_words = [word for word, count in words_counter.most_common(num_words)]
            most_common_bigrams = [bigram for bigram, count in bigrams_counter.most_common(num_bigrams)]
            most_common_trigrams = [trigram for trigram, count in trigrams_counter.most_common(num_trigrams)]

            df['Mots les plus courants'] = ', '.join(most_common_words)
            df['Bigrammes les plus courants'] = ', '.join(most_common_bigrams)
            df['Trigrammes les plus courants'] = ', '.join(most_common_trigrams)

            st.write(df)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            
            st.download_button(
                label="Télécharger les résultats en Excel",
                data=output,
                file_name="resultats_mytextguru.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
