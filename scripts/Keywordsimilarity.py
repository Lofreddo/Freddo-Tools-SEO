import streamlit as st
import pandas as pd
from itertools import combinations

def main():
    st.title("Analyse de Similarité de Mots-Clés par URLs")

    # Chargement du fichier
    uploaded_file = st.file_uploader("Téléchargez votre fichier Excel", type=["xlsx"])
    
    if uploaded_file:
        data = pd.read_excel(uploaded_file)
        st.write("Aperçu des données :", data.head())

        # Sélection des colonnes
        keyword_col = st.selectbox("Sélectionnez la colonne des mots-clés", data.columns)
        url_col = st.selectbox("Sélectionnez la colonne des URLs", data.columns)
        rank_col = st.selectbox("Sélectionnez la colonne des positions", data.columns)

        # Sélection du nombre de résultats maximum
        max_results = st.selectbox("Nombre de résultats maximum analysés par mot-clé",
                                   [10, 20, 30, 40, 50, 100])

        # Seuil de similarité minimum
        similarity_threshold = st.selectbox("Pourcentage de similarité minimum",
                                            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100])

        if st.button("Lancer l'analyse"):
            # Filtrer les données par rang
            filtered_data = data[data[rank_col] <= max_results]

            # Calcul de similarité
            similarity_results = []
            keywords = filtered_data[keyword_col].unique()

            for kw1, kw2 in combinations(keywords, 2):
                urls_kw1 = set(filtered_data[filtered_data[keyword_col] == kw1][url_col])
                urls_kw2 = set(filtered_data[filtered_data[keyword_col] == kw2][url_col])

                # Calcul du pourcentage de similarité
                common_urls = urls_kw1.intersection(urls_kw2)
                similarity = (len(common_urls) / max_results) * 100

                if similarity >= similarity_threshold:
                    similarity_results.append([kw1, kw2, round(similarity, 2)])

            # Afficher et télécharger les résultats
            if similarity_results:
                results_df = pd.DataFrame(similarity_results, columns=["Mot-Clé 1", "Mot-Clé 2", "Pourcentage de Similarité"])
                st.write("Résultats de Similarité :", results_df)

                # Téléchargement du fichier Excel
                output_file = "similarity_results.xlsx"
                results_df.to_excel(output_file, index=False)
                with open(output_file, "rb") as file:
                    btn = st.download_button(
                        label="Télécharger les résultats en Excel",
                        data=file,
                        file_name=output_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.write("Aucune paire de mots-clés ne dépasse le seuil de similarité.")
