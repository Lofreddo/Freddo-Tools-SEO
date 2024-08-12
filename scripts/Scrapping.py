import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import re

# Fonction pour nettoyer le contenu HTML en fonction des exigences
def clean_html_content(soup):
    for tag in soup.find_all(['span', 'div', 'label', 'img', 'path', 'svg', 'em', 'th', 'strong']):
        tag.unwrap()
    for tag in soup.find_all(['tr', 'td', 'table', 'button']):
        tag.decompose()
    social_keywords = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'social']
    for a_tag in soup.find_all('a', href=True):
        if any(keyword in a_tag['href'].lower() for keyword in social_keywords):
            a_tag.decompose()
        else:
            a_tag.unwrap()
    for tag in soup.find_all(True):
        tag.attrs = {}
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()
    return soup

# Fonction pour extraire le contenu et la structure des balises hn
def get_hn_and_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        return None, None
    soup = BeautifulSoup(response.content, 'html.parser')
    for tag in soup.find_all(['header', 'footer']):
        tag.decompose()
    clean_soup = clean_html_content(soup)
    html_content = ""
    structure_hn = []
    for tag in clean_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
        if tag.get_text(strip=True):
            html_content += str(tag) + '\n'
        if tag.name.startswith('h'):
            structure_hn.append(f"<{tag.name}>{tag.get_text(strip=True)}</{tag.name}>")
    structure_hn_str = "\n".join(structure_hn)
    html_content = re.sub(r'\t+', ' ', html_content)
    html_content = re.sub(' +', ' ', html_content)
    html_content = "\n".join([line for line in html_content.splitlines() if line.strip()])
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

    option = st.radio("Choisissez votre mode d'entrée :", ('Entrée manuelle des URLs', 'Importer un fichier Excel'))

    urls = []

    if option == 'Entrée manuelle des URLs':
        st.subheader("Entrez les URLs à scraper (une URL par ligne):")
        urls_input = st.text_area("Entrez vos URLs ici", height=200)
        urls = [url.strip() for url in urls_input.splitlines() if url.strip()]

    elif option == 'Importer un fichier Excel':
        st.subheader("Téléchargez votre fichier Excel contenant les URLs")
        uploaded_file = st.file_uploader("Choisissez un fichier Excel", type=["xlsx"])
        
        if uploaded_file is not None:
            df_input = pd.read_excel(uploaded_file)
            st.write("Aperçu du fichier téléchargé :", df_input.head())
            url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df_input.columns)
            urls = df_input[url_column].dropna().tolist()

    if st.button("Lancer le scraping"):
        if urls:
            df_output = generate_output(urls)
            
            st.subheader("Aperçu des résultats")
            st.write(df_output)

            buffer = BytesIO()

            if option == 'Entrée manuelle des URLs':
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_output.to_excel(writer, index=False)
                st.download_button(
                    label="Télécharger le fichier Excel",
                    data=buffer.getvalue(),
                    file_name="output.xlsx",
                    mime="application/vnd.ms-excel"
                )
            elif option == 'Importer un fichier Excel' and uploaded_file is not None:
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_input_with_output = pd.concat([df_input, df_output[['content', 'structure_hn']]], axis=1)
                    df_input_with_output.to_excel(writer, index=False)
                st.download_button(
                    label="Télécharger le fichier Excel avec les résultats",
                    data=buffer.getvalue(),
                    file_name="output_with_results.xlsx",
                    mime="application/vnd.ms-excel"
                )
        else:
            st.warning("Veuillez entrer ou sélectionner au moins une URL.")

# Exécution directe du script
if __name__ == "__main__":
    main()
