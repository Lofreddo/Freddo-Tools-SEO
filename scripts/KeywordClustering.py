import streamlit as st
import pandas as pd
import numpy as np
from openai import OpenAI
from sklearn.cluster import KMeans
import os

def main():
    st.title("Catégorisation de mots-clés")

    # Initialiser le client OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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

    n_clusters = st.slider("Nombre de catégories :", min_value=2, max_value=20, value=5)

    if st.button("Catégoriser"):
        with st.spinner("Catégorisation en cours..."):
            # Obtenir les embeddings et clusteriser
            clusters = cluster_keywords(client, keywords, n_clusters)
            
            # Créer le DataFrame de sortie
            if input_method == "Fichier (XLSX/CSV)":
                output_df = df.copy()
                output_df["Catégorie"] = clusters
            else:
                output_df = pd.DataFrame({"Mot-clé": keywords, "Catégorie": clusters})
            
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

def get_embedding(client, text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

def cluster_keywords(client, keywords, n_clusters):
    embeddings = [get_embedding(client, kw) for kw in keywords]
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    return kmeans.fit_predict(embeddings)

if __name__ == "__main__":
    main()
