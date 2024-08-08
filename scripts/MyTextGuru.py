import pandas as pd
import nltk
from nltk import ngrams
from bs4 import BeautifulSoup
from collections import Counter
import spacy
import string
import subprocess
import sys

# Vérifier et télécharger le modèle de langue française de spaCy si nécessaire
def download_spacy_model(model_name):
    try:
        spacy.load(model_name)
        print(f"Model {model_name} loaded successfully.")
    except OSError:
        print(f"Model {model_name} not found. Downloading now...")
        subprocess.run([sys.executable, "-m", "spacy", "download", model_name])
        print(f"Model {model_name} downloaded successfully.")

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords')
nltk.download('punkt')

# Liste de mots vides en français et lettres de l'alphabet
french_stopwords_list = nltk.corpus.stopwords.words('french')
alphabet_list = list(string.ascii_lowercase)

# Nom du modèle de langue française de spaCy
model_name = 'fr_core_news_md'

# Télécharger le modèle de langue française
download_spacy_model(model_name)

# Charger le modèle de langue française de spaCy
nlp = spacy.load(model_name)
print(f"Model {model_name} loaded into spaCy.")

# Définir la fonction pour nettoyer le texte HTML
def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

# Définir la fonction pour extraire les mots et les n-grams
def extract_words_ngrams(text, n):
    doc = nlp(text)
    tokens = [token.text for token in doc]
    pos_tokens = [(token.text, token.pos_) for token in doc]

    filtered_tokens = []
    for token, pos in pos_tokens:
        if token not in french_stopwords_list and token.isalpha() and pos not in ['VERB', 'AUX'] and token not in alphabet_list:
            filtered_tokens.append(token)

    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens

# Définir la fonction principale pour traiter le fichier Excel et générer le fichier texte
def process_text_file(uploaded_file, column_choice, num_words, num_bigrams, num_trigrams):
    print("Processing text file...")
    df = pd.read_excel(uploaded_file)
    html_content = df[column_choice].tolist()
    cleaned_text = [clean_html(text) for text in html_content]

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

    output_text = "Mots les plus courants:\n"
    output_text += ", ".join(most_common_words) + "\n\n"
    output_text += "Bigrammes les plus courants:\n"
    output_text += ", ".join(most_common_bigrams) + "\n\n"
    output_text += "Trigrammes les plus courants:\n"
    output_text += ", ".join(most_common_trigrams)

    return output_text
