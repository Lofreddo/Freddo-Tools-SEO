import pandas as pd
import nltk
from nltk import ngrams, pos_tag, word_tokenize
from bs4 import BeautifulSoup
from collections import Counter
import string

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
