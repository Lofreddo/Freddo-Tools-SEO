import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import io
from concurrent.futures import ThreadPoolExecutor
import gc

# Fonction pour crawler un site web avec ThreadPoolExecutor pour plus de vitesse
def crawl_website(domain, max_urls=1000, workers=10):
    crawled_urls = set()
    to_crawl = {domain}
    url_results = []

    def process_url(url):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                crawled_urls.add(url)
                links = [urljoin(domain, link['href']) for link in soup.find_all('a', href=True)]
                return soup, links
        except requests.exceptions.RequestException:
            pass
        return None, []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while to_crawl and len(crawled_urls) < max_urls:
            url = to_crawl.pop()
            soup, links = process_url(url)
            if soup:
                url_results.append((url, soup))
                to_crawl.update(link for link in links if urlparse(link).netloc == urlparse(domain).netloc and link not in crawled_urls)
            st.write(f"{len(crawled_urls)} URLs crawled jusqu'à présent...")

    return url_results

# Analyse des URLs récupérées, évitant de refaire plusieurs requêtes
def analyze_url_data(url, soup):
    result = {}

    # Vérification HTTP -> HTTPS
    http_url = url.replace("https://", "http://", 1)
    try:
        http_response = requests.head(http_url, allow_redirects=False, timeout=5)
        result["http_https"] = "Oui" if http_response.status_code in [301, 302] and "https://" in http_response.headers.get('Location', '') else "Non"
    except requests.exceptions.RequestException:
        result["http_https"] = "Non"

    # Vérification des redirections avec ou sans slash
    if url.endswith("/"):
        url_without_slash = url.rstrip("/")
        try:
            response = requests.head(url_without_slash, allow_redirects=False, timeout=5)
            result["trailing_slash"] = "Oui" if response.status_code in [301, 302] and response.headers.get('Location', '').endswith("/") else "Non"
        except requests.exceptions.RequestException:
            result["trailing_slash"] = "Non"
    else:
        url_with_slash = url + "/"
        try:
            response = requests.head(url_with_slash, allow_redirects=False, timeout=5)
            result["trailing_slash"] = "Oui" if response.status_code in [301, 302] and response.headers.get('Location', '') == url else "Non"
        except requests.exceptions.RequestException:
            result["trailing_slash"] = "Non"

    # Analyse des images
    images = soup.find_all('img')
    large_images = sum(1 for img in images if int(img.get('data-file-size', 0)) > 100 * 1024)
    empty_alt = sum(1 for img in images if not img.get('alt', '').strip())
    result['large_images'] = large_images
    result['empty_alt'] = empty_alt

    return result

# Fonction principale d'analyse optimisée
def main():
    st.title("Site Analyzer - Optimisé pour la vitesse et les ressources")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")
            
            # Crawler toutes les URLs du site avec ThreadPoolExecutor
            url_data = crawl_website(domain)

            # Analyser les résultats une fois récupérés
            st.write("Analyse des URLs...")
            results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {url: executor.submit(analyze_url_data, url, soup) for url, soup in url_data}
                for url, future in futures.items():
                    result = future.result()
                    results.append({
                        'URL': url,
                        'HTTP -> HTTPS': result.get("http_https"),
                        'Redirection Slash': result.get("trailing_slash"),
                        'Images > 100Ko': result.get("large_images"),
                        'Balises Alt vides': result.get("empty_alt")
                    })
                    gc.collect()

            # Créer un DataFrame à partir des résultats
            df_results = pd.DataFrame(results)

            # Affichage et téléchargement des résultats
            st.write("Résultats :")
            st.dataframe(df_results)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, sheet_name="Résultats", index=False)

            output.seek(0)  # Rewind the buffer to the beginning

            # Téléchargement du fichier Excel
            st.download_button(label="Télécharger le fichier Excel",
                               data=output.getvalue(),
                               file_name="site_analysis_results.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error("Veuillez entrer une URL valide.")

if __name__ == "__main__":
    main()
