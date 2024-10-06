import streamlit as st
import pandas as pd
import aiohttp
import asyncio
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from io import BytesIO
import gc
import trafilatura
import re
import warnings

# Ignorer l'avertissement XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

async def scrape_text_from_url(url, session):
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            html = await response.text()
            
            # Extraction du contenu principal avec Trafilatura
            main_content = trafilatura.extract(
                html,
                output_format='html',
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                favor_precision=False,
                favor_recall=True,
                no_fallback=False,
                include_formatting=True
            )
            
            if main_content is None:
                return url, "<p>Aucun contenu extrait</p>", []
            
            # Extraction des en-têtes
            soup = BeautifulSoup(html, 'lxml-xml')
            headers = soup.find_all(re.compile('^h[1-6]$'))
            header_structure = [f"<{header.name}>{header.get_text(strip=True)}</{header.name}>" for header in headers]
            
            # Nettoyage et ajout du <h1>
            main_content = re.sub(r'</?html>|</?body>', '', main_content)
            h1_tags = [h for h in header_structure if h.startswith('<h1>')]
            if h1_tags and not re.search(r'<h1>', main_content):
                main_content = h1_tags[0] + main_content
            
            return url, main_content, header_structure
    except Exception as e:
        return url, f"<p>Error: {str(e)}</p>", []

async def scrape_all_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_text_from_url(url, session) for url in urls]
        return await asyncio.gather(*tasks)

def create_output_df(scraped_data_list):
    output_data = []
    for url, scraped_data, header_structure in scraped_data_list:
        output_data.append({
            'URL': url,
            'Contenu Scrapé': scraped_data,
            'Structure Hn': ' '.join(header_structure)
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
            batch_size = 1000  # Réduit pour une meilleure gestion de la mémoire
            total_batches = len(urls) // batch_size + 1
            all_scraped_data = []

            progress_bar = st.progress(0)
            for batch_num in range(total_batches):
                batch_urls = urls[batch_num * batch_size: (batch_num + 1) * batch_size]
                scraped_data_list = asyncio.run(scrape_all_urls(batch_urls))
                all_scraped_data.extend(scraped_data_list)

                progress = (batch_num + 1) / total_batches
                progress_bar.progress(progress)

                gc.collect()

            df = create_output_df(all_scraped_data)
            
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
