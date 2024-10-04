import streamlit as st
import pandas as pd
from openai import OpenAI
from sklearn.cluster import KMeans
import numpy as np
from collections import defaultdict
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

def extract_main_keywords(keywords):
    frequency = defaultdict(int)
    common_words = ['de', 'd', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'homme', 'femme', 'enfant', 'garçon', 'fille']
    for keyword in keywords:
        words = keyword.lower().split()
        main_words = [word for word in words if word not in common_words]
        for word in main_words:
            if word.endswith('s') and not word.endswith('ss'):
                word = word[:-1]  # Mettre au singulier
            frequency[word] += 1
    return frequency

def define_categories(frequencies, min_occurrence=10):
    categories = [word for word, count in frequencies.items() if count >= min_occurrence]
    if not categories:
        categories = sorted(frequencies, key=frequencies.get, reverse=True)[:5]  # Prendre les 5 plus fréquents
    return categories

def categorize_keywords(keywords, categories):
    categorized = []
    for keyword in keywords:
        keyword_lower = keyword.lower()
        for category in categories:
            if category in keyword_lower:
                categorized.append((keyword, category))
                break
        else:
            categorized.append((keyword, "Non catégorisé"))
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
            # Extraire les mots principaux et leurs fréquences
            frequencies = extract_main_keywords(keywords)

            # Définir les catégories
            categories = define_categories(frequencies)

            # Catégoriser les mots-clés
            final_categories = categorize_keywords(keywords, categories)
            
            if input_method == "Fichier (XLSX/CSV)":
                output_df = df.copy()
                output_df["Catégorie"] = [category for _, category in final_categories]
            else:
                output_df = pd.DataFrame({"Mot-clé": keywords, "Catégorie": [category for _, category in final_categories]})
            
            st.write("Catégories définies :", categories)
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
