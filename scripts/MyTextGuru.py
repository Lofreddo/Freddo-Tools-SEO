import streamlit as st
import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
from nltk.corpus import stopwords
import string

# Patch for treetaggerwrapper
import sys
import configparser
import importlib

def patch_treetaggerwrapper():
    import treetaggerwrapper
    if 'SafeConfigParser' in dir(configparser):
        treetaggerwrapper.configparser.SafeConfigParser = configparser.ConfigParser
    else:
        treetaggerwrapper.configparser.SafeConfigParser = configparser.ConfigParser

    importlib.reload(treetaggerwrapper)
    return treetaggerwrapper

treetaggerwrapper = patch_treetaggerwrapper()

def app():
    # Téléchargement de la liste de stop words et de 'punkt'
    nltk.download('stopwords')
    nltk.download('punkt')

    # Votre ami a suggéré d'utiliser cette liste de mots d'arrêt
    french_stopwords_list = nltk.corpus.stopwords.words('french')
    # Votre ami a suggéré d'utiliser cette liste de lettres de l'alphabet
    alphabet_list = list(string.ascii_lowercase)

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

        tagger = treetaggerwrapper.TreeTagger(TAGDIR='C:/TreeTagger', TAGLANG='fr')

        # Fonction pour extraire les mots et les n-grams
        def extract_words_ngrams(text, n):
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
