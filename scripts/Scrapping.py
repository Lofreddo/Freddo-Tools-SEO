import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import re

# Fonction pour nettoyer le contenu HTML en fonction des exigences
def clean_html_content(soup):
    # Supprimer les balises <span>, <div>, <label>, <img>, <table>, <tr>, <td>, <path>, <svg>, <em>, <th>
    # en conservant leur contenu
    for tag in soup.find_all(['span', 'div', 'label', 'img', 'table', 'tr', 'td', 'path', 'svg', 'em', 'th']):
        tag.unwrap()

    # Supprimer les balises <a> en conservant le contenu, sauf si elles contiennent des liens vers les réseaux sociaux
    social_keywords = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'social']
    for a_tag in soup.find_all('a', href=True):
        if any(keyword in a_tag['href'].lower() for keyword in social_keywords):
            a_tag.decompose()  # Supprime la balise entière si elle contient un lien vers les réseaux sociaux
        else:
            a_tag.unwrap()  # Supprime la balise <a> mais conserve son contenu

    # Supprimer les classes CSS et autres attributs des balises restantes
    for tag in soup.find_all(True):
        tag.attrs = {}

    return soup

# Fonction pour supprimer les balises vides et nettoyer les espaces inutiles
def remove_empty_tags_and_clean_spaces(soup):
    # Supprimer les balises vides
    for tag in soup.find_all():
        if not tag.get_text(strip=True):  # Si la balise ne contient pas de texte
            tag.decompose()

    # Convertir le HTML en texte brut et nettoyer les espaces
    clean_html = str(soup)
    clean_html = re.sub(r'\s+', ' ', clean_html)  # Remplacer les espaces multiples par un seul espace
    clean_html = clean_html.strip()  # Supprimer les espaces en début et fin de texte

    return clean_html

# Fonction pour extraire le contenu et la structure des balises hn
def get_hn_and_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Supprimer les balises header et footer
    for tag in soup.find_all(['header', 'footer']):
        tag.decompose()

    # Nettoyer le contenu HTML selon les critères définis
    clean_soup = clean_html_content(soup)

    # Supprimer les balises vides et nettoyer les espaces inutiles
    html_content = remove_empty_tags_and_clean_spaces(clean_soup)

    structure_hn = []
    for tag in clean_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
        structure_hn.append(f"<{tag.name}>{tag.get_text(strip=True)}</{tag.name}>")

    structure_hn_str = "\n".join(structure_hn)

    return html_content.strip(), structure_hn_str

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

    urls = [url.strip() for url in urls_input.splitlines() if url.strip()]

    if st.button("Lancer le scraping"):
        if urls:
            df = generate_output(urls)

            st.subheader("Aperçu des résultats")
            st.write(df)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Télécharger le fichier Excel",
                data=buffer.getvalue(),
                file_name="output.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.warning("Veuillez entrer au moins une URL.")

# Exécution directe du script
if __name__ == "__main__":
    main()
