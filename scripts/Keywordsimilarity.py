import streamlit as st
import pandas as pd
from itertools import combinations
import networkx as nx # Bibliothèque pour les graphes
from io import BytesIO # Pour l'export Excel en mémoire

def main():
    st.title("Analyse de Similarité et Groupement Complet (Cliques) de Mots-Clés") # Titre mis à jour

    # Chargement du fichier
    uploaded_file = st.file_uploader("Téléchargez votre fichier Excel", type=["xlsx"])

    if uploaded_file:
        try:
            data = pd.read_excel(uploaded_file)
            # Supprimer les lignes où les colonnes essentielles seraient vides dès le départ
            # Note: On fera une sélection plus tard, mais ça évite des erreurs si les colonnes existent déjà avec des nans
            # data.dropna(subset=[col for col in ['Mot-clé', 'URL', 'Position'] if col in data.columns], inplace=True) # Exemple, adapter si noms connus
            st.write("Aperçu des données :", data.head())
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier Excel : {e}")
            return

        if data.empty:
            st.warning("Le fichier Excel semble vide ou est devenu vide après suppression des lignes incomplètes.")
            return

        available_columns = list(data.columns)
        if not available_columns:
             st.warning("Le fichier Excel ne contient aucune colonne.")
             return

        # Sélection des colonnes
        keyword_col = st.selectbox("Sélectionnez la colonne des mots-clés", available_columns, key="kw_col")
        url_col = st.selectbox("Sélectionnez la colonne des URLs", available_columns, key="url_col")
        rank_col = st.selectbox("Sélectionnez la colonne des positions", available_columns, key="rank_col")

        # Vérifier que les colonnes sélectionnées existent bien
        if not all(col in data.columns for col in [keyword_col, url_col, rank_col]):
             st.error("Une ou plusieurs colonnes sélectionnées ne sont pas valides. Rechargez la page si besoin.")
             return

        # --- Options d'analyse ---
        col1, col2 = st.columns(2)

        with col1:
            max_results_options = [10, 20, 30, 40, 50, 100]
            default_max_results = max_results_options[0]
            max_results = st.selectbox("Nombre de résultats max analysés par mot-clé",
                                    max_results_options, index=max_results_options.index(default_max_results), key="max_res")

        with col2:
            similarity_options = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            default_similarity = 50
            if default_similarity not in similarity_options: default_similarity = similarity_options[0]
            similarity_threshold = st.selectbox("Similarité minimum requise (%)",
                                                similarity_options, index=similarity_options.index(default_similarity), key="sim_thresh")

        # Option pour la taille minimale des groupes (cliques) à afficher
        min_group_size = st.selectbox("Taille minimum des groupes à afficher",
                                      options=[2, 3, 4, 5], index=0, key="min_group",
                                      help="Seuls les groupes contenant au moins ce nombre de mots-clés (tous similaires entre eux) seront affichés.")


        if st.button(f"Trouver les Groupes (Taille >= {min_group_size})"):
            with st.spinner("Analyse en cours... Filtrage, calcul des similarités et recherche des groupes..."):
                try:
                    # --- Préparation et Filtrage des Données ---
                    # S'assurer que la colonne de rang est numérique
                    if not pd.api.types.is_numeric_dtype(data[rank_col]):
                        try:
                            data[rank_col] = pd.to_numeric(data[rank_col], errors='coerce')
                            initial_rows = len(data)
                            data.dropna(subset=[rank_col], inplace=True)
                            if len(data) < initial_rows:
                                st.info(f"{initial_rows - len(data)} lignes supprimées car la colonne '{rank_col}' n'était pas numérique.")
                            data[rank_col] = data[rank_col].astype(int)
                        except Exception as conv_e:
                            st.error(f"Impossible de convertir la colonne '{rank_col}' en numérique : {conv_e}")
                            return

                    # Filtrer par rang et supprimer les lignes avec des NaN dans les colonnes clés après filtrage
                    filtered_data = data[data[rank_col] <= max_results].copy()
                    filtered_data.dropna(subset=[keyword_col, url_col], inplace=True)

                    # Assurer le type string pour éviter les problèmes de type mixte
                    filtered_data[keyword_col] = filtered_data[keyword_col].astype(str).str.strip()
                    filtered_data[url_col] = filtered_data[url_col].astype(str).str.strip()

                    keywords = filtered_data[keyword_col].unique()
                    keywords = [kw for kw in keywords if kw] # Exclure les mots-clés vides si présents

                    if len(keywords) < min_group_size:
                        st.warning(f"Moins de {min_group_size} mots-clés uniques trouvés après filtrage ({len(keywords)}). Impossible de former des groupes de cette taille.")
                        return

                    # --- Calcul des Similarités et Construction du Graphe ---
                    G = nx.Graph()
                    G.add_nodes_from(keywords)

                    total_combinations = len(list(combinations(keywords, 2)))
                    st.write(f"Calcul des similarités pour {total_combinations} paires de mots-clés (parmi {len(keywords)} uniques)...")

                    # Optimisation: Pré-calculer les sets d'URLs par mot-clé
                    urls_per_keyword = {}
                    for keyword in keywords:
                        urls_per_keyword[keyword] = set(filtered_data.loc[filtered_data[keyword_col] == keyword, url_col])

                    # Barre de progression
                    progress_bar = st.progress(0)
                    processed_count = 0

                    for kw1, kw2 in combinations(keywords, 2):
                        urls_kw1 = urls_per_keyword[kw1]
                        urls_kw2 = urls_per_keyword[kw2]

                        common_urls = urls_kw1.intersection(urls_kw2)
                        if max_results > 0:
                            similarity = (len(common_urls) / max_results) * 100
                        else:
                            similarity = 0

                        if similarity >= similarity_threshold:
                            G.add_edge(kw1, kw2, weight=round(similarity, 2))

                        processed_count += 1
                        if total_combinations > 0:
                             progress_bar.progress(processed_count / total_combinations)

                    progress_bar.empty() # Cache la barre une fois terminé

                    # --- Recherche des Cliques (Groupes Entièrement Connectés) ---
                    st.write("Recherche des groupes où tous les membres sont similaires entre eux...")
                    # nx.find_cliques retourne un générateur de listes (chaque liste est une clique)
                    all_cliques = list(nx.find_cliques(G))

                    # Filtrer les cliques par taille minimale
                    meaningful_cliques = [clique for clique in all_cliques if len(clique) >= min_group_size]

                    # --- Affichage et Export des Résultats ---
                    st.subheader(f"Groupes Trouvés (Cliques de Taille >= {min_group_size})")

                    if meaningful_cliques:
                        # Trier les cliques pour un affichage cohérent (par taille décroissante, puis alphabétiquement)
                        sorted_cliques = sorted(meaningful_cliques, key=lambda c: (-len(c), sorted(c)))

                        output_data = []
                        group_id_counter = 1
                        for clique in sorted_cliques:
                            # Trier les mots-clés au sein de la clique
                            sorted_keywords_in_clique = sorted(list(clique))
                            for keyword in sorted_keywords_in_clique:
                                output_data.append({"Groupe ID": group_id_counter, "Mot-Clé": keyword, "Taille Groupe": len(clique)})
                            group_id_counter += 1

                        results_df = pd.DataFrame(output_data)

                        # Affichage résumé dans Streamlit
                        st.write(f"Nombre total de groupes (cliques) trouvés : {len(sorted_cliques)}")
                        for i, clique in enumerate(sorted_cliques):
                             display_group = ", ".join(sorted(list(clique)))
                             st.write(f"**Groupe {i+1} (Taille {len(clique)}):** {display_group}")

                        st.write("---")
                        st.write("Tableau Détaillé des Groupes (pour export) :")
                        st.dataframe(results_df)

                        # Export Excel
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            results_df.to_excel(writer, index=False, sheet_name=f'Cliques_Taille>={min_group_size}')
                            # Ajouter une feuille d'info (optionnel)
                            info_df = pd.DataFrame({
                                'Paramètre': ['Colonne Mots-clés', 'Colonne URLs', 'Colonne Positions', 'Max Résultats Analysés', 'Seuil Similarité (%)', 'Taille Minimum Groupe'],
                                'Valeur': [keyword_col, url_col, rank_col, max_results, similarity_threshold, min_group_size]
                            })
                            info_df.to_excel(writer, index=False, sheet_name='Parametres_Analyse')

                        excel_data = output.getvalue()

                        st.download_button(
                            label=f"Télécharger les Groupes (Cliques) en Excel",
                            data=excel_data,
                            file_name=f"keyword_cliques_sim{similarity_threshold}pct_top{max_results}_min{min_group_size}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.write(f"Aucun groupe (clique) de taille >= {min_group_size} où tous les mots-clés sont mutuellement similaires n'a été trouvé avec un seuil de {similarity_threshold}%.")
                        st.info("Essayez peut-être avec un seuil de similarité plus bas ou une taille de groupe minimum plus petite.")

                except Exception as analysis_e:
                     st.error(f"Une erreur est survenue pendant l'analyse : {analysis_e}")
                     import traceback
                     st.error(traceback.format_exc()) # Plus de détails pour le débogage

# Point d'entrée du script
if __name__ == "__main__":
    try:
        import networkx
    except ImportError:
        st.error("La bibliothèque 'networkx' est requise. Veuillez l'installer : pip install networkx")
        st.stop()

    main()
