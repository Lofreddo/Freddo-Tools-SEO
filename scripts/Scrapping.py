import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

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

    html_content = ""
    structure_hn = []
    
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
        structure_hn.append(tag.name)
        html_content += tag.get_text(strip=True) + '\n'

    structure_hn_str = " > ".join(structure_hn)

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
