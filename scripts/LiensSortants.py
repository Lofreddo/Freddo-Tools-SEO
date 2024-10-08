import streamlit as st
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import io
from urllib.parse import urljoin
import requests
import random

# Liste d'User-Agents pour la rotation
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

async def analyze_url(session, url, semaphore):
    async with semaphore:
        try:
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            results = []
            anchor_counts = {}
            
            # Compter d'abord toutes les occurrences d'ancres
            for link in links:
                anchor_text = link.text.strip()
                anchor_counts[anchor_text] = anchor_counts.get(anchor_text, 0) + 1
            
            for link in links:
                href = link['href']
                full_url = urljoin(url, href)
                
                zone = get_link_zone(link)
                anchor_text = link.text.strip()
                
                results.append({
                    'URL': url,
                    'Link': full_url,
                    'Zone': zone,
                    'Occurrences': len(soup.find_all('a', href=href)),
                    'Anchor': anchor_text,
                    'Anchor_Occurrences': anchor_counts[anchor_text]
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
        semaphore = asyncio.Semaphore(10)
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
            url_link_counts = {}
            for result, num_links in results:
                all_results.extend(result)
                if result:
                    url_link_counts[result[0]['URL']] = num_links
            
            df_results = pd.DataFrame(all_results)
            df_link_counts = pd.DataFrame(list(url_link_counts.items()), columns=['URL', 'Number of Links'])
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, sheet_name='Link Analysis', index=False)
                df_link_counts.to_excel(writer, sheet_name='Links per URL', index=False)
            
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
