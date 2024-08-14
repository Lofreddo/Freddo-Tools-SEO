import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO
from nltk.stem import PorterStemmer
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Initialisation du stemmer
stemmer = PorterStemmer()

# Liste des articles et pronoms à exclure
exclusion_list = [
    'le', 'la', 'les', 'l\'', 'un', 'une', 'des', 'du', 'de la', 'de l\'', 
    'mon', 'ton', 'son', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs'
]

# Fonction pour supprimer les articles et pronoms exclus
def remove_exclusions(text):
    words = text.lower().split()
    filtered_words = [word for word in words if word not in exclusion_list]
    return ' '.join(filtered_words)

# Fonction pour obtenir la racine d'un mot
def get_stem(word):
    return stemmer.stem(word.lower())

# Fonction pour calculer la similarité entre deux phrases
def similar_phrases(phrase1, phrase2):
    return SequenceMatcher(None, phrase1, phrase2).ratio()

# Fonction pour vérifier la présence du mot-clé dans une balise spécifique avec des règles avancées
def check_keyword_in_text(text, keyword):
    # Supprimer les articles et pronoms exclus
    text = remove_exclusions(text)
    keyword = remove_exclusions(keyword)

    # Appliquer le stemming sur chaque mot
    stemmed_text = " ".join([get_stem(word) for word in text.split()])
    stemmed_keyword = " ".join([get_stem(part) for part in keyword.split()])
    
    # Vérification stricte de la correspondance
    if stemmed_keyword in stemmed_text:
        return True
    
    # Si pas de correspondance stricte, vérifier la similarité des phrases (seuil de 80%)
    similarity = similar_phrases(stemmed_text, stemmed_keyword)
    return similarity > 0.8

# Ajout d'un User-Agent pour simuler un navigateur comme Google Chrome
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Fonction pour extraire et vérifier les balises, tout en excluant certaines zones comme le footer
def extract_and_check(url):
    try:
        response = requests.get(url, timeout=5, headers=headers)  # Ajout du User-Agent dans les requêtes
        
        # Vérifier si la page retourne une erreur 404
        if response.status_code == 404:
            return {
                'Balise Title': 'Erreur 404',
                'H1': 'Erreur 404',
                'Hn Structure': 'Erreur 404',
                'Redirection URL': 'N/A'
            }
        
        # Vérifier si une redirection 301 a eu lieu
        if len(response.history) > 0 and response.history[0].status_code == 301:
            return {
                'Balise Title': 'Redirection 301',
                'H1': 'Redirection 301',
                'Hn Structure': 'Redirection 301',
                'Redirection URL': 'Redirection 301'
            }

        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Exclure le footer et les éléments contenant "nav" dans leur classe CSS
        if soup.footer:
            soup.footer.decompose()  # Supprimer le footer
        for element in soup.find_all(class_=re.compile("nav")):
            element.decompose()  # Supprimer les éléments avec "nav" dans leur classe

        # Extraire et vérifier les balises
        title = soup.title.string if soup.title else ""
        
        h1 = soup.h1.get_text() if soup.h1 else ""
        
        hn_texts = []
        tags = soup.find_all(['h2', 'h3'])
        for t in tags:
            hn_text = f"<{t.name}>{t.get_text()}</{t.name}>"
            hn_texts.append(hn_text)
        
        hn_text = "\n".join(hn_texts)
        
        return {
            'Balise Title': title,
            'H1': h1,
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

# Fonction pour traiter les URLs en parallèle avec estimation du temps restant
def process_urls(df, keyword_column, url_column, progress_bar, time_estimation):
    url_results = {}
    total_urls = len(df)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=50) as executor:  # Augmenter à 50 threads pour accélérer le processus
        futures = {}
        for index, row in df.iterrows():
            url = row[url_column]
            if url not in url_results:
                futures[url] = executor.submit(extract_and_check, url)
        
        completed = 0
        update_interval = 100  # Mettre à jour la barre de progression toutes les 100 URLs
        for url, future in futures.items():
            url_results[url] = future.result()
            completed += 1
            
            if completed % update_interval == 0:
                # Mettre à jour la barre de progression et le temps estimé
                progress_bar.progress(completed / total_urls)
                
                elapsed_time = time.time() - start_time
                time_per_url = elapsed_time / completed
                estimated_total_time = time_per_url * total_urls
                time_left = estimated_total_time - elapsed_time
                time_estimation.text(f"Temps estimé restant : {int(time_left // 60)} min {int(time_left % 60)} sec")
    
    return url_results

# Fonction principale pour l'application Streamlit
def main():
    st.title("Vérification de mot-clé dans des pages web")

    # Chargement du fichier xlsx
    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.write("Aperçu du fichier :")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")
            return

        # Sélection des colonnes
        keyword_column = st.selectbox("Sélectionnez la colonne contenant les mots-clés", df.columns)
        url_column = st.selectbox("Sélectionnez la colonne contenant les URLs", df.columns)

        if st.button("Lancer le crawl"):
            # Initialisation de la barre de progression et de l'estimation du temps
            progress_bar = st.progress(0)
            time_estimation = st.empty()

            st.write("Initialisation des colonnes et démarrage du scraping en parallèle...")
            url_results = process_urls(df, keyword_column, url_column, progress_bar, time_estimation)
            
            # Ajouter les résultats dans le dataframe
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

            # Affichage du résultat
            st.write("Résultat du crawl :")
            st.dataframe(df)

            # Sauvegarde du fichier Excel
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

# Ajouter cette ligne pour que le script soit exécuté avec la fonction main()
if __name__ == "__main__":
    main()
