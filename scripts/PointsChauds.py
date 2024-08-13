import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Initialisation du lemmatizer
lemmatizer = WordNetLemmatizer()

# Fonction pour obtenir le lemme d'un mot
def get_lemma(word):
    lemma = lemmatizer.lemmatize(word, pos='v')  # Lemmatisation en tant que verbe
    if lemma == word:  # Si le lemme en tant que verbe ne change rien, essayer en tant que nom
        lemma = lemmatizer.lemmatize(word, pos='n')
    return lemma

# Fonction pour vérifier la présence du mot-clé dans une balise spécifique
def check_keyword_in_tag(soup, tag, keyword):
    tags = soup.find_all(tag)
    for t in tags:
        if keyword_in_text(t.get_text(), keyword):
            return "Oui"
    return "Non"

# Fonction pour vérifier le mot-clé avec tolérance pour les variations
def keyword_in_text(text, keyword):
    # Tokenisation et lemmatisation des mots du mot-clé
    keyword_parts = [get_lemma(part) for part in word_tokenize(keyword)]
    
    # Création du motif de recherche avec tolérance de 0 à 5 caractères entre les mots
    # Respect de l'ordre des mots
    pattern = r'\b' + r'.{0,5}'.join(map(re.escape, keyword_parts)) + r'\b'
    
    # Lemmatisation du texte de la balise avant la recherche
    lemmatized_text = " ".join([get_lemma(word) for word in word_tokenize(text)])
    
    # Recherche du motif dans le texte
    return re.search(pattern, lemmatized_text, re.IGNORECASE) is not None

# Fonction principale pour l'application Streamlit
def main():
    st.title("Vérification de mot-clé dans des pages web")

    # Chargement du fichier xlsx
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write("Aperçu du fichier :")
        st.dataframe(df)

        # Sélection des colonnes
        keyword_column = st.selectbox("Sélectionnez la colonne contenant les mots-clés", df.columns)
        url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)

        if st.button("Lancer le crawl"):
            # Initialisation des nouvelles colonnes
            df['Balise Title'] = ''
            df['H1'] = ''
            df['Hn'] = ''

            for index, row in df.iterrows():
                keyword = row[keyword_column]
                url = row[url_column]

                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Vérification du mot-clé dans les différentes balises
                    df.at[index, 'Balise Title'] = check_keyword_in_tag(soup, 'title', keyword)
                    df.at[index, 'H1'] = check_keyword_in_tag(soup, 'h1', keyword)
                    df.at[index, 'Hn'] = "Oui" if any(check_keyword_in_tag(soup, tag, keyword) == "Oui" for tag in ['h2', 'h3', 'h4']) else "Non"

                except requests.exceptions.RequestException as e:
                    st.error(f"Erreur pour l'URL {url}: {e}")
                    df.at[index, 'Balise Title'] = 'Erreur'
                    df.at[index, 'H1'] = 'Erreur'
                    df.at[index, 'Hn'] = 'Erreur'

            # Affichage du résultat
            st.write("Résultat du crawl :")
            st.dataframe(df)

            # Téléchargement du fichier résultant
            df.to_excel("résultat.xlsx", index=False)
            st.download_button(label="Télécharger le fichier avec les résultats", data=open("résultat.xlsx", "rb"), file_name="résultat.xlsx")

# Ajouter cette ligne pour que le script soit exécuté avec la fonction main()
if __name__ == "__main__":
    main()
