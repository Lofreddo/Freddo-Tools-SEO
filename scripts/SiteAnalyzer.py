import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd

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

def check_canonical(domain):
    response = requests.get(domain)
    soup = BeautifulSoup(response.text, 'html.parser')
    canonical = soup.find('link', rel='canonical')
    if canonical:
        canonical_url = canonical['href']
        if canonical_url == domain:
            return "Oui"
        else:
            return f"Non, Canonical vers: {canonical_url}"
    return "Non"

def main():
    st.title("Site Analyzer")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            results = {"Critère": [], "Présence": []}

            # Vérifier robots.txt
            robots_exists = check_robots_txt(domain)
            results["Critère"].append("Robots.txt")
            results["Présence"].append("Oui" if robots_exists else "Non")

            # Vérifier sitemap
            sitemap_exists = check_sitemap(domain)
            results["Critère"].append("Sitemap")
            results["Présence"].append("Oui" if sitemap_exists else "Non")
            
            # Vérifier les liens (404 et 301)
            broken_links, redirects = check_links(domain)
            results["Critère"].append("Liens 404")
            results["Présence"].append(str(broken_links) if broken_links > 0 else "Non")
            results["Critère"].append("Redirections 301")
            results["Présence"].append(str(redirects) if redirects > 0 else "Non")
            
            # Vérifier canonical
            canonical_check = check_canonical(domain)
            results["Critère"].append("Balise Canonical")
            results["Présence"].append(canonical_check)

            df = pd.DataFrame(results)
            st.dataframe(df)

            if st.button("Exporter en Excel"):
                df.to_excel("site_analysis_results.xlsx", index=False)
                st.write("Fichier exporté avec succès.")
        else:
            st.error("Veuillez entrer une URL valide.")
