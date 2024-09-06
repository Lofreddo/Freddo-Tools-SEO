import streamlit as st
import pandas as pd
from io import BytesIO

def main():
    st.title("Analyse de mots-clés")

    # Étape 1: Charger les fichiers CSV ou XLSX
    uploaded_files = st.file_uploader("Importer les fichiers de données", accept_multiple_files=True, type=['csv', 'xlsx'])

    if uploaded_files:
        dataframes = []
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-16', sep='\t')
            else:
                df = pd.read_excel(uploaded_file)
            dataframes.append(df)

        if dataframes:
            st.write("Fichiers importés :")
            for i, df in enumerate(dataframes):
                st.write(f"Fichier {i + 1} :")
                st.write(df.head())

            # Étape 2: Sélectionner les colonnes appropriées
            column_names = dataframes[0].columns.tolist()

            keyword_column = st.selectbox("Sélectionner la colonne Mot-clé", column_names)
            volume_column = st.selectbox("Sélectionner la colonne Volume de recherche", column_names)
            position_column = st.selectbox("Sélectionner la colonne Position", column_names)
            url_column = st.selectbox("Sélectionner la colonne URL", column_names)

            # Étape 3: Paramètres de filtrage
            min_sites = st.number_input("Nombre minimum de sites positionnés sur le mot-clé", min_value=1, value=3)
            max_position = st.number_input("Position maximum pour le mot-clé", min_value=1, value=20)
            max_site_position = st.number_input("Position maximum pour le site le mieux positionné", min_value=1, value=10)

            # Étape 4: Analyse et création du fichier final
            if st.button("Lancer l'analyse"):
                result_df = pd.DataFrame()

                for df in dataframes:
                    # Filtrer les données par le nombre de sites positionnés et les positions
                    filtered_df = df[(df[position_column] <= max_position) & 
                                     (df.groupby(keyword_column)[position_column].transform('count') >= min_sites)]

                    grouped = filtered_df.groupby(keyword_column)
                    for keyword, group in grouped:
                        top_position = group[position_column].min()
                        if top_position <= max_site_position:
                            row = {
                                'Mot-clé': keyword,
                                'Volume': group[volume_column].max(),
                                'Nombre de sites positionnés': group[position_column].count()
                            }
                            # Ajouter la position et l'URL de chaque site
                            for i, (_, row_data) in enumerate(group.iterrows()):
                                row[f'Site {i+1} - Position'] = row_data[position_column]
                                row[f'Site {i+1} - URL'] = row_data[url_column]
                            result_df = result_df.append(row, ignore_index=True)

                # Créer un fichier Excel en mémoire
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    result_df.to_excel(writer, index=False)

                # Assurer le format correct pour le téléchargement
                output.seek(0)
                st.download_button(
                    label="Télécharger le fichier",
                    data=output,
                    file_name="resultat_analyse.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
