import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from nltk.stem import PorterStemmer
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import lxml.html

# Initialisation du stemmer
stemmer = PorterStemmer()

# Liste des articles et pronoms à exclure
exclusion_list = [
    'le', 'la', 'les', 'l\'', 'un', 'une', 'des', 'du', 'de la', 'de l\'', 
    'mon', 'ton', 'son', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs'
]

def remove_exclusions(text):
    words = text.lower().split()
    filtered_words = [word for word in words if word not in exclusion_list]
    return ' '.join(filtered_words)

def get_stem(word):
    return stemmer.stem(word.lower())

def similar_phrases(phrase1, phrase2):
    return SequenceMatcher(None, phrase1, phrase2).ratio()

def check_keyword_in_text(text, keyword):
    text = remove_exclusions(text)
    keyword = remove_exclusions(keyword)
    stemmed_text = " ".join([get_stem(word) for word in text.split()])
    stemmed_keyword = " ".join([get_stem(part) for part in keyword.split()])
    
    if stemmed_keyword in stemmed_text:
        return True
    
    similarity = similar_phrases(stemmed_text, stemmed_keyword)
    return similarity > 0.8

# Fonction pour extraire et vérifier les balises HTML principales
def extract_and_check(url):
    try:
        headers = {'Accept': 'text/html'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 404:
            return {
                'Balise Title': 'Erreur 404',
                'H1': 'Erreur 404',
                'Hn Structure': 'Erreur 404',
                'Redirection URL': 'N/A'
            }
        
        if len(response.history) > 0 and response.history[0].status_code == 301:
            return {
                'Balise Title': 'Redirection 301',
                'H1': 'Redirection 301',
                'Hn Structure': 'Redirection 301',
                'Redirection URL': 'Redirection 301'
            }

        response.raise_for_status()
        tree = lxml.html.fromstring(response.content)
        
        title = tree.xpath('//title/text()')
        h1 = tree.xpath('//h1/text()')
        
        hn_elements = tree.xpath('//h2 | //h3 | //h4 | //h5')
        hn_texts = []
        for el in hn_elements:
            hn_text = f"<{el.tag}>{el.text_content()}</{el.tag}>"
            hn_texts.append(hn_text)
        
        hn_text = "\n".join(hn_texts)
        
        return {
            'Balise Title': title[0] if title else "",
            'H1': h1[0] if h1 else "",
            'Hn Structure': hn_text,
            'Redirection URL': 'Pas de redirection'
        }
    except requests.exceptions.RequestException as e:
        return {
            'Balise Title': 'Erreur',
            'H1': 'Erreur',
            'Hn Structure': 'Erreur',
            'Redirection URL': 'Erreur'
        }

def process_urls(df, keyword_column, url_column, progress_bar, time_estimation):
    url_results = {}
    total_urls = len(df)
    start_time = time.time()

    max_workers = min(20, total_urls // 10 + 1)  # Ajuste dynamiquement le nombre de threads

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for index, row in df.iterrows():
            url = row[url_column]
            if url not in url_results:
                futures[url] = executor.submit(extract_and_check, url)
        
        completed = 0
        update_interval = 100
        for url, future in futures.items():
            url_results[url] = future.result()
            completed += 1
            
            if completed % update_interval == 0:
                progress_bar.progress(completed / total_urls)
                
                elapsed_time = time.time() - start_time
                time_per_url = elapsed_time / completed
                estimated_total_time = time_per_url * total_urls
                time_left = estimated_total_time - elapsed_time
                time_estimation.text(f"Temps estimé restant : {int(time_left // 60)} min {int(time_left % 60)} sec")
    
    return url_results

def main():
    st.title("Vérification de mot-clé dans des pages web")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("Aperçu du fichier :")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")
            return

        keyword_column = st.selectbox("Sélectionnez la colonne contenant les mots-clés", df.columns)
        url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)

        if st.button("Lancer le crawl"):
            progress_bar = st.progress(0)
            time_estimation = st.empty()

            st.write("Initialisation des colonnes et démarrage du scraping en parallèle...")
            url_results = process_urls(df, keyword_column, url_column, progress_bar, time_estimation)
            
            for index, row in df.iterrows():
                keyword = row[keyword_column]
                url = row[url_column]
                result = url_results[url]
                
                title_match = check_keyword_in_text(result['Balise Title'], keyword)
                h1_match = check_keyword_in_text(result['H1'], keyword)
                hn_match = check_keyword_in_text(result['Hn Structure'], keyword)

                df.at[index, 'Balise Title'] = result['Balise Title']
                df.at[index, 'Title Match'] = "Oui" if title_match else "Non"
                df.at[index, 'H1'] = result['H1']
                df.at[index, 'H1 Match'] = "Oui" if h1_match else "Non"
                df.at[index, 'Hn Structure'] = result['Hn Structure']
                df.at[index, 'Hn Match'] = "Oui" if hn_match else "Non"
                df.at[index, 'Redirection URL'] = result['Redirection URL']

            st.write("Résultat du crawl :")
            st.dataframe(df)

            try:
                output_file = BytesIO()
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                st.download_button(
                    label="Télécharger le fichier avec les résultats",
                    data=output_file.getvalue(),
                    file_name="résultat_scraping.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Erreur lors de la création du fichier Excel : {e}")

if __name__ == "__main__":
    main()
