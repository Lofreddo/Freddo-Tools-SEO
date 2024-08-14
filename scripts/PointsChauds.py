import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# Fonction pour scraper les éléments demandés
def scrape_html(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else ''
            h1 = soup.h1.string if soup.h1 else ''
            hn_structure = ''
            for hn in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
                hn_structure += f"{hn.name}: {hn.text.strip()} | "
            return title, h1, hn_structure.strip('| ')
        else:
            return '', '', ''
    except Exception as e:
        return '', '', ''

# Fonction principale à exécuter
def main():
    st.title("Analyse SEO des Pages Web")

    # Étape 1 : Upload du fichier Excel
    uploaded_file = st.file_uploader("Upload un fichier Excel", type=["xlsx"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)

        # Étape 2 : Sélection des colonnes pour "Mot clé" et "URL"
        col_keyword = st.selectbox("Sélectionnez la colonne 'Mot clé'", df.columns)
        col_url = st.selectbox("Sélectionnez la colonne 'URL'", df.columns)

        if st.button("Lancer l'analyse"):
            # Initialisation des nouvelles colonnes
            df['Contenu Balise Title'] = ''
            df['Contenu Balise H1'] = ''
            df['Contenu Structure Hn'] = ''
            df['Présence Title'] = ''
            df['Présence H1'] = ''
            df['Présence Structure Hn'] = ''

            # Parcours des URLs et scrape des informations
            for index, row in df.iterrows():
                keyword = str(row[col_keyword]).lower()
                url = row[col_url]
                title, h1, hn_structure = scrape_html(url)

                # Mise à jour des colonnes avec le contenu scrappé
                df.at[index, 'Contenu Balise Title'] = title
                df.at[index, 'Contenu Balise H1'] = h1
                df.at[index, 'Contenu Structure Hn'] = hn_structure

                # Vérification de la présence des mots clés
                df.at[index, 'Présence Title'] = 'Oui' if keyword in title.lower() else 'Non'
                df.at[index, 'Présence H1'] = 'Oui' if keyword in h1.lower() else 'Non'
                df.at[index, 'Présence Structure Hn'] = 'Oui' if keyword in hn_structure.lower() else 'Non'

            # Étape 7 : Bouton de téléchargement du fichier Excel avec les résultats
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Télécharger le fichier Excel avec les résultats",
                data=output.getvalue(),
                file_name="resultats_analyse.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
