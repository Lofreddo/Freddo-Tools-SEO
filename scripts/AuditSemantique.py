import streamlit as st
import pandas as pd
from io import BytesIO

def main():
    st.title("Analyse de mots-clés")

    # Étape 1: Charger les fichiers CSV ou XLSX
    uploaded_files = st.file_uploader("Importer les fichiers de données", accept_multiple_files=True, type=['csv', 'xlsx'])

    if uploaded_files:
        dataframes = {}
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-16', sep='\t')
            else:
                df = pd.read_excel(uploaded_file)
            # Utiliser le nom de fichier comme clé pour identifier chaque fichier/site
            dataframes[uploaded_file.name] = df

        if dataframes:
            st.write("Fichiers importés :")
            for name, df in dataframes.items():
                st.write(f"Fichier : {name}")
                st.write(df.head())

            # Étape 2: Sélectionner les colonnes appropriées pour tous les fichiers
            column_names = list(dataframes.values())[0].columns.tolist()

            keyword_column = st.selectbox("Sélectionner la colonne Mot-clé", column_names)
            volume_column = st.selectbox("Sélectionner la colonne Volume de recherche", column_names)
            position_column = st.selectbox("Sélectionner la colonne Position", column_names)
            url_column = st.selectbox("Sélectionner la colonne URL", column_names)

            # Étape 3: Paramètres de filtrage
            min_sites = st.number_input("Nombre minimum de sites positionnés sur le mot-clé", min_value=1, value=2)
            max_position = st.number_input("Position maximum pour le mot-clé", min_value=1, value=20)
            max_site_position = st.number_input("Position maximum pour le site le mieux positionné", min_value=1, value=10)

            # Étape 4: Analyse et création du fichier final
            if st.button("Lancer l'analyse"):
                result_rows = []  # Liste pour stocker les résultats finaux

                # Dictionnaire pour stocker les informations par mot-clé
                keyword_info = {}

                # Analyser chaque fichier/site
                for site_name, df in dataframes.items():
                    st.write(f"Analyse du fichier {site_name} avec {len(df)} lignes.")

                    # Filtrer les mots-clés par la position maximum
                    filtered_df = df[df[position_column] <= max_position]

                    # Grouper par mot-clé
                    grouped = filtered_df.groupby(keyword_column)

                    for keyword, group in grouped:
                        top_position = group[position_column].min()

                        # Vérifier si le site le mieux positionné est dans la limite
                        if top_position <= max_site_position:
                            if keyword not in keyword_info:
                                keyword_info[keyword] = {
                                    'Volume': group[volume_column].max(),  # Prendre le volume maximum
                                    'Nombre de sites positionnés': 0,
                                    'Sites': {}
                                }

                            # Ajouter ce site au comptage
                            keyword_info[keyword]['Nombre de sites positionnés'] += 1

                            # Ajouter la position et l'URL de ce site
                            for _, row_data in group.iterrows():
                                keyword_info[keyword]['Sites'][site_name] = {
                                    'Position': row_data[position_column],
                                    'URL': row_data[url_column]
                                }

                # Étape 5: Créer les lignes du DataFrame final
                for keyword, info in keyword_info.items():
                    # Ne garder que les mots-clés avec suffisamment de sites positionnés
                    if info['Nombre de sites positionnés'] >= min_sites:
                        row = {
                            'Mot-clé': keyword,
                            'Volume': info['Volume'],
                            'Nombre de sites positionnés': info['Nombre de sites positionnés']
                        }

                        # Ajouter la position et l'URL de chaque site
                        for site_name, site_info in info['Sites'].items():
                            row[f'{site_name} - Position'] = site_info['Position']
                            row[f'{site_name} - URL'] = site_info['URL']

                        result_rows.append(row)

                # Créer le DataFrame final
                result_df = pd.DataFrame(result_rows)

                # Afficher le résultat avant génération du fichier
                if not result_df.empty:
                    st.write("Résultats de l'analyse :")
                    st.write(result_df.head())
                else:
                    st.write("Aucun résultat trouvé. Vérifiez les filtres.")

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
