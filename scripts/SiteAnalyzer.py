import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import re
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# Fonction pour crawler les URLs du site
def crawl_website(domain, max_urls=1000):
    crawled_urls = set()
    to_crawl = {domain}
    exclude_extensions = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip")

    def fetch_url(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
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

# Fonction pour vérifier la présence du fichier sitemap.xml
def check_sitemap(domain):
    sitemap_urls = [
        f"{domain}/sitemap.xml",
        f"{domain}/sitemap_index.xml",
        f"{domain}/index_sitemap.xml"
    ]
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                return "Oui"
        except requests.exceptions.RequestException:
            continue
    return "Non"

# Fonction pour vérifier les redirections HTTP -> HTTPS
def check_http_https_redirection(url):
    http_url = url.replace("https://", "http://", 1)
    try:
        response = requests.head(http_url, allow_redirects=False)
        if response.status_code in [301, 302]:
            location = response.headers.get('Location', '')
            if location.startswith("https://"):
                return "Oui"
    except requests.exceptions.RequestException:
        pass
    return "Non"

# Fonction pour vérifier les redirections avec/sans slash
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

# Fonction pour vérifier la présence d'une balise canonical et sa validité
def check_canonical_tag(url):
    try:
        response = requests.get(url)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return "Absente"

        soup = BeautifulSoup(response.text, 'html.parser')
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag:
            canonical_url = canonical_tag['href']
            if canonical_url == url:
                return "Oui"
            else:
                return f"Différente (Canonical vers: {canonical_url})"
        else:
            return "Absente"
    except requests.exceptions.RequestException:
        return "Erreur"

# Fonction pour vérifier la présence d'un fichier robots.txt
def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return "Oui"
        else:
            return "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

# Fonction pour analyser les images sur une page
def analyze_images(url):
    try:
        response = requests.get(url)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return 0, 0, 0, 0  # Ignorer les non-HTML

        soup = BeautifulSoup(response.text, 'html.parser')
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

# Fonction pour vérifier les liens 404 et 301 sur une page
def check_links(url):
    try:
        response = requests.get(url)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return 0, 0

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)

        broken_links = 0
        redirects = 0

        for link in links:
            link_url = link['href']
            if link_url.startswith('/'):
                link_url = urljoin(url, link_url)
            try:
                link_response = requests.head(link_url, allow_redirects=True)
                if link_response.status_code == 404:
                    broken_links += 1
                if len(link_response.history) > 0 and link_response.history[0].status_code == 301:
                    redirects += 1
            except requests.exceptions.RequestException:
                broken_links += 1

        return broken_links, redirects
    except requests.exceptions.RequestException:
        return 0, 0

# Fonction principale
def main():
    st.title("Site Analyzer - Analyse complète")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")

            # Récupération des URLs
            urls = crawl_website(domain)

            # Initialisation des résultats
            results = {
                "http_https_redirections": [],
                "trailing_slash_redirections": [],
                "redirect_chains": [],
                "images_results": [],
                "canonical_results": [],
                "robots_txt": check_robots_txt(domain),
                "sitemap": check_sitemap(domain),
                "broken_links_total": 0,
                "redirects_total": 0,
                "404_links": []
            }

            # Analyse des critères
            for url in urls:
                results["http_https_redirections"].append(check_http_https_redirection(url))
                results["trailing_slash_redirections"].append(check_trailing_slash_redirection(url))
                results["redirect_chains"].append(check_redirect_chain(url))
                canonical_result = check_canonical_tag(url)
                results["canonical_results"].append(canonical_result)
                if canonical_result != "Absente" and canonical_result != "Erreur":
                    results["404_links"].append(url)

                large_images, large_img_percentage, empty_alt_count, total_images = analyze_images(url)
                results["images_results"].append((large_images, large_img_percentage, empty_alt_count, total_images))

                broken_links, redirects = check_links(url)
                results["broken_links_total"] += broken_links
                results["redirects_total"] += redirects

            # Résumé général pour la première feuille
            results_summary = {
                "Critère": [
                    "Redirection HTTP -> HTTPS",
                    "Redirection avec/sans slash",
                    "Chaînes de redirection",
                    "Images > 100 ko",
                    "Balises alt vides",
                    "Canonical",
                    "robots.txt",
                    "Sitemap",
                    "Liens 404",
                    "Redirections 301"
                ],
                "Présence": [
                    f"{results['http_https_redirections'].count('Oui')}/{len(results['http_https_redirections'])}",
                    f"{results['trailing_slash_redirections'].count('Oui')}/{len(results['trailing_slash_redirections'])}",
                    len([chain for chain in results["redirect_chains"] if chain != "Non"]),
                    f"{sum(res[0] for res in results['images_results'])}/{len(results['images_results'])}",
                    f"{sum(res[2] for res in results['images_results'])}/{sum(res[3] for res in results['images_results'])}",
                    f"{results['canonical_results'].count('Oui')}/{len(results['canonical_results'])}",
                    results["robots_txt"],
                    results["sitemap"],
                    str(results["broken_links_total"]),
                    str(results["redirects_total"])
                ]
            }

            df_summary = pd.DataFrame(results_summary)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_summary.to_excel(writer, sheet_name="Résumé", index=False)

                # Onglet pour les liens en 404
                df_404 = pd.DataFrame(results["404_links"], columns=["URL"])
                df_404.to_excel(writer, sheet_name="Liens 404", index=False)

                # Onglet pour les canonical
                df_canonical = pd.DataFrame(results["canonical_results"], columns=["URL", "Canonical"])
                df_canonical.to_excel(writer, sheet_name="Canonical", index=False)

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
