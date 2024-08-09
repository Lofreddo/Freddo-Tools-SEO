import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# Fonction pour filtrer les éléments non pertinents
def filter_tags(soup):
    # Supprimer les balises de navigation, footers, et listes de liens
    for tag in soup.find_all(['nav', 'footer', 'path', 'svg']):
        tag.decompose()  # Retirer ces sections du soup

    # Supprimer les sections avec des liens vers les réseaux sociaux
    social_keywords = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'social']
    for link in soup.find_all('a', href=True):
        if any(keyword in link['href'].lower() for keyword in social_keywords):
            link.decompose()

    # Supprimer les listes de liens qui sont souvent en bas de page
    for ul in soup.find_all('ul'):
        if ul.find_all('a', href=True):
            ul.decompose()

    # Supprimer les balises <span>, <img>, <table>, <td>, <tr> mais conserver le contenu pertinent
    for tag in soup.find_all(['span', 'img', 'table', 'td', 'tr']):
        # Remplacer la balise par son contenu si celui-ci contient des balises intéressantes
        if any(child.name in ['p', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5'] for child in tag.find_all(True)):
            tag.unwrap()  # Déplie la balise et garde son contenu
        else:
            tag.decompose()  # Supprime la balise et son contenu

# Fonction pour extraire le contenu des balises hn et HTML
def get_hn_and_content(url):
    with requests.Session() as session:
        try:
            response = session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            return None, None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Filtrer les éléments non pertinents
    filter_tags(soup)

    # Gérer le cas où <body> est absent
    content_container = soup.body if soup.body else soup

    # Extraire uniquement les balises pertinentes
    html_content = ""
    for tag in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
        # Supprimer les attributs pour éviter de conserver les classes CSS
        tag.attrs = {}
        if tag.get_text().strip():
            html_content += str(tag) + '\n'

    return html_content

# Fonction pour traiter les URLs en parallèle
def process_urls_in_parallel(urls, max_workers=10):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(get_hn_and_content, urls))
    return results

# Fonction pour générer la sortie en DataFrame
def generate_output(urls):
    contents = process_urls_in_parallel(urls)

    df = pd.DataFrame({
        'url': urls,
        'content': contents
    })

    return df

# Fonction principale pour l'interface Streamlit
def main():
    st.title("Scraping Tool")

    # Zone de texte pour entrer les URLs
    st.subheader("Entrez les URLs à scraper (une URL par ligne):")
    urls_input = st.text_area("Entrez vos URLs ici", height=200)

    # Convertir les URLs en une liste
    urls = urls_input.splitlines()

    # Ajouter un bouton pour lancer le scraping
    if st.button("Lancer le scraping"):
        if urls:
            df = generate_output(urls)

            # Afficher les résultats dans Streamlit
            st.subheader("Aperçu des résultats")
            st.write(df.head())

            # Ajouter un bouton pour télécharger le fichier Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Télécharger le fichier Excel",
                data=buffer,
                file_name="output.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.warning("Veuillez entrer au moins une URL.")

# Exécution directe du script
if __name__ == "__main__":
    main()
