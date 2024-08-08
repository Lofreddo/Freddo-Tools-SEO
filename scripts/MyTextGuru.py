import streamlit as st
import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords
import spacy
import string

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')

# Votre ami a suggéré d'utiliser cette liste de mots d'arrêt
french_stopwords_list = nltk.corpus.stopwords.words('french')
# Votre ami a suggéré d'utiliser cette liste de lettres de l'alphabet
alphabet_list = list(string.ascii_lowercase)

# Charger le modèle de langue français de spacy
nlp = spacy.load('fr_core_news_sm')

def app():
    # Interface Streamlit pour charger le fichier Excel
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        html_content = df['hn_content'].tolist()

        # Fonction pour nettoyer le texte HTML
        def clean_html(text):
            if isinstance(text, str):
                soup = BeautifulSoup(text, "html.parser")
                return soup.get_text().lower()
            else:
                return ""

        # Nettoyer le texte HTML
        cleaned_text = [clean_html(text) for text in html_content]

        # Fonction pour extraire les mots et les n-grams
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

        # Nombre de mots/n-grams que vous voulez pour chaque colonne
        num_words = st.number_input('Nombre de mots les plus courants à extraire', value=50)
        num_bigrams = st.number_input('Nombre de bigrammes les plus courants à extraire', value=30)
        num_trigrams = st.number_input('Nombre de trigrammes les plus courants à extraire', value=30)

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

        # Afficher les résultats dans Streamlit
        st.write("Mots les plus courants:", ', '.join(most_common_words))
        st.write("Bigrammes les plus courants:", ', '.join(most_common_bigrams))
        st.write("Trigrammes les plus courants:", ', '.join(most_common_trigrams))

        # Ajouter les mots/n-grams les plus courants au DataFrame
        df['Mots les plus courants'] = ', '.join(most_common_words)
        df['Bigrammes les plus courants'] = ', '.join(most_common_bigrams)
        df['Trigrammes les plus courants'] = ', '.join(most_common_trigrams)

        # Enregistrer le DataFrame dans un nouveau fichier Excel
        df.to_excel('nouveau_fichier.xlsx', index=False)
        st.write("Le fichier a été enregistré sous le nom 'nouveau_fichier.xlsx'. Vous pouvez le télécharger en utilisant le lien ci-dessous.")
        st.download_button(label="Télécharger le fichier Excel", data=df.to_excel(index=False), file_name='nouveau_fichier.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
