import streamlit as st
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import io
from urllib.parse import urljoin
import requests

async def analyze_url(session, url, semaphore):
    async with semaphore:
        try:
            # Utiliser requests pour obtenir le HTML brut
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Lève une exception pour les codes d'état HTTP non-200
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            results = []
            for link in links:
                href = link['href']
                # Convertir les URLs relatives en URLs absolues
                full_url = urljoin(url, href)
                
                zone = get_link_zone(link)
                anchor_text = link.text.strip()
                results.append({
                    'URL': url,
                    'Link': full_url,
                    'Zone': zone,
                    'Occurrences': len(soup.find_all('a', href=href)),
                    'Anchor': anchor_text,
                    'Anchor_Occurrences': len(soup.find_all('a', text=anchor_text))
                })
            
            return results, len(links)
        except Exception as e:
            st.error(f"Error analyzing {url}: {str(e)}")
            return [], 0

def get_link_zone(link):
    for parent in link.parents:
        if parent.name in ['body', 'head', 'header', 'nav', 'footer', 'aside']:
            return parent.name
    return 'body'

async def process_urls(urls):
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(10)  # Limite le nombre de requêtes simultanées
        tasks = [analyze_url(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
    return results

def main():
    st.title("URL Link Analyzer")

    input_method = st.radio("Choose input method:", ("Text Input", "File Upload"))

    urls = []
    if input_method == "Text Input":
        url_input = st.text_area("Enter URLs (one per line):")
        urls = [url.strip() for url in url_input.split('\n') if url.strip()]
    else:
        uploaded_file = st.file_uploader("Choose a file", type=['xlsx', 'csv'])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            column = st.selectbox("Select URL column", df.columns)
            urls = df[column].tolist()

    if st.button("Analyze"):
        if urls:
            results = asyncio.run(process_urls(urls))
            
            all_results = []
            total_links = 0
            for result, num_links in results:
                all_results.extend(result)
                total_links += num_links
            
            df_results = pd.DataFrame(all_results)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, sheet_name='Link Analysis', index=False)
                pd.DataFrame({'Total Links': [total_links]}).to_excel(writer, sheet_name='Summary', index=False)
            
            st.download_button(
                label="Download Excel file",
                data=buffer,
                file_name="link_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Please enter URLs or upload a file.")

if __name__ == "__main__":
    main()
