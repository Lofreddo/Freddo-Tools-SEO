import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# Fonction pour vérifier la présence du mot-clé dans une balise spécifique
def check_keyword_in_tag(soup, tag, keyword):
    tags = soup.find_all(tag)
    for t in tags:
        if keyword_in_text(t.get_text(), keyword):
            return "Oui"
    return "Non"

# Fonction pour vérifier le mot-clé avec tolérance pour les variations
def keyword_in_text(text, keyword):
    # Échappement des caractères spéciaux pour éviter les problèmes de regex
    keyword = re.escape(keyword)
    # Création du motif de recherche avec tolérance
    pattern = r'\b' + r'\s*'.join(list(keyword)) + r'\b'
    return re.search(pattern, text, re.IGNORECASE) is not None

# Streamlit UI
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
