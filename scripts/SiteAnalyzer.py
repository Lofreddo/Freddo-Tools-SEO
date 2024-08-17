import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc

# Fonction pour crawler les URLs du site en utilisant le multithreading pour plus de rapidité
def crawl_website(domain, max_urls=1000):
    crawled_urls = set()
    to_crawl = {domain}
    exclude_extensions = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip")
    
    def fetch_url(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                new_links = set()
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    full_url = urljoin(domain, href)
                    if not any(full_url.lower().endswith(ext) for ext in exclude_extensions):
                        if urlparse(full_url).netloc == urlparse(domain).netloc and full_url not in crawled_urls:
                            new_links.add(full_url)
                return url, new_links
        except requests.exceptions.RequestException:
            return url, set()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_url, url): url for url in to_crawl}
        counter = 0
        
        while futures and len(crawled_urls) < max_urls:
            for future in as_completed(futures):
                try:
                    url, new_links = future.result()
                    crawled_urls.add(url)
                    to_crawl.update(new_links - crawled_urls)
                    counter += 1

                    if counter % 250 == 0:
                        st.write(f"{counter} URLs crawled jusqu'à présent...")
                    
                    if len(crawled_urls) >= max_urls:
                        break
                except Exception as e:
                    st.write(f"Erreur lors du crawl de {url}: {e}")
            
            futures = {executor.submit(fetch_url, url): url for url in to_crawl}
            to_crawl.clear()
    
    return list(crawled_urls)

# Fonction pour explorer le sitemap
def explore_sitemap(sitemap_url):
    urls = set()
    try:
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.content, 'xml')
        if soup.find_all("sitemap"):
            for sitemap in soup.find_all("sitemap"):
                loc = sitemap.findNext("loc").text
                urls.update(explore_sitemap(loc))
        else:
            for loc in soup.find_all("loc"):
                urls.add(loc.text.strip())
    except requests.exceptions.RequestException:
        pass
    return urls

# Fonction pour obtenir toutes les URLs du site
def get_all_urls(domain):
    sitemap_urls = explore_sitemap(f"{domain}/sitemap.xml")
    if sitemap_urls:
        st.write(f"{len(sitemap_urls)} URLs trouvées dans le sitemap.")
        return list(sitemap_urls)
    
    st.write("Aucun sitemap trouvé ou index. Démarrage du crawling à partir de la page d'accueil...")
    return crawl_website(domain)

# Fonction pour vérifier la redirection HTTP -> HTTPS
def check_http_https_redirection(url):
    if url.startswith("https://"):
        http_url = url.replace("https://", "http://", 1)
        try:
            response = requests.head(http_url, allow_redirects=False)
            if response.status_code in [301, 302] and 'Location' in response.headers:
                if response.headers['Location'].startswith("https://"):
                    return "Oui"
        except requests.exceptions.RequestException:
            pass
    return "Non"

# Fonction pour vérifier la redirection avec/sans slash
def check_trailing_slash_redirection(url):
    if url.endswith("/"):
        url_without_slash = url.rstrip("/")
        try:
            response = requests.head(url_without_slash, allow_redirects=False)
            if response.status_code in [301, 302] and 'Location' in response.headers:
                if response.headers['Location'].endswith("/"):
                    return "Oui"
        except requests.exceptions.RequestException:
            pass
    else:
        url_with_slash = url + "/"
        try:
            response = requests.head(url_with_slash, allow_redirects=False)
            if response.status_code in [301, 302] and 'Location' in response.headers:
                if response.headers['Location'] == url:
                    return "Oui"
        except requests.exceptions.RequestException:
            pass
    return "Non"

# Fonction pour vérifier les chaînes de redirection
def check_redirect_chain(url):
    try:
        response = requests.head(url, allow_redirects=True)
        if len(response.history) > 1:
            return f"Oui ({len(response.history)} redirections)"
    except requests.exceptions.RequestException:
        pass
    return "Non"

# Fonction pour analyser les images sur une page
def analyze_images(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        images = soup.find_all('img')
        
        large_images = 0
        total_images = len(images)
        empty_alt_count = 0
        
        for img in images:
            img_url = img.get('src')
            alt_text = img.get('alt', '').strip()
            if alt_text == "":
                empty_alt_count += 1
            if img_url:
                full_img_url = urljoin(url, img_url)
                try:
                    img_response = requests.head(full_img_url, allow_redirects=True)
                    img_size = int(img_response.headers.get('content-length', 0))
                    if img_size > 100 * 1024:  # 100 ko
                        large_images += 1
                except requests.exceptions.RequestException:
                    continue
        
        large_img_percentage = (large_images / total_images) * 100 if total_images > 0 else 0
        return large_images, large_img_percentage, empty_alt_count, total_images
    except requests.exceptions.RequestException:
        return 0, 0, 0, 0

# Fonction pour traiter les URLs avec multithreading
def process_urls(urls):
    max_workers = min(20, len(urls) // 10 + 1)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_images, url): url for url in urls}
        
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception as e:
                st.write(f"Erreur lors de l'analyse de {url}: {e}")
            finally:
                gc.collect()

    return results

# Fonction principale
def main():
    st.title("Site Analyzer - Optimisé")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")

            # Récupération des URLs
            urls = get_all_urls(domain)

            # Analyse des redirections HTTP -> HTTPS, trailing slash, chaînes de redirections et images
            http_https_redirections = []
            trailing_slash_redirections = []
            redirect_chains = []
            images_results = process_urls(urls)

            for url in urls:
                http_https_redirections.append(check_http_https_redirection(url))
                trailing_slash_redirections.append(check_trailing_slash_redirection(url))
                redirect_chains.append(check_redirect_chain(url))

            # Résumé général pour la première feuille
            results_summary = {
                "Critère": [
                    "Redirection HTTP -> HTTPS",
                    "Redirection avec/sans slash",
                    "Chaînes de redirection",
                    "Images > 100 ko",
                    "Balises alt vides"
                ],
                "Présence": [
                    f"{http_https_redirections.count('Oui')}/{len(http_https_redirections)}",
                    f"{trailing_slash_redirections.count('Oui')}/{len(trailing_slash_redirections)}",
                    f"{redirect_chains.count('Oui')}/{len(redirect_chains)}",
                    f"{sum(res[0] for res in images_results.values())}/{len(images_results)}",
                    f"{sum(res[2] for res in images_results.values())}/{sum(res[3] for res in images_results.values())}"
                ]
            }

            df_summary = pd.DataFrame(results_summary)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_summary.to_excel(writer, sheet_name="Résumé", index=False)

            output.seek(0)

            st.write("Analyse terminée.")

            # Téléchargement du fichier Excel
            st.download_button(
                label="Télécharger le fichier Excel",
                data=output.getvalue(),
                file_name="site_analysis_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Veuillez entrer une URL valide.")

if __name__ == "__main__":
    main()
