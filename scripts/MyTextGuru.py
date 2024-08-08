import pandas as pd
import nltk
from nltk import ngrams, pos_tag, word_tokenize
from bs4 import BeautifulSoup
from collections import Counter
import string
import streamlit as st

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# Définir les listes de mots d'arrêt et de lettres de l'alphabet
french_stopwords_list = nltk.corpus.stopwords.words('french')
alphabet_list = list(string.ascii_lowercase)

# Fonction pour nettoyer le texte HTML
def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

# Fonction pour extraire les mots et les n-grams
def extract_words_ngrams(text, n):
    tokens = word_tokenize(text)
    pos_tokens = pos_tag(tokens)
    
    # Ignorer les mots vides, non alphabétiques, les verbes, les auxiliaires et les lettres seules
    filtered_tokens = [token for token, pos in pos_tokens if token not in french_stopwords_list and token.isalpha() and pos not in ['VB', 'VBP', 'VBZ', 'VBD', 'VBG', 'VBN'] and token not in alphabet_list]
    
    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens

def main():
    st.title("Analyseur de texte HTML")

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
