import streamlit as st
import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
import treetaggerwrapper
import string

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')

# Liste de mots vides en français et lettres de l'alphabet
french_stopwords_list = nltk.corpus.stopwords.words('french')
alphabet_list = list(string.ascii_lowercase)

# Définir la fonction pour nettoyer le texte HTML
def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

# Définir la fonction pour extraire les mots et les n-grams
def extract_words_ngrams(text, n):
    tokens = nltk.word_tokenize(text)
    pos_tokens = treetaggerwrapper.make_tags(tagger.tag_text(text))

    filtered_tokens = []
    for token, pos_token in zip(tokens, pos_tokens):
        if token not in french_stopwords_list and token.isalpha() and isinstance(pos_token, treetaggerwrapper.Tag) and not (pos_token.pos.startswith('VER') or pos_token.pos.startswith('AUX')) and token not in alphabet_list:
            filtered_tokens.append(token)

    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens

# Interface utilisateur avec Streamlit
st.title("Analyse des mots et n-grams")

uploaded_file = st.file_uploader("Importer un fichier Excel", type="xlsx")

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    columns = df.columns.tolist()
    column_choice = st.selectbox("Sélectionner la colonne contenant le contenu HTML", columns)

    num_words = st.number_input("Nombre de mots uniques à garder", min_value=1, value=50)
    num_bigrams = st.number_input("Nombre de bigrammes à garder", min_value=1, value=30)
    num_trigrams = st.number_input("Nombre de trigrammes à garder", min_value=1, value=30)

    html_content = df[column_choice].tolist()
    cleaned_text = [clean_html(text) for text in html_content]

    tagger = treetaggerwrapper.TreeTagger(TAGDIR='C:/TreeTagger', TAGLANG='fr')

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

    with open("output.txt", "w", encoding='utf-8') as f:
        f.write("Mots les plus courants:\n")
        f.write(", ".join(most_common_words) + "\n\n")
        f.write("Bigrammes les plus courants:\n")
        f.write(", ".join(most_common_bigrams) + "\n\n")
        f.write("Trigrammes les plus courants:\n")
        f.write(", ".join(most_common_trigrams))

    with open("output.txt", "r", encoding='utf-8') as f:
        st.download_button('Télécharger le fichier de sortie', f, file_name='output.txt')

st.write("Veuillez importer un fichier Excel pour commencer.")
