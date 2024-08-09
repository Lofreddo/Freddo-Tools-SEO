import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# Fonction pour filtrer les éléments non pertinents
def filter_tags(soup):
    # Supprimer les balises de header et footer basées sur des tags, classes ou ID communs
    for tag in soup.find_all(['header', 'footer']):
        tag.decompose()

    # Supprimer les balises non pertinentes tout en conservant le contenu des balises pertinentes
    for tag in soup.find_all(True):  # True trouve toutes les balises
        if tag.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']:
            tag.decompose()

# Fonction pour extraire le contenu et la structure des balises hn
def get_hn_and_content(url):
    try:
        with requests.Session() as session:
            response = session.get(url)
            response.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Erreur lors de la récupération de l'URL {url}: {e}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Filtrer les éléments non pertinents
    filter_tags(soup)

    # Gérer le cas où <body> est absent
    content_container = soup.body if soup.body else soup

    # Extraire le contenu et la structure des balises hn
    html_content = ""
    structure_hn = []
    
    for tag in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
        tag.attrs = {}  # Supprimer les attributs CSS et autres
        if tag.get_text().strip():
            html_content += str(tag) + '\n'
            if tag.name.startswith('h'):
                structure_hn.append(tag.name)

    if not html_content:  # Vérifie si du contenu a été récupéré
        st.warning(f"Aucun contenu pertinent trouvé pour l'URL {url}")

    # Combiner la structure hn en une chaîne de caractères
    structure_hn_str = " > ".join(structure_hn)

    return html_content, structure_hn_str

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
        'content': [content for content, _ in contents],
        'structure_hn': [structure for _, structure in contents]
    })

    return df

# Fonction principale pour l'interface Streamlit
def main():
    st.title("Scraping Tool")

    st.subheader("Entrez les URLs à scraper (une URL par ligne):")
    urls_input = st.text_area("Entrez vos URLs ici", height=200)

    urls = urls_input.splitlines()

    if st.button("Lancer le scraping"):
        if urls:
            df = generate_output(urls)

            st.subheader("Aperçu des résultats")
            st.write(df.head())

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
