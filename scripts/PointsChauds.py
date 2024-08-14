import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO
from nltk.stem import PorterStemmer

# Initialisation du stemmer
stemmer = PorterStemmer()

# Liste des articles et pronoms à exclure
exclusion_list = [
    'le', 'la', 'les', 'l\'', 'un', 'une', 'des', 'du', 'de', 'de la', 'de l\'', 
    'mon', 'ton', 'son', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs'
]

# Fonction pour supprimer les articles et pronoms exclus
def remove_exclusions(text):
    words = text.lower().split()
    filtered_words = [word for word in words if word not in exclusion_list]
    return ' '.join(filtered_words)

# Fonction pour obtenir la racine d'un mot
def get_stem(word):
    return stemmer.stem(word.lower())

# Fonction pour vérifier la présence du mot-clé dans une balise spécifique avec des règles avancées
def check_keyword_in_text(text, keyword):
    # Supprimer les articles et pronoms exclus
    text = remove_exclusions(text)
    keyword = remove_exclusions(keyword)

    # Tokenisation simple et stemming des mots du mot-clé
    keyword_parts = [get_stem(part) for part in keyword.split()]
    
    # Création du motif de recherche avec tolérance de 0 à 5 caractères entre les mots
    pattern_1 = r'\b' + r'.{0,5}'.join(map(re.escape, keyword_parts)) + r'\b'
    
    # Stemming du texte avant la recherche
    text_words = [get_stem(word) for word in text.split()]
    stemmed_text = " ".join(text_words)
    
    # Recherche des motifs dans le texte
    match_1 = re.search(pattern_1, stemmed_text, re.IGNORECASE)
    
    return match_1 is not None

# Fonction pour extraire et vérifier les balises
def extract_and_check(soup, keyword):
    # Récupérer le contenu de la balise title
    title = soup.title.string if soup.title else ""
    title_match = check_keyword_in_text(title, keyword)

    # Récupérer le contenu de la balise h1
    h1 = soup.h1.get_text() if soup.h1 else ""
    h1_match = check_keyword_in_text(h1, keyword)
    
    # Récupérer les contenus des balises h2, h3 dans l'ordre d'apparition
    hn_texts = []
    hn_match = False
    tags = soup.find_all(['h2', 'h3'])  # Chercher h2 et h3 dans l'ordre d'apparition
    for t in tags:
        hn_text = f"<{t.name}>{t.get_text()}</{t.name}>"
        hn_texts.append(hn_text)
        if check_keyword_in_text(t.get_text(), keyword):
            hn_match = True
    
    hn_text = "\n".join(hn_texts)  # Pour avoir une structure lisible des Hn
    
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
