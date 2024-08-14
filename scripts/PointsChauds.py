import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

# Fonction pour scrapper les balises title, h1, h2, h3, h4
def scrape_tags_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        
        title = soup.title.string if soup.title else ""
        h1 = soup.h1.get_text(strip=True) if soup.h1 else ""
        
        hn_texts = []
        for tag in ['h2', 'h3', 'h4']:
            tags = soup.find_all(tag)
            for t in tags:
                hn_texts.append(t.get_text(strip=True))
        
        hn_text = " | ".join(hn_texts)  # Structure lisible des balises h2, h3, h4

        return url, title, h1, hn_text
    except Exception as e:
        return url, "Error", "Error", str(e)

# Fonction pour lancer le scraping en parallèle
def scrape_all_urls(urls):
    scraped_results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(scrape_tags_from_url, url): url for url in urls}
        for future in as_completed(future_to_url):
            url, title, h1, hn_text = future.result()
            scraped_results.append((url, title, h1, hn_text))
    return scraped_results

# Fonction principale pour l'application Streamlit
def main():
    st.title("Vérification de mot-clé dans des pages web")

    # Chargement du fichier xlsx
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type=["xlsx", "xls"])

    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write("Aperçu du fichier :")
        st.dataframe(df)

        # Sélection des colonnes
        keyword_column = st.selectbox("Sélectionnez la colonne contenant les mots-clés", df.columns)
        url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)

        if st.button("Lancer le crawl"):
            urls = df[url_column].dropna().tolist()
            scraped_data_list = scrape_all_urls(urls)
            
            # Ajouter les colonnes au fichier importé
            for url, title, h1, hn_text in scraped_data_list:
                # Recherchez l'index de la ligne dans le dataframe correspondant à l'URL
                idx = df[df[url_column] == url].index[0]
                df.at[idx, 'Balise Title'] = title
                df.at[idx, 'H1'] = h1
                df.at[idx, 'Hn Structure'] = hn_text

            # Affichage du résultat
            st.write("Résultat du crawl :")
            st.dataframe(df)

            # Créer un fichier Excel pour téléchargement
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            excel_data = output.getvalue()
            
            st.download_button(
                label="Télécharger le fichier avec les résultats",
                data=excel_data,
                file_name="résultat_scraping.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
