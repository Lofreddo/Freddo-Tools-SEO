import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# Fonction pour extraire les balises et vérifier la présence des mots-clés
def extract_and_display(soup):
    # Récupérer le contenu de la balise title
    title = soup.title.string if soup.title else ""
    st.write(f"Title: {title}")

    # Récupérer le contenu de la balise h1
    h1 = soup.h1.get_text() if soup.h1 else ""
    st.write(f"H1: {h1}")
    
    # Récupérer les contenus des balises h2, h3, h4
    hn_texts = []
    for tag in ['h2', 'h3', 'h4']:
        tags = soup.find_all(tag)
        for t in tags:
            hn_texts.append(t.get_text())
    
    hn_text = " | ".join(hn_texts)  # Pour avoir une structure lisible des Hn
    st.write(f"Hn: {hn_text}")
    
    return title, h1, hn_text

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
            df['Hn Structure'] = ''

            for index, row in df.iterrows():
                url = row[url_column].strip()

                try:
                    st.write(f"Scraping URL: {url}")

                    # Récupérer la page web
                    response = requests.get(url, timeout=10)
                    
                    # Vérifier si la requête est réussie
                    if response.status_code != 200:
                        st.error(f"Erreur pour l'URL {url}: Statut {response.status_code}")
                        df.at[index, 'Balise Title'] = f"Erreur: {response.status_code}"
                        df.at[index, 'H1'] = 'Erreur'
                        df.at[index, 'Hn Structure'] = 'Erreur'
                        continue

                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extraire et afficher les balises
                    title, h1, hn_text = extract_and_display(soup)
                    
                    # Ajouter les résultats dans le dataframe
                    df.at[index, 'Balise Title'] = title
                    df.at[index, 'H1'] = h1
                    df.at[index, 'Hn Structure'] = hn_text

                except requests.exceptions.RequestException as e:
                    st.error(f"Erreur pour l'URL {url}: {e}")
                    df.at[index, 'Balise Title'] = 'Erreur'
                    df.at[index, 'H1'] = 'Erreur'
                    df.at[index, 'Hn Structure'] = 'Erreur'

            # Affichage du résultat
            st.write("Résultat du crawl :")
            st.dataframe(df)

            # Téléchargement du fichier résultant
            df.to_excel("résultat.xlsx", index=False)
            st.download_button(label="Télécharger le fichier avec les résultats", data=open("résultat.xlsx", "rb"), file_name="résultat.xlsx")

# Ajouter cette ligne pour que le script soit exécuté avec la fonction main()
if __name__ == "__main__":
    main()
