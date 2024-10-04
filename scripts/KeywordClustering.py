import streamlit as st
import pandas as pd
import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk
import os
from collections import defaultdict
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

def download_nltk_resources():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
    try:
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        nltk.download('omw-1.4')

def main():
    st.title("Catégorisation de mots-clés multilingue")

    # Télécharger les ressources NLTK nécessaires
    download_nltk_resources()

    # Initialiser le client OpenAI
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # Sélection de la langue
    language = st.selectbox("Sélectionnez la langue des mots-clés :", ["Français", "Italien", "Espagnol", "Anglais"])
    lang_code = {"Français": "fra", "Italien": "ita", "Espagnol": "spa", "Anglais": "eng"}[language]

    # Interface utilisateur Streamlit
    input_method = st.radio("Choisissez la méthode d'entrée :", ("Fichier (XLSX/CSV)", "Texte libre"))

    if input_method == "Fichier (XLSX/CSV)":
        uploaded_file = st.file_uploader("Choisissez un fichier XLSX ou CSV", type=["xlsx", "csv"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            st.write("Aperçu du fichier :")
            st.dataframe(df.head())
            
            column = st.selectbox("Sélectionnez la colonne contenant les mots-clés :", df.columns)
            keywords = df[column].tolist()
    else:
        keywords_text = st.text_area("Entrez les mots-clés (un par ligne) :")
        keywords = [kw.strip() for kw in keywords_text.split("\n") if kw.strip()]

    if st.button("Catégoriser"):
        with st.spinner("Catégorisation en cours..."):
            # Lemmatisation et catégorisation
            categorized_keywords = categorize_keywords(client, keywords, lang_code)
            
            # Créer le DataFrame de sortie
            if input_method == "Fichier (XLSX/CSV)":
                output_df = df.copy()
                output_df["Catégorie"] = [categorized_keywords[kw] for kw in keywords]
            else:
                output_df = pd.DataFrame({"Mot-clé": keywords, "Catégorie": [categorized_keywords[kw] for kw in keywords]})
            
            st.write("Résultats de la catégorisation :")
            st.dataframe(output_df)
            
            # Téléchargement du fichier de sortie
            output_file = "mots_cles_categorises.xlsx"
            output_df.to_excel(output_file, index=False)
            with open(output_file, "rb") as file:
                st.download_button(
                    label="Télécharger les résultats",
                    data=file,
                    file_name=output_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

@st.cache_data
def get_embedding(client, text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

def lemmatize_keywords(keywords, lang_code):
    lemmatizer = WordNetLemmatizer()
    lemmatized = {}
    for kw in keywords:
        try:
            tokens = word_tokenize(kw.lower(), language=lang_code)
        except LookupError:
            tokens = word_tokenize(kw.lower())
        
        try:
            lemmas = [lemmatizer.lemmatize(token, lang=lang_code) for token in tokens]
        except KeyError:
            lemmas = [lemmatizer.lemmatize(token) for token in tokens]
        
        main_word = lemmas[0]  # Prend le lemme du premier mot comme terme principal
        lemmatized[kw] = main_word
    return lemmatized

def categorize_keywords(client, keywords, lang_code):
    # Lemmatisation
    lemmatized = lemmatize_keywords(keywords, lang_code)
    
    # Regroupement initial par lemme
    groups = defaultdict(list)
    for kw, lemma in lemmatized.items():
        groups[lemma].append(kw)
    
    # Pour les groupes avec un seul mot-clé, utiliser l'embedding pour le regroupement final
    single_keywords = [group[0] for group in groups.values() if len(group) == 1]
    if single_keywords:
        embeddings = [get_embedding(client, kw) for kw in single_keywords]
        
        # Déterminer le nombre optimal de clusters
        max_clusters = min(len(single_keywords), 20)
        silhouette_scores = []
        
        for n_clusters in range(2, max_clusters + 1):
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, cluster_labels)
            silhouette_scores.append(score)
        
        optimal_clusters = silhouette_scores.index(max(silhouette_scores)) + 2
        
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Regrouper les mots-clés restants basés sur leur cluster
        for kw, label in zip(single_keywords, cluster_labels):
            groups[f"groupe_{label}"].append(kw)
    
    # Créer le dictionnaire final de catégorisation
    categorized = {}
    for category, kws in groups.items():
        for kw in kws:
            categorized[kw] = category
    
    return categorized

if __name__ == "__main__":
    main()
