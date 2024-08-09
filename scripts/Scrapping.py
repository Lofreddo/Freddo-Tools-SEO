import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# Fonction pour extraire le contenu des balises hn et HTML
def get_hn_and_content(url):
    with requests.Session() as session:
        try:
            response = session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            return None, None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Supprimer les sections de navigation et footers
    for nav_tag in soup.find_all(['nav', 'footer']):
        nav_tag.decompose()  # Retirer ces sections du soup

    # Gérer le cas où <body> est absent
    if not soup.body:
        content_container = soup
    else:
        content_container = soup.body

    hn_structure = ""
    for tag in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        if tag.get_text().strip():
            hn_structure += f"<{tag.name}>{tag.get_text()}</{tag.name}>\n"

    html_content = ""
    for tag in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'li', 'ol']):
        for child in tag.find_all(True):
            if child.name in ['b', 'i', 'em', 'strong']:
                child.replace_with(child.get_text())
        tag.attrs = {}
        if tag.get_text().strip():
            html_content += str(tag) + '\n'

    return hn_structure, html_content

# Fonction pour traiter les URLs en parallèle
def process_urls_in_parallel(urls, max_workers=10):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(get_hn_and_content, urls))
    return results

# Fonction pour générer la sortie en DataFrame
def generate_output(urls):
    results = process_urls_in_parallel(urls)

    hn_structures, html_contents = zip(*results)

    df = pd.DataFrame({
        'url': urls,
        'url_hn': hn_structures,
        'url_content': html_contents
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
