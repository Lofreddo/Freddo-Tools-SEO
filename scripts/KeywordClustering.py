import streamlit as st
import pandas as pd
from openai import OpenAI
from sklearn.cluster import KMeans
import numpy as np
import re

# Initialiser le client OpenAI
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.secrets["openai_api_key"])

client = get_openai_client()

@st.cache_data
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

def extract_main_keyword(keyword):
    common_words = ['de', 'd', 'du', 'des', 'le', 'la', 'les', 'un', 'une']
    words = keyword.lower().split()
    main_words = [word for word in words if word not in common_words]
    
    if main_words:
        main_keyword = main_words[0]
        if main_keyword.endswith('s') and not main_keyword.endswith('ss'):
            main_keyword = main_keyword[:-1]
        return main_keyword
    return keyword

def get_representative_keywords(keywords, cluster_labels, n=5):
    clusters = {}
    for keyword, label in zip(keywords, cluster_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(keyword)
    
    representative_keywords = {}
    for label, cluster_keywords in clusters.items():
        representative_keywords[label] = cluster_keywords[:n]
    
    return representative_keywords

def generate_category_name(keywords):
    main_keywords = [extract_main_keyword(kw) for kw in keywords]
    unique_main_keywords = list(set(main_keywords))
    
    if len(unique_main_keywords) == 1:
        return unique_main_keywords[0]
    
    prompt = f"""Génère une catégorie générique unique et courte (1 à 2 mots maximum) pour ces mots-clés. 
    La catégorie doit contenir le mot-clé principal le plus fréquent parmi : {', '.join(unique_main_keywords)}.
    Mots-clés : {', '.join(keywords)}
    Catégorie :"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.3
    )
    return response.choices[0].message.content.strip().lower()

def post_process_category(category):
    articles = ['le', 'la', 'les', 'un', 'une', 'des']
    for article in articles:
        if category.startswith(article + ' '):
            category = category[len(article)+1:]
    
    words = category.split()
    if len(words) > 2:
        category = ' '.join(words[:2])
    
    if category.endswith('s') and not category.endswith('ss'):
        category = category[:-1]
    
    return category.strip()

def categorize_keywords(keywords):
    embeddings = [get_embedding(kw) for kw in keywords]
    
    unique_keywords = list(set(keywords))
    n_clusters = len(unique_keywords)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    representative_keywords = get_representative_keywords(keywords, cluster_labels)
    
    category_names = {}
    for label, rep_keywords in representative_keywords.items():
        category = generate_category_name(rep_keywords)
        category_names[label] = post_process_category(category)
    
    categorized = {kw: category_names[label] for kw, label in zip(keywords, cluster_labels)}
    
    return categorized

def main():
    st.title("Catégorisation de mots-clés")

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
            categorized_keywords = categorize_keywords(keywords)
            
            if input_method == "Fichier (XLSX/CSV)":
                output_df = df.copy()
                output_df["Catégorie"] = [categorized_keywords[kw] for kw in keywords]
            else:
                output_df = pd.DataFrame({"Mot-clé": keywords, "Catégorie": [categorized_keywords[kw] for kw in keywords]})
            
            st.write("Résultats de la catégorisation :")
            st.dataframe(output_df)
            
            output_file = "mots_cles_categorises.xlsx"
            output_df.to_excel(output_file, index=False)
            with open(output_file, "rb") as file:
                st.download_button(
                    label="Télécharger les résultats",
                    data=file,
                    file_name=output_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
