import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import gc
import trafilatura
import re

session = requests.Session()

def scrape_text_from_url(url):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        # Extraction du contenu principal avec Trafilatura
        downloaded = trafilatura.fetch_url(url)
        main_content = trafilatura.extract(downloaded, output_format='html', include_comments=False, include_tables=False)
        
        if main_content is None:
            return url, "<p>Aucun contenu extrait</p>"
        
        # Extraction des balises h1 du header
        soup = BeautifulSoup(response.text, 'lxml')
        header = soup.find('header')
        h1_tags = []
        if header:
            h1_tags = [h1.get_text(strip=True) for h1 in header.find_all('h1')]
        
        # Ajout des balises h1 du header au début du contenu
        for h1 in h1_tags:
            main_content = f"<h1>{h1}</h1>\n" + main_content
        
        gc.collect()
        return url, main_content
    except Exception as e:
        return url, f"<p>Error: {str(e)}</p>"

def scrape_all_urls(urls):
    scraped_results = []
    max_workers = min(100, len(urls) // 100 + 1)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_text_from_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            try:
                url, data = future.result()
                scraped_results.append((url, data))
            except Exception as e:
                scraped_results.append((future_to_url[future], f"<p>Error: {str(e)}</p>"))

            if len(scraped_results) % 1000 == 0:
                gc.collect()

    return scraped_results

def create_output_df(urls, scraped_data_list):
    output_data = []
    for url, scraped_data in scraped_data_list:
        output_data.append({
            'URL': url,
            'Contenu Scrapé': scraped_data
        })
    return pd.DataFrame(output_data)

def create_excel_file(df):
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Scraped Data')
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        st.error(f"Erreur lors de la création du fichier Excel : {str(e)}")
        return None

def main():
    st.title("Scraper de contenu HTML avec Trafilatura")

    option = st.selectbox(
        "Comment souhaitez-vous fournir les URLs ?",
        ("Zone de texte", "Fichier Excel")
    )

    urls = []

    if option == "Zone de texte":
        url_input = st.text_area("Entrez les URLs à scraper (une par ligne)")
        if url_input:
            urls = list(filter(None, url_input.splitlines()))

    elif option == "Fichier Excel":
        uploaded_file = st.file_uploader("Choisissez un fichier Excel", type=["xlsx", "xls"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            column_name = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)
            urls = df[column_name].dropna().tolist()

    if st.button("Scraper"):
        if urls:
            batch_size = 10000
            total_batches = len(urls) // batch_size + 1
            all_scraped_data = []

            for batch_num in range(total_batches):
                batch_urls = urls[batch_num * batch_size: (batch_num + 1) * batch_size]
                scraped_data_list = scrape_all_urls(batch_urls)
                all_scraped_data.extend(scraped_data_list)

                gc.collect()

            df = create_output_df(urls, all_scraped_data)
            
            excel_data = create_excel_file(df)
            
            if excel_data:
                st.success("Scraping terminé avec succès ! Téléchargez le fichier ci-dessous.")
                st.download_button(
                    label="Télécharger le fichier Excel",
                    data=excel_data,
                    file_name="scraped_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Impossible de créer le fichier Excel. Veuillez vérifier les logs pour plus de détails.")
        else:
            st.error("Aucune URL fournie.")

if __name__ == "__main__":
    main()
