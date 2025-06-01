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
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='utf-16', sep='\t')
                else:
                    df = pd.read_excel(uploaded_file)
                # Utiliser le nom de fichier comme clé pour identifier chaque fichier/site
                dataframes[uploaded_file.name] = df
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier {uploaded_file.name}: {e}")
                return # Arrêter si un fichier ne peut être lu

        if dataframes:
            st.write("Fichiers importés :")
            for name, df_head in dataframes.items(): # Renommé df à df_head pour éviter confusion
                st.write(f"Fichier : {name} (premières lignes)")
                st.write(df_head.head())

            # Étape 2: Sélectionner les colonnes appropriées pour tous les fichiers
            # Utiliser les colonnes du premier dataframe comme référence
            # Il serait préférable de vérifier que toutes les colonnes existent dans tous les dataframes
            # ou de permettre une sélection par fichier si les colonnes diffèrent.
            # Pour l'instant, on suppose une structure de colonnes similaire.
            if not dataframes: # Vérification supplémentaire si dataframes est vide après une erreur de lecture
                st.warning("Aucun fichier n'a pu être chargé correctement.")
                return

            reference_df_columns = list(dataframes.values())[0].columns.tolist()

            keyword_column = st.selectbox("Sélectionner la colonne Mot-clé", reference_df_columns)
            volume_column = st.selectbox("Sélectionner la colonne Volume de recherche", reference_df_columns)
            position_column = st.selectbox("Sélectionner la colonne Position", reference_df_columns)
            url_column = st.selectbox("Sélectionner la colonne URL", reference_df_columns)

            # Étape 3: Paramètres de filtrage
            min_sites = st.number_input("Nombre minimum de sites positionnés sur le mot-clé", min_value=1, value=2)
            max_position = st.number_input("Position maximum pour le mot-clé (pour être considéré)", min_value=1, value=20)
            max_site_position = st.number_input("Position maximum pour le site le mieux positionné (pour que le mot-clé soit retenu pour ce site)", min_value=1, value=10)

            # Étape 4: Analyse et création du fichier final
            if st.button("Lancer l'analyse"):
                result_rows = []  # Liste pour stocker les résultats finaux
                keyword_info = {} # Dictionnaire pour stocker les informations par mot-clé

                # Analyser chaque fichier/site
                for site_name, df_original in dataframes.items():
                    st.write(f"Analyse du fichier {site_name} avec {len(df_original)} lignes.")
                    
                    df = df_original.copy() # Travailler sur une copie

                    # Vérifier que les colonnes sélectionnées existent
                    required_columns = [keyword_column, volume_column, position_column, url_column]
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        st.error(f"Les colonnes suivantes sont manquantes dans le fichier '{site_name}': {', '.join(missing_columns)}. Veuillez vérifier la sélection des colonnes ou le fichier.")
                        continue # Passer au fichier suivant

                    # --- DÉBUT DES MODIFICATIONS DE TYPE ---
                    try:
                        # S'assurer que la colonne Mot-clé est de type string
                        df[keyword_column] = df[keyword_column].astype(str)
                        
                        # S'assurer que la colonne URL est de type string
                        df[url_column] = df[url_column].astype(str)

                        # Convertir la colonne Position en numérique, les erreurs deviennent NaN
                        df[position_column] = pd.to_numeric(df[position_column], errors='coerce')
                        
                        # Convertir la colonne Volume en numérique, les erreurs deviennent NaN
                        df[volume_column] = pd.to_numeric(df[volume_column], errors='coerce')
                        df[volume_column] = df[volume_column].fillna(0) # Remplacer les NaN du volume par 0

                        # Supprimer les lignes où la position est NaN (après conversion)
                        df.dropna(subset=[keyword_column, position_column], inplace=True) # Aussi sur keyword_column au cas où il y aurait des NaN avant astype(str)

                        # Convertir la colonne position en entier après suppression des NaN
                        # et s'il reste des lignes
                        if not df.empty:
                             df[position_column] = df[position_column].astype(int)
                        else:
                            st.warning(f"Le fichier {site_name} est vide après le nettoyage initial des données (conversion de types, suppression des NaN sur position).")
                            continue


                    except Exception as e:
                        st.error(f"Erreur lors de la conversion des types de données pour le fichier {site_name}: {e}")
                        continue # Passer au fichier suivant
                    # --- FIN DES MODIFICATIONS DE TYPE ---

                    if df.empty:
                        st.info(f"Aucune donnée à analyser pour le fichier {site_name} après conversion et filtrage initial.")
                        continue

                    # Filtrer les mots-clés par la position maximum globale
                    filtered_df = df[df[position_column] <= max_position].copy() # .copy() pour éviter SettingWithCopyWarning

                    if filtered_df.empty:
                        st.info(f"Aucun mot-clé ne correspond au critère 'Position maximum <= {max_position}' dans {site_name}.")
                        continue
                    
                    # Grouper par mot-clé (maintenant de type string)
                    grouped = filtered_df.groupby(keyword_column)

                    for keyword, group in grouped:
                        # Pour ce mot-clé et ce site, trouver la meilleure position
                        # Le groupe 'group' contient toutes les lignes pour 'keyword' DANS CE FICHIER 'site_name'
                        # qui respectent déjà max_position.
                        best_row_in_group_for_site = group.loc[group[position_column].idxmin()]
                        top_position_for_site = best_row_in_group_for_site[position_column]
                        
                        # Vérifier si la meilleure position de CE SITE pour CE MOT-CLÉ est dans la limite max_site_position
                        if top_position_for_site <= max_site_position:
                            if keyword not in keyword_info:
                                keyword_info[keyword] = {
                                    'Volume': 0, # Sera mis à jour avec le max des volumes des sites concernés
                                    'Nombre de sites positionnés': 0,
                                    'Sites': {}
                                }
                            
                            # Mettre à jour le volume avec le maximum rencontré pour ce mot-clé parmi les sites pertinents
                            current_keyword_volume = best_row_in_group_for_site[volume_column]
                            if pd.notna(current_keyword_volume): # S'assurer que le volume n'est pas NaN
                                keyword_info[keyword]['Volume'] = max(keyword_info[keyword]['Volume'], current_keyword_volume)
                            
                            keyword_info[keyword]['Nombre de sites positionnés'] += 1
                            
                            keyword_info[keyword]['Sites'][site_name] = {
                                'Position': top_position_for_site,
                                'URL': best_row_in_group_for_site[url_column]
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

                        # Ajouter la position et l'URL de chaque site qui était positionné pour ce mot-clé
                        for site_name_key in dataframes.keys(): # Itérer sur tous les noms de sites possibles
                            if site_name_key in info['Sites']:
                                site_data = info['Sites'][site_name_key]
                                row[f'{site_name_key} - Position'] = site_data['Position']
                                row[f'{site_name_key} - URL'] = site_data['URL']
                            else:
                                # Si le site n'est pas dans info['Sites'] pour ce mot-clé,
                                # c'est qu'il ne répondait pas aux critères ou n'avait pas ce mot-clé.
                                # On peut mettre des valeurs vides ou NaN.
                                row[f'{site_name_key} - Position'] = None # ou pd.NA ou ""
                                row[f'{site_name_key} - URL'] = None     # ou pd.NA ou ""


                        result_rows.append(row)

                # Créer le DataFrame final
                if result_rows:
                    result_df = pd.DataFrame(result_rows)
                    
                    # S'assurer que les colonnes de site sont dans un ordre cohérent (alphabétique par nom de site)
                    # et après les colonnes principales.
                    main_cols = ['Mot-clé', 'Volume', 'Nombre de sites positionnés']
                    site_cols_sorted = []
                    for site_name_key in sorted(dataframes.keys()):
                        site_cols_sorted.append(f'{site_name_key} - Position')
                        site_cols_sorted.append(f'{site_name_key} - URL')
                    
                    final_columns_order = main_cols + site_cols_sorted
                    # S'assurer que toutes les colonnes existent dans result_df avant de réordonner
                    final_columns_order = [col for col in final_columns_order if col in result_df.columns]

                    result_df = result_df[final_columns_order]

                    # Trier par 'Nombre de sites positionnés' (décroissant) puis par 'Volume' (décroissant)
                    result_df.sort_values(by=['Nombre de sites positionnés', 'Volume'], ascending=[False, False], inplace=True)

                    st.write("Résultats de l'analyse :")
                    st.dataframe(result_df) # Utiliser st.dataframe pour une meilleure interactivité

                    # Créer un fichier Excel en mémoire
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Analyse Mots-clés')
                    
                    output.seek(0)
                    st.download_button(
                        label="Télécharger le fichier Excel",
                        data=output,
                        file_name="resultat_analyse_mots_cles.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.write("Aucun résultat trouvé correspondant à tous les critères. Vérifiez les filtres et les données d'entrée.")

# Assurez-vous que votre script Streamlit appelle cette fonction main
if __name__ == '__main__':
    main()
