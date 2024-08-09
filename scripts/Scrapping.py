import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# Fonction pour filtrer et nettoyer le contenu HTML
def clean_html_content(soup):
    # Supprimer les balises <span>, <div>, <label>
    for tag in soup.find_all(['span', 'div', 'label']):
        tag.decompose()
    
    # Supprimer les balises <a> en conservant le contenu, sauf si elles contiennent des liens vers les réseaux sociaux
    social_keywords = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'social']
    for a_tag in soup.find_all('a', href=True):
        if any(keyword in a_tag['href'].lower() for keyword in social_keywords):
            a_tag.decompose()  # Supprime la balise entière si elle contient un lien vers les réseaux sociaux
        else:
            a_tag.unwrap()  # Supprime la balise <a> mais conserve son contenu

    # Supprimer les attributs (classes CSS, id, etc.) des balises restantes
    for tag in soup.find_all(True):
        tag.attrs = {}

    return soup

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

    # Nettoyer le contenu HTML en fonction des exigences
    clean_soup = clean_html_content(soup)

    html_content = ""
    structure_hn = []
    
    for tag in clean_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
        # Conserver la balise HTML dans le contenu nettoyé
        if tag.get_text(strip=True):  # Vérifie si le texte n'est pas vide
            html_content += str(tag) + '\n'
        # Ajouter la balise dans la structure hn, avec son contenu
        if tag.name.startswith('h'):
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
        'content': [content if content is not None else "" for content, _ in contents],
        'structure_hn': [structure if structure is not None else "" for _, structure in contents]
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
