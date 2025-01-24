import streamlit as st
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import io
from urllib.parse import urljoin
import requests
import random
import time
import base64  # <-- Peut être supprimé si vous n'en avez plus besoin
import streamlit.components.v1 as components  # <-- Peut être supprimé si vous n'en avez plus besoin

# Liste d'User-Agents pour la rotation
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

def retry_request(url, headers, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
            return response
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                st.error(f"All attempts failed for {url}: {str(e)}")
                raise

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
            response = retry_request(url, headers)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            results = []
            anchor_counts = {}
            
            for link in links:
                anchor_text = link.text.strip()
                anchor_counts[anchor_text] = anchor_counts.get(anchor_text, 0) + 1
            
            for link in links:
                href = link['href']
                full_url = urljoin(url, href)
                
                zone = get_link_zone(link)
                anchor_text = link.text.strip()
                
                nofollow = 'rel' in link.attrs and 'nofollow' in link['rel']
                
                try:
                    link_response = retry_request(full_url, headers)
                    link_status = link_response.status_code
                except:
                    link_status = 'Error'
                
                results.append({
                    'URL': url,
                    'Link': full_url,
                    'Zone': zone,
                    'Occurrences': len(soup.find_all('a', href=href)),
                    'Anchor': anchor_text,
                    'Anchor_Occurrences': anchor_counts[anchor_text],
                    'Nofollow': nofollow,
                    'Link_Status': link_status
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

def analyze_anchors(all_results):
    anchor_dict = {}
    for result in all_results:
        anchor = result['Anchor']
        url = result['Link']
        if anchor not in anchor_dict:
            anchor_dict[anchor] = {'count': 0, 'urls': set()}
        if url not in anchor_dict[anchor]['urls']:
            anchor_dict[anchor]['urls'].add(url)
            anchor_dict[anchor]['count'] += 1
    
    anchor_results = [(anchor, data['count'], ', '.join(data['urls'])) for anchor, data in anchor_dict.items()]
    return pd.DataFrame(anchor_results, columns=['Anchor', 'Number of Pages', 'URLs'])

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
                    url = result[0]['URL']
                    url_link_counts[url] = {
                        'Total_Links': num_links,
                        'Links_301': sum(1 for r in result if r['Link_Status'] == 301),
                        'Links_404': sum(1 for r in result if r['Link_Status'] == 404)
                    }
            
            df_results = pd.DataFrame(all_results)
            df_link_counts = pd.DataFrame([
                {
                    'URL': url,
                    'Number of Links': data['Total_Links'],
                    'Links to 301': data['Links_301'],
                    'Links to 404': data['Links_404']
                }
                for url, data in url_link_counts.items()
            ])
            df_anchor_analysis = analyze_anchors(all_results)
            
            # Génération du fichier Excel en mémoire
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, sheet_name='Link Analysis', index=False)
                df_link_counts.to_excel(writer, sheet_name='Links per URL', index=False)
                df_anchor_analysis.to_excel(writer, sheet_name='Anchors Analysis', index=False)

            # Remettre le pointeur au début du buffer
            buffer.seek(0)
            
            download_filename = "link_analysis.xlsx"

            # Utilisation de st.download_button pour permettre le téléchargement via un bouton
            st.download_button(
                label="Télécharger le fichier Excel",
                data=buffer,
                file_name=download_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.success("Analyse terminée. Vous pouvez télécharger le fichier Excel ci-dessus.")
        else:
            st.warning("Veuillez entrer des URLs ou télécharger un fichier.")

if __name__ == "__main__":
    main()
