import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import io

def get_all_urls_from_sitemap(domain):
    sitemaps = [f"{domain}/sitemap.xml", f"{domain}/sitemap_index.xml", f"{domain}/index_sitemap.xml"]
    all_urls = set()
    
    for sitemap_url in sitemaps:
        try:
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "xml")
                urls = soup.find_all("loc")
                for url in urls:
                    all_urls.add(url.text.strip())
        except requests.exceptions.RequestException:
            continue
    
    return all_urls

def get_all_urls(domain):
    st.write("Tentative de récupération des URLs à partir du sitemap...")
    sitemap_urls = get_all_urls_from_sitemap(domain)
    
    if sitemap_urls:
        st.write(f"{len(sitemap_urls)} URLs trouvées dans le sitemap.")
        return sitemap_urls
    
    st.write("Aucun sitemap trouvé. Démarrage du crawling à partir de la page d'accueil...")
    crawled_urls = set()
    to_crawl = {domain}
    
    while to_crawl:
        url = to_crawl.pop()
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            crawled_urls.add(url)
            for link in soup.find_all('a', href=True):
                full_url = urljoin(domain, link['href'])
                if urlparse(full_url).netloc == urlparse(domain).netloc and full_url not in crawled_urls:
                    to_crawl.add(full_url)
            st.write(f"{len(crawled_urls)} URLs crawled jusqu'à présent...")
        except requests.exceptions.RequestException:
            continue
            
    st.write(f"Crawling terminé. {len(crawled_urls)} URLs trouvées.")
    return crawled_urls

def check_canonical_for_all_urls(urls):
    results = []
    
    for url in urls:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            canonical_tag = soup.find('link', rel='canonical')
            
            if canonical_tag:
                canonical_url = canonical_tag['href']
                if canonical_url == url:
                    status = "Correcte"
                else:
                    status = f"Différente (Canonical vers: {canonical_url})"
            else:
                status = "Absente"
            
            results.append({"URL": url, "Canonical": canonical_url if canonical_tag else "N/A", "Statut": status})
        
        except requests.exceptions.RequestException:
            results.append({"URL": url, "Canonical": "Erreur d'accès", "Statut": "Non vérifiable"})
    
    return results

def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    response = requests.get(url)
    return response.status_code == 200

def check_sitemap(domain):
    sitemaps = ["sitemap.xml", "sitemap_index.xml", "index_sitemap.xml"]
    for sitemap in sitemaps:
        url = f"{domain}/{sitemap}"
        response = requests.get(url)
        if response.status_code == 200:
            return True
    return False

def check_links(domain):
    response = requests.get(domain)
    soup = BeautifulSoup(response.text, 'html.parser')
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
            canonical_results = check_canonical_for_all_urls(urls)

            # Résumé général pour la première feuille
            results_summary = {"Critère": [], "Présence": []}
            robots_exists = check_robots_txt(domain)
            results_summary["Critère"].append("Robots.txt")
            results_summary["Présence"].append("Oui" if robots_exists else "Non")

            sitemap_exists = check_sitemap(domain)
            results_summary["Critère"].append("Sitemap")
            results_summary["Présence"].append("Oui" if sitemap_exists else "Non")
            
            broken_links, redirects = check_links(domain)
            results_summary["Critère"].append("Liens 404")
            results_summary["Présence"].append(str(broken_links) if broken_links > 0 else "Non")
            results_summary["Critère"].append("Redirections 301")
            results_summary["Présence"].append(str(redirects) if redirects > 0 else "Non")

            df_summary = pd.DataFrame(results_summary)
            df_canonical = pd.DataFrame(canonical_results)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_summary.to_excel(writer, sheet_name="Résumé", index=False)
                df_canonical.to_excel(writer, sheet_name="Canonical", index=False)
                writer.save()

            st.write("Analyse terminée.")

            # Téléchargement du fichier Excel
            st.download_button(label="Télécharger le fichier Excel",
                               data=output.getvalue(),
                               file_name="site_analysis_results.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error("Veuillez entrer une URL valide.")
