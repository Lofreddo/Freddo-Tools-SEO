import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import io

def crawl_website(domain, max_urls=1000):
    crawled_urls = set()
    to_crawl = {domain}
    
    while to_crawl and len(crawled_urls) < max_urls:
        url = to_crawl.pop()
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                crawled_urls.add(url)
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    full_url = urljoin(domain, href)
                    
                    if urlparse(full_url).netloc == urlparse(domain).netloc and full_url not in crawled_urls:
                        to_crawl.add(full_url)
                        
                st.write(f"{len(crawled_urls)} URLs crawled jusqu'à présent...")
        except requests.exceptions.RequestException:
            continue
    
    return crawled_urls

def explore_sitemap(sitemap_url):
    urls = set()
    try:
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.content, 'xml')
        if soup.find_all("sitemap"):
            # It is a sitemap index, explore each listed sitemap
            for sitemap in soup.find_all("sitemap"):
                loc = sitemap.findNext("loc").text
                urls.update(explore_sitemap(loc))
        else:
            # It is a regular sitemap, collect all URLs
            for loc in soup.find_all("loc"):
                urls.add(loc.text.strip())
    except requests.exceptions.RequestException:
        pass
    return urls

def get_all_urls(domain):
    sitemap_urls = explore_sitemap(f"{domain}/sitemap.xml")
    if sitemap_urls:
        st.write(f"{len(sitemap_urls)} URLs trouvées dans le sitemap.")
        return sitemap_urls
    
    st.write("Aucun sitemap trouvé ou index. Démarrage du crawling à partir de la page d'accueil...")
    return crawl_website(domain)

def check_canonical_for_all_urls(urls):
    image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")
    
    # Filtrer les URLs pour exclure celles qui pointent vers des images
    filtered_urls = [url for url in urls if not url.lower().endswith(image_extensions)]
    
    results = []
    correct_canonical_count = 0
    
    for url in filtered_urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            canonical_tag = soup.find('link', rel='canonical')
            
            if canonical_tag:
                canonical_url = canonical_tag['href']
                if canonical_url == url:
                    status = "Correcte"
                    correct_canonical_count += 1
                else:
                    status = f"Différente (Canonical vers: {canonical_url})"
            else:
                status = "Absente"
            
            results.append({"URL": url, "Canonical": canonical_url if canonical_tag else "N/A", "Statut": status})
        
        except requests.exceptions.RequestException:
            results.append({"URL": url, "Canonical": "Erreur d'accès", "Statut": "Non vérifiable"})
    
    return results, correct_canonical_count, len(filtered_urls)

def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    response = requests.get(url)
    return response.status_code == 200

def check_links(domain):
    response = requests.get(domain)
    soup = BeautifulSoup(response.text, 'lxml')
    links = soup.find_all('a', href=True)
    
    broken_links = 0
    redirects = 0
    
    for link in links:
        url = link['href']
        if url.startswith('/'):
            url = domain + url
        try:
            link_response = requests.head(url, allow_redirects=True)
            if link_response.status_code == 404:
                broken_links += 1
            if len(link_response.history) > 0:
                redirects += 1
        except requests.exceptions.RequestException:
            broken_links += 1
            
    return broken_links, redirects

def main():
    st.title("Site Analyzer - Vérification des balises Canonical et SEO")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")

            # Crawler toutes les URLs du site
            urls = get_all_urls(domain)

            # Vérification des balises canonical pour chaque URL
            st.write("Vérification des balises canonical...")
            canonical_results, correct_canonical_count, total_urls_checked = check_canonical_for_all_urls(urls)

            # Résumé général pour la première feuille
            results_summary = {"Critère": [], "Présence": []}
            robots_exists = check_robots_txt(domain)
            results_summary["Critère"].append("Robots.txt")
            results_summary["Présence"].append("Oui" if robots_exists else "Non")

            broken_links, redirects = check_links(domain)
            results_summary["Critère"].append("Liens 404")
            results_summary["Présence"].append(str(broken_links) if broken_links > 0 else "Non")
            results_summary["Critère"].append("Redirections 301")
            results_summary["Présence"].append(str(redirects) if redirects > 0 else "Non")

            # Ajouter la ligne Canonical
            results_summary["Critère"].append("Canonical")
            results_summary["Présence"].append(f"{correct_canonical_count}/{total_urls_checked}")

            df_summary = pd.DataFrame(results_summary)
            df_canonical = pd.DataFrame(canonical_results)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_summary.to_excel(writer, sheet_name="Résumé", index=False)
                df_canonical.to_excel(writer, sheet_name="Canonical", index=False)

            output.seek(0)  # Rewind the buffer to the beginning

            st.write("Analyse terminée.")

            # Téléchargement du fichier Excel
            st.download_button(label="Télécharger le fichier Excel",
                               data=output.getvalue(),
                               file_name="site_analysis_results.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error("Veuillez entrer une URL valide.")
