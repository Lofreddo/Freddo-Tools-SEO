import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from urllib.parse import urljoin, urlparse
import re
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl
import socket
import json
from googlesearch import search

def crawl_website(domain, max_urls=1000):
    crawled_urls = set()
    to_crawl = {domain}
    exclude_extensions = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".zip")

    def fetch_url(url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                new_links = set()
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    full_url = urljoin(domain, href)
                    if not any(full_url.lower().endswith(ext) for ext in exclude_extensions):
                        if urlparse(full_url).netloc == urlparse(domain).netloc and full_url not in crawled_urls:
                            new_links.add(full_url)
                return url, new_links, response.text
        except requests.exceptions.RequestException:
            return url, set(), None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_url, url): url for url in to_crawl}
        counter = 0
        while futures and len(crawled_urls) < max_urls:
            for future in as_completed(futures):
                url, new_links, content = future.result()
                if content:
                    crawled_urls.add(url)
                    to_crawl.update(new_links - crawled_urls)
                    counter += 1
                    if counter % 250 == 0:
                        st.write(f"{counter} URLs crawled jusqu'à présent...")
                    if len(crawled_urls) >= max_urls:
                        break
                futures = {executor.submit(fetch_url, url): url for url in to_crawl if url not in crawled_urls}
                to_crawl.clear()

    return list(crawled_urls)

def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    try:
        response = requests.get(url)
        return "Oui" if response.status_code == 200 else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

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

def check_subdomains(domain):
    query = f"site:{domain} -inurl:www"
    try:
        results = list(search(query, num_results=5))
        return "Oui" if results else "Non"
    except Exception:
        return "Erreur"

def analyze_url(url):
    try:
        response = requests.get(url, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Vérification des redirections
        http_https_redirection = "Oui" if url.startswith("https") and requests.get(url.replace("https", "http", 1)).status_code in [301, 302] else "Non"
        trailing_slash_redirection = "Oui" if (url.endswith("/") and requests.get(url[:-1]).status_code in [301, 302]) or (not url.endswith("/") and requests.get(url + "/").status_code in [301, 302]) else "Non"
        redirect_chain = "Oui" if len(response.history) > 1 else "Non"

        # Analyse des liens
        links = soup.find_all('a', href=True)
        broken_links = sum(1 for link in links if requests.head(urljoin(url, link['href'])).status_code == 404)
        redirects = sum(1 for link in links if requests.head(urljoin(url, link['href'])).status_code == 301)

        # Vérification de la balise canonical
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag:
            canonical_url = canonical_tag['href']
            canonical = "Oui" if canonical_url == url else f"Différente ({canonical_url})"
        else:
            canonical = "Non"

        # Analyse des images
        images = soup.find_all('img')
        large_images = sum(1 for img in images if int(requests.head(urljoin(url, img.get('src', ''))).headers.get('content-length', 0)) > 100 * 1024)
        large_img_percentage = (large_images / len(images)) * 100 if images else 0
        empty_alt = sum(1 for img in images if not img.get('alt'))

        # Autres vérifications
        lazy_loading = "Oui" if soup.find(attrs={"loading": "lazy"}) else "Non"
        noindex = "Oui" if soup.find('meta', attrs={'name': 'robots', 'content': re.compile(r'noindex', re.I)}) else "Non"
        hreflang = "Oui" if soup.find('link', rel='alternate', hreflang=True) else "Non"
        title = soup.title.string if soup.title else ""
        title_length = "Oui" if len(title) > 70 else "Non"
        breadcrumb = "Oui" if soup.find(class_=re.compile(r'breadcrumb', re.I)) else "Non"
        internal_links = len([link for link in links if urlparse(link['href']).netloc == urlparse(url).netloc])
        js_in_body = "Oui" if soup.body.find('script') else "Non"
        inline_css = "Oui" if soup.find('style') or soup.find(style=True) else "Non"
        utm_links = sum(1 for link in links if 'utm_' in link['href'])
        unique_title_h1 = "Oui" if title and soup.h1 and title.strip() != soup.h1.text.strip() else "Non"
        correct_hn_structure = "Oui" if all(int(tag.name[1]) <= int(prev_tag.name[1])+1 for prev_tag, tag in zip(soup.find_all(re.compile(r'h\d')), soup.find_all(re.compile(r'h\d'))[1:])) else "Non"
        line_breaks = "Oui" if '\n' in response.text else "Non"
        unused_scripts = "Non"  # Cette vérification nécessiterait une analyse plus approfondie
        html5_tags = "Oui" if soup.find(['header', 'nav', 'article', 'section', 'aside', 'footer']) else "Non"
        structured_data = "Oui" if soup.find('script', type='application/ld+json') else "Non"

        return {
            "URL": url,
            "HTTP -> HTTPS": http_https_redirection,
            "Redirection /": trailing_slash_redirection,
            "Chaîne de redirection": redirect_chain,
            "Liens 404": f"{broken_links}" if broken_links > 0 else "Non",
            "Redirections 301": f"{redirects}" if redirects > 0 else "Non",
            "Canonical": canonical,
            "Images > 100ko": f"{large_images} ({large_img_percentage:.2f}%)",
            "Alt vides": f"{empty_alt}/{len(images)}",
            "Lazy loading": lazy_loading,
            "Noindex": noindex,
            "Hreflang": hreflang,
            "Title > 70 car": title_length,
            "Breadcrumb": breadcrumb,
            "Liens internes": f"{internal_links}" if internal_links > 5 else "Non",
            "JS dans <body>": js_in_body,
            "CSS inline": inline_css,
            "Liens UTM": f"{utm_links}" if utm_links > 0 else "Non",
            "Title et H1 uniques": unique_title_h1,
            "Structure Hn correcte": correct_hn_structure,
            "Retours à la ligne": line_breaks,
            "Scripts non utilisés": unused_scripts,
            "Balises HTML5": html5_tags,
            "Données structurées": structured_data
        }
    except Exception as e:
        return {"URL": url, "Erreur": str(e)}

def check_ssl(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
                cert = secure_sock.getpeercert()
        return "Oui"
    except:
        return "Non"

def main():
    st.title("Site Analyzer - Analyse complète")
    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")

            # Vérifications générales
            robots_txt = check_robots_txt(domain)
            sitemap = check_sitemap(domain)
            subdomains = check_subdomains(domain)
            ssl_cert = check_ssl(urlparse(domain).netloc)

            # Crawl et analyse des URLs
            urls = crawl_website(domain)
            results = []
            for url in urls:
                result = analyze_url(url)
                results.append(result)

            # Création du DataFrame
            df = pd.DataFrame(results)

            # Création du fichier Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Feuille de résumé
                summary = {
                    "Critère": ["robots.txt", "Sitemap", "Sous-domaines", "Certificat SSL"],
                    "Résultat": [robots_txt, sitemap, subdomains, ssl_cert]
                }
                pd.DataFrame(summary).to_excel(writer, sheet_name="Résumé", index=False)

                # Feuille principale
                df.to_excel(writer, sheet_name="Analyse détaillée", index=False)

            output.seek(0)
            st.write("Analyse terminée.")

            # Bouton de téléchargement
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
