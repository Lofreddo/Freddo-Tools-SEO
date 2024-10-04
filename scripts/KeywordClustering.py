import streamlit as st
import pandas as pd
from openai import OpenAI
from sklearn.cluster import KMeans
import numpy as np

# Initialiser le client OpenAI
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.secrets["openai_api_key"])

client = get_openai_client()

@st.cache_data
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

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
    prompt = f"Génère un nom de catégorie court et descriptif pour ces mots-clés : {', '.join(keywords)}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def categorize_keywords(keywords):
    # Obtenir les embeddings
    embeddings = [get_embedding(kw) for kw in keywords]
    
    # Clustering
    n_clusters = max(1, min(len(keywords) // 10, 20))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Obtenir les mots-clés représentatifs
    representative_keywords = get_representative_keywords(keywords, cluster_labels)
    
    # Générer des noms de catégories
    category_names = {}
    for label, rep_keywords in representative_keywords.items():
        category_names[label] = generate_category_name(rep_keywords)
    
    # Créer le dictionnaire final de catégorisation
    categorized = {kw: category_names[label] for kw, label in zip(keywords, cluster_labels)}
    
    return categorized

def main():
    st.title("Catégorisation de mots-clés")

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
            # Catégorisation
            categorized_keywords = categorize_keywords(keywords)
            
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

if __name__ == "__main__":
    main()
