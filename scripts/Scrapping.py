import streamlit as st
import pandas as pd
from io import BytesIO
from playwright.sync_api import sync_playwright
import re

# Fonction pour nettoyer le contenu HTML
def clean_html_content(soup):
    for tag in soup.find_all(['span', 'div', 'label', 'img', 'path', 'svg', 'em', 'th', 'strong']):
        tag.unwrap()
    for tag in soup.find_all(['tr', 'td', 'table', 'button']):
        tag.decompose()
    for tag in soup.find_all('a', href=True):
        tag.unwrap()
    for tag in soup.find_all(True):
        tag.attrs = {}
    for tag in soup.find_all():
        if not tag.get_text(strip=True):
            tag.decompose()
    return soup

# Fonction pour extraire le contenu avec Playwright
def get_hn_and_content(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup.find_all(['header', 'footer']):
            tag.decompose()

        clean_soup = clean_html_content(soup)

        html_content = ""
        structure_hn = []

        for tag in clean_soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'ul', 'li', 'ol']):
            if tag.get_text(strip=True):
                html_content += str(tag) + '\n'
            if tag.name.startswith('h'):
                structure_hn.append(f"<{tag.name}>{tag.get_text(strip=True)}</{tag.name}>")

        structure_hn_str = "\n".join(structure_hn)

        html_content = re.sub(r'\t+', ' ', html_content)
        html_content = re.sub(' +', ' ', html_content)
        html_content = "\n".join([line for line in html_content.splitlines() if line.strip()])

        return html_content.strip(), structure_hn_str

    except Exception as e:
        print(f"Error fetching content for {url}: {e}")
        return None, None

# Fonction pour générer la sortie en DataFrame
def generate_output(urls):
    contents = [get_hn_and_content(url) for url in urls]

    df = pd.DataFrame({
        'url': urls,
        'content': [content for content, _ in contents],
        'structure_hn': [structure for _, structure in contents]
    })

    return df

# Fonction principale pour l'interface Streamlit
def main():
    st.title("Scraping Tool")

    st.subheader("Entrez les URLs à scraper (une URL par ligne):")
    urls_input = st.text_area("Entrez vos URLs ici", height=200)

    urls = [url.strip() for url in urls_input.splitlines() if url.strip()]

    if st.button("Lancer le scraping"):
        if urls:
            df = generate_output(urls)

            st.subheader("Aperçu des résultats")
            st.write(df)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button(
                label="Télécharger le fichier Excel",
                data=buffer.getvalue(),
                file_name="output.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.warning("Veuillez entrer au moins une URL.")

if __name__ == "__main__":
    main()
