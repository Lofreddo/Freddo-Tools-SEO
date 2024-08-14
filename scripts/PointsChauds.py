import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO
from nltk.stem import PorterStemmer

# Initialisation du stemmer
stemmer = PorterStemmer()

# Fonction pour obtenir la racine d'un mot
def get_stem(word):
    return stemmer.stem(word)

# Fonction pour vérifier la présence du mot-clé dans une balise spécifique
def check_keyword_in_text(text, keyword):
    # Tokenisation simple et stemming des mots du mot-clé
    keyword_parts = [get_stem(part) for part in keyword.split()]
    
    # Création du motif de recherche avec tolérance de 0 à 5 caractères entre les mots
    pattern = r'\b' + r'.{0,5}'.join(map(re.escape, keyword_parts)) + r'\b'
    
    # Stemming du texte avant la recherche
    stemmed_text = " ".join([get_stem(word) for word in text.split()])
    
    # Recherche du motif dans le texte
    return re.search(pattern, stemmed_text, re.IGNORECASE) is not None

# Fonction pour extraire et vérifier les balises
def extract_and_check(soup, keyword):
    # Récupérer le contenu de la balise title
    title = soup.title.string if soup.title else ""
    title_match = check_keyword_in_text(title, keyword)

    # Récupérer le contenu de la balise h1
    h1 = soup.h1.get_text() if soup.h1 else ""
    h1_match = check_keyword_in_text(h1, keyword)
    
    # Récupérer les contenus des balises h2, h3, h4
    hn_texts = []
    hn_match = False
    for tag in ['h2', 'h3', 'h4']:
        tags = soup.find_all(tag)
        for t in tags:
            hn_texts.append(t.get_text())
            if check_keyword_in_text(t.get_text(), keyword):
                hn_match = True
    
    hn_text = " | ".join(hn_texts)  # Pour avoir une structure lisible des Hn
    
    return title, title_match, h1, h1_match, hn_text, hn_match

# Fonction principale pour l'application Streamlit
def main():
    st.title("Vérification de mot-clé dans des pages web")

    # Chargement du fichier xlsx
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("Aperçu du fichier :")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")
            return

        # Sélection des colonnes
        keyword_column = st.selectbox("Sélectionnez la colonne contenant les mots-clés", df.columns)
        url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)

        if st.button("Lancer le crawl"):
            # Initialisation des nouvelles colonnes
            st.write("Initialisation des colonnes...")
            df['Balise Title'] = ''
            df['Title Match'] = ''
            df['H1'] = ''
            df['H1 Match'] = ''
            df['Hn Structure'] = ''
            df['Hn Match'] = ''
            st.write("Colonnes initialisées avec succès.")

            for index, row in df.iterrows():
                keyword = row[keyword_column]
                url = row[url_column]

                try:
                    st.write(f"Scraping URL: {url}")
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extraire et vérifier les balises
                    title, title_match, h1, h1_match, hn_text, hn_match = extract_and_check(soup, keyword)
                    
                    # Ajouter les résultats dans le dataframe
                    df.at[index, 'Balise Title'] = title
                    df.at[index, 'Title Match'] = "Oui" if title_match else "Non"
                    df.at[index, 'H1'] = h1
                    df.at[index, 'H1 Match'] = "Oui" if h1_match else "Non"
                    df.at[index, 'Hn Structure'] = hn_text
                    df.at[index, 'Hn Match'] = "Oui" if hn_match else "Non"

                except requests.exceptions.RequestException as e:
                    st.error(f"Erreur pour l'URL {url}: {e}")
                    df.at[index, 'Balise Title'] = 'Erreur'
                    df.at[index, 'Title Match'] = 'Erreur'
                    df.at[index, 'H1'] = 'Erreur'
                    df.at[index, 'H1 Match'] = 'Erreur'
                    df.at[index, 'Hn Structure'] = 'Erreur'
                    df.at[index, 'Hn Match'] = 'Erreur'

            # Affichage du résultat
            st.write("Résultat du crawl :")
            st.dataframe(df)

            # Sauvegarde du fichier Excel
            try:
                output_file = BytesIO()
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button(
                    label="Télécharger le fichier avec les résultats",
                    data=output_file.getvalue(),
                    file_name="résultat_scraping.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Erreur lors de la création du fichier Excel : {e}")

# Ajouter cette ligne pour que le script soit exécuté avec la fonction main()
if __name__ == "__main__":
    main()
