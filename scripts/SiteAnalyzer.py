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
                    if counter % 100 == 0:
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
    sitemap_urls = [f"{domain}/sitemap.xml", f"{domain}/sitemap_index.xml", f"{domain}/index_sitemap.xml"]
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                return "Oui"
        except requests.exceptions.RequestException:
            continue
    return "Non"

def check_subdomains(domain):
    return "Vérification manuelle requise"

def check_links(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        broken_links = 0
        redirects = 0
        for link in links:
            link_url = urljoin(url, link['href'])
            try:
                link_response = requests.head(link_url, allow_redirects=False)
                if link_response.status_code == 404:
                    broken_links += 1
                elif link_response.status_code in [301, 302]:
                    redirects += 1
            except requests.exceptions.RequestException:
                broken_links += 1
        return broken_links, redirects
    except requests.exceptions.RequestException:
        return 0, 0

def check_canonical_tag(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag:
            canonical_url = canonical_tag['href']
            return "Oui" if canonical_url == url else f"Différente ({canonical_url})"
        return "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_internal_links_to_canonicals(url):
    return "Vérification manuelle requise"

def check_http_https_redirection(url):
    http_url = url.replace("https://", "http://", 1)
    try:
        response = requests.head(http_url, allow_redirects=False)
        return "Oui" if response.status_code in [301, 302] and response.headers.get('Location', '').startswith("https://") else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_trailing_slash_redirection(url):
    try:
        with_slash = url if url.endswith('/') else url + '/'
        without_slash = url[:-1] if url.endswith('/') else url
        response_with = requests.head(with_slash, allow_redirects=False)
        response_without = requests.head(without_slash, allow_redirects=False)
        return "Oui" if (response_with.status_code in [301, 302] or response_without.status_code in [301, 302]) else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_redirect_chain(url):
    try:
        response = requests.get(url, allow_redirects=True)
        return "Oui" if len(response.history) > 1 else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def analyze_images(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find_all('img')
        total_images = len(images)
        large_images = sum(1 for img in images if int(requests.head(urljoin(url, img.get('src', ''))).headers.get('content-length', 0)) > 100 * 1024)
        empty_alt_count = sum(1 for img in images if not img.get('alt'))
        return large_images, (large_images / total_images) * 100 if total_images > 0 else 0, empty_alt_count, total_images
    except requests.exceptions.RequestException:
        return 0, 0, 0, 0

def check_lazy_loading(url):
    try:
        response = requests.get(url)
        return "Oui" if 'loading="lazy"' in response.text else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_noindex(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return "Oui" if soup.find('meta', attrs={'name': 'robots', 'content': re.compile(r'noindex', re.I)}) else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_hreflang(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return "Oui" if soup.find('link', rel='alternate', hreflang=True) else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_title_length(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else ""
        return "Oui" if len(title) > 70 else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_breadcrumb(url):
    try:
        response = requests.get(url)
        return "Oui" if 'class="breadcrumb"' in response.text or 'itemtype="http://schema.org/BreadcrumbList"' in response.text else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_internal_links_count(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        internal_links = len([link for link in soup.find_all('a', href=True) if urlparse(link['href']).netloc == urlparse(url).netloc or not urlparse(link['href']).netloc])
        return "Oui" if internal_links > 5 else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_javascript_in_body(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return "Oui" if soup.body.find('script') else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_inline_css(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return "Oui" if soup.find('style') or soup.find(style=True) else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_utm_links(url):
    try:
        response = requests.get(url)
        return "Oui" if 'utm_' in response.text else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_unique_title_h1(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else ""
        h1 = soup.h1.string if soup.h1 else ""
        return "Oui" if title.strip() != h1.strip() else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_heading_structure(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        for i in range(len(headings) - 1):
            if int(headings[i].name[1]) - int(headings[i+1].name[1]) < -1:
                return "Non"
        return "Oui"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_line_breaks(url):
    try:
        response = requests.get(url)
        return "Oui" if '\n' in response.text else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_html5_tags(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        html5_tags = ['header', 'nav', 'article', 'section', 'aside', 'footer']
        return "Oui" if any(soup.find(tag) for tag in html5_tags) else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_structured_data(url):
    try:
        response = requests.get(url)
        return "Oui" if 'application/ld+json' in response.text else "Non"
    except requests.exceptions.RequestException:
        return "Erreur"

def check_ssl_certificate(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
                return "Oui"
    except:
        return "Non"

def analyze_url(url):
    return {
        "URL": url,
        "Canonical": check_canonical_tag(url),
        "HTTP -> HTTPS": check_http_https_redirection(url),
        "Redirection /": check_trailing_slash_redirection(url),
        "Chaîne de redirection": check_redirect_chain(url),
        "Lazy loading": check_lazy_loading(url),
        "Noindex": check_noindex(url),
        "Hreflang": check_hreflang(url),
        "Title > 70 car": check_title_length(url),
        "Breadcrumb": check_breadcrumb(url),
        "Liens internes > 5": check_internal_links_count(url),
        "JS dans <body>": check_javascript_in_body(url),
        "CSS inline": check_inline_css(url),
        "Liens UTM": check_utm_links(url),
        "Title et H1 uniques": check_unique_title_h1(url),
        "Structure Hn correcte": check_heading_structure(url),
        "Retours à la ligne": check_line_breaks(url),
        "Balises HTML5": check_html5_tags(url),
        "Données structurées": check_structured_data(url)
    }

def main():
    st.title("Site Analyzer - Analyse complète")
    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            st.write("Démarrage de l'analyse...")

            urls = crawl_website(domain)
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(analyze_url, urls))
            
            df = pd.DataFrame(results)
            
            global_checks = {
                "robots.txt": check_robots_txt(domain),
                "Sitemap": check_sitemap(domain),
                "Sous-domaines": check_subdomains(domain),
                "Certificat SSL": check_ssl_certificate(urlparse(domain).netloc)
            }
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame([global_checks]).to_excel(writer, sheet_name="Vérifications globales", index=False)
                df.to_excel(writer, sheet_name="Analyse détaillée", index=False)
            
            output.seek(0)
            st.write("Analyse terminée.")
            
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
