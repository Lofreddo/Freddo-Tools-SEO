import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import os

# Initialisation d'une session pour réutiliser les connexions
session = requests.Session()

def scrape_text_from_url(url):
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove unwanted sections
        for unwanted in soup(['header', 'nav', 'footer', 'script', 'style']):
            unwanted.decompose()
        
        scraped_data = []
        tags_to_extract = ['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'li']
        
        for tag in tags_to_extract:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text(strip=True)
                if text:  # Only add non-empty text
                    scraped_data.append({
                        'structure': f"<{tag}>",
                        'content': text
                    })
        
        return url, scraped_data
    except requests.exceptions.RequestException as e:
        return url, [{"structure": "Error", "content": f"Request failed: {str(e)}"}]

def scrape_all_urls(urls):
    scraped_results = []
    # Dynamically determine the number of workers based on available CPU cores
    max_workers = os.cpu_count() or 1  # Fallback to 1 if os.cpu_count() returns None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_text_from_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            try:
                url, data = future.result()
                scraped_results.append((url, data))
            except Exception as e:
                scraped_results.append((future_to_url[future], [{"structure": "Error", "content": str(e)}]))

    return scraped_results

def create_output_df(scraped_data_list):
    output_data = []
    for url, scraped_data in scraped_data_list:
        for data in scraped_data:
            output_data.append({
                'URL': url,
                'Structure': data['structure'],
                'Contenu Scrapé': data['content']
            })
    return pd.DataFrame(output_data)

def create_excel_file(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Scraped Data')
    return output.getvalue()

def main():
    st.title("Scraper de contenu HTML")

    option = st.selectbox(
        "Comment souhaitez-vous fournir les URLs ?",
        ("Zone de texte", "Fichier Excel")
    )

    urls = []

    if option == "Zone de texte":
        url_input = st.text_area("Entrez les URLs à scraper (une par ligne)")
        if url_input:
            urls = list(filter(None, url_input.splitlines()))  # Supprime les lignes vides

    elif option == "Fichier Excel":
        uploaded_file = st.file_uploader("Choisissez un fichier Excel", type=["xlsx", "xls"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            column_name = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)
            urls = df[column_name].dropna().tolist()

    if st.button("Scraper"):
        if urls:
            scraped_data_list = scrape_all_urls(urls)
            df = create_output_df(scraped_data_list)
            
            excel_data = create_excel_file(df)
            
            st.success("Scraping terminé avec succès ! Téléchargez le fichier ci-dessous.")
            st.download_button(
                label="Télécharger le fichier Excel",
                data=excel_data,
                file_name="scraped_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Aucune URL fournie.")

if __name__ == "__main__":
    main()
