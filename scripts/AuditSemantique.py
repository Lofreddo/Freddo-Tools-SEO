import streamlit as st
import pandas as pd
from io import BytesIO

def main():
    st.title("Analyse de mots-clés")

    uploaded_files = st.file_uploader("Importer les fichiers de données", accept_multiple_files=True, type=['csv', 'xlsx'])

    if uploaded_files:
        dataframes = {}
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='utf-16', sep='\t')
                else:
                    df = pd.read_excel(uploaded_file)
                dataframes[uploaded_file.name] = df
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier {uploaded_file.name}: {e}")
                return

        if dataframes:
            st.write("Fichiers importés :")
            for name, df_head in dataframes.items():
                st.write(f"Fichier : {name} (premières lignes)")
                st.write(df_head.head())

            if not dataframes:
                st.warning("Aucun fichier n'a pu être chargé correctement.")
                return

            # Utiliser les colonnes du premier dataframe comme référence
            try:
                reference_df_columns = list(dataframes.values())[0].columns.tolist()
            except IndexError:
                st.error("Aucun fichier n'a été chargé ou les fichiers sont vides.")
                return


            keyword_column = st.selectbox("Sélectionner la colonne Mot-clé", reference_df_columns, key="kw_col")
            volume_column = st.selectbox("Sélectionner la colonne Volume de recherche", reference_df_columns, key="vol_col")
            position_column = st.selectbox("Sélectionner la colonne Position", reference_df_columns, key="pos_col")
            url_column = st.selectbox("Sélectionner la colonne URL", reference_df_columns, key="url_col")

            st.subheader("Paramètres de filtrage avancés")
            max_site_pos_threshold = st.number_input("Position maximum pour qu'un site soit considéré 'bien positionné' (ex: 10)", min_value=1, value=10, key="max_site_pos_thresh")
            min_total_sites_with_keyword = st.number_input("Nombre total minimum de sites devant avoir le mot-clé (ex: 3)", min_value=1, value=3, key="min_total_sites")
            min_sites_in_top_pos = st.number_input(f"Parmi ces sites, nombre minimum devant être 'bien positionnés' (position <= {max_site_pos_threshold}) (ex: 2)", min_value=0, value=2, key="min_sites_top")

            if min_sites_in_top_pos > min_total_sites_with_keyword:
                st.warning("'Nombre minimum de sites bien positionnés' ne peut pas être supérieur au 'Nombre total minimum de sites'. Ajustez les valeurs.")
                # On pourrait bloquer le bouton "Lancer l'analyse" ici ou juste laisser l'utilisateur corriger.

            if st.button("Lancer l'analyse"):
                result_rows = []
                # Dictionnaire pour stocker les informations agrégées par mot-clé
                # keyword_info[keyword] = {
                # 'Volume': 0,
                # 'total_sites_having_keyword': 0,
                # 'sites_in_top_position_count': 0,
                # 'Site_Data': { site_name: {'Position': pos, 'URL': url, 'Volume_Site': vol}, ... }
                # }
                keyword_info = {}

                for site_name, df_original in dataframes.items():
                    st.write(f"Analyse du fichier {site_name}...")
                    df = df_original.copy()

                    required_cols = [keyword_column, volume_column, position_column, url_column]
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    if missing_cols:
                        st.error(f"Colonnes manquantes dans '{site_name}': {', '.join(missing_cols)}. Ce fichier sera ignoré pour l'analyse.")
                        continue

                    try:
                        df[keyword_column] = df[keyword_column].astype(str).str.strip() # Nettoyer aussi les espaces
                        df[url_column] = df[url_column].astype(str)
                        df[position_column] = pd.to_numeric(df[position_column], errors='coerce')
                        df[volume_column] = pd.to_numeric(df[volume_column], errors='coerce')
                        
                        df.dropna(subset=[keyword_column, position_column], inplace=True) # Besoin d'un mot-clé et d'une position valides
                        if not df.empty:
                            df[position_column] = df[position_column].astype(int)
                        else:
                            st.info(f"Le fichier {site_name} est vide après nettoyage initial des données (conversion de types, suppression des NaN sur mot-clé/position).")
                            continue
                    except Exception as e:
                        st.error(f"Erreur lors de la conversion des types de données pour le fichier {site_name}: {e}. Ce fichier sera ignoré.")
                        continue
                    
                    if df.empty:
                        st.info(f"Aucune donnée valide à analyser pour le fichier {site_name} après conversion.")
                        continue
                    
                    # Grouper par mot-clé pour ce site, pour trouver la meilleure position du site pour chaque mot-clé
                    grouped_by_keyword_for_site = df.groupby(keyword_column)

                    for keyword_value, group_for_keyword in grouped_by_keyword_for_site:
                        if not keyword_value: # Ignorer les mots-clés vides après conversion
                            continue

                        best_row_for_site_keyword = group_for_keyword.loc[group_for_keyword[position_column].idxmin()]
                        
                        site_pos_for_kw = best_row_for_site_keyword[position_column]
                        site_url_for_kw = best_row_for_site_keyword[url_column]
                        site_vol_for_kw = best_row_for_site_keyword[volume_column] if pd.notna(best_row_for_site_keyword[volume_column]) else 0

                        # Initialiser/mettre à jour les informations pour ce mot-clé
                        if keyword_value not in keyword_info:
                            keyword_info[keyword_value] = {
                                'Volume': 0, # Sera le max des volumes de tous les sites ayant le mot-clé
                                'total_sites_having_keyword': 0,
                                'sites_in_top_position_count': 0,
                                'Site_Data': {} # Stockera {site_name: {Position, URL, Volume_Site}}
                            }
                        
                        # Mettre à jour le volume global du mot-clé avec le max rencontré
                        keyword_info[keyword_value]['Volume'] = max(keyword_info[keyword_value]['Volume'], site_vol_for_kw)
                        
                        # Ce site a ce mot-clé
                        keyword_info[keyword_value]['total_sites_having_keyword'] += 1
                        
                        # Stocker les données de ce site pour ce mot-clé
                        keyword_info[keyword_value]['Site_Data'][site_name] = {
                            'Position': site_pos_for_kw,
                            'URL': site_url_for_kw,
                            'Volume_Site': site_vol_for_kw # Peut être utile pour des analyses futures
                        }
                        
                        # Vérifier si ce site est "bien positionné" pour ce mot-clé
                        if site_pos_for_kw <= max_site_pos_threshold:
                            keyword_info[keyword_value]['sites_in_top_position_count'] += 1

                # Étape finale: Filtrer les mots-clés et construire le DataFrame de résultats
                for keyword, info in keyword_info.items():
                    passes_min_total_sites = info['total_sites_having_keyword'] >= min_total_sites_with_keyword
                    passes_min_sites_in_top = info['sites_in_top_position_count'] >= min_sites_in_top_pos
                    
                    if passes_min_total_sites and passes_min_sites_in_top:
                        row = {
                            'Mot-clé': keyword,
                            'Volume Global Max': info['Volume'], # Volume max trouvé pour ce mot-clé
                            'Nb total sites avec M-C': info['total_sites_having_keyword'],
                            f'Nb sites position ≤ {max_site_pos_threshold}': info['sites_in_top_position_count']
                        }
                        
                        # Ajouter les colonnes Position et URL pour chaque site source
                        for site_name_key in dataframes.keys(): # Pour assurer un ordre cohérent des colonnes de site
                            if site_name_key in info['Site_Data']:
                                site_specific_data = info['Site_Data'][site_name_key]
                                row[f'{site_name_key} - Position'] = site_specific_data['Position']
                                row[f'{site_name_key} - URL'] = site_specific_data['URL']
                            else:
                                # Ce site n'avait pas le mot-clé, ou a été filtré avant
                                row[f'{site_name_key} - Position'] = None 
                                row[f'{site_name_key} - URL'] = None
                        result_rows.append(row)

                if result_rows:
                    result_df = pd.DataFrame(result_rows)
                    
                    # Organiser les colonnes
                    main_cols = ['Mot-clé', 'Volume Global Max', 'Nb total sites avec M-C', f'Nb sites position ≤ {max_site_pos_threshold}']
                    site_detail_cols_sorted = []
                    for site_name_key in sorted(dataframes.keys()): # Tri par nom de fichier/site pour la cohérence
                        if f'{site_name_key} - Position' in result_df.columns : # Vérifier si la colonne existe (au cas où un site n'aurait aucun mot-clé retenu)
                             site_detail_cols_sorted.append(f'{site_name_key} - Position')
                        if f'{site_name_key} - URL' in result_df.columns :
                             site_detail_cols_sorted.append(f'{site_name_key} - URL')
                    
                    # S'assurer que seules les colonnes existantes sont demandées
                    final_columns_order = main_cols + [col for col in site_detail_cols_sorted if col in result_df.columns]
                    result_df = result_df[final_columns_order]

                    # Trier les résultats
                    result_df.sort_values(by=[f'Nb sites position ≤ {max_site_pos_threshold}', 'Nb total sites avec M-C', 'Volume Global Max'], 
                                          ascending=[False, False, False], 
                                          inplace=True,
                                          na_position='last')

                    st.write("Résultats de l'analyse :")
                    st.dataframe(result_df)

                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Analyse Mots-clés')
                    output.seek(0)
                    st.download_button(
                        label="Télécharger le fichier Excel",
                        data=output,
                        file_name="resultat_analyse_mots_cles_avances.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.write("Aucun mot-clé ne correspond à tous vos critères de filtrage. Essayez d'assouplir les filtres.")

if __name__ == '__main__':
    main()
