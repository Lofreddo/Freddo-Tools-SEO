import streamlit as st
import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse
import io

def load_data(file):
    data = pd.read_excel(file, sheet_name=0)
    data.columns = data.columns.str.strip()
    return data

def normalize_url(url):
    if pd.isna(url) or not isinstance(url, str):
        return None
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}"

def detect_url_position_columns(data):
    url_cols = [col for col in data.columns if col.endswith("URL")]
    position_cols = [col for col in data.columns if col.endswith("Position")]
    
    matched_cols = []
    for url_col in url_cols:
        base_name = url_col[:-3]  # Enlève "URL" de la fin
        matching_position_col = next((col for col in position_cols if col.startswith(base_name)), None)
        if matching_position_col:
            matched_cols.append((url_col, matching_position_col))
    
    return matched_cols

def group_keywords(data, position_cols, url_cols, num_competitors, min_similar_results):
    grouped_keywords = defaultdict(list)
    
    for index, row in data.iterrows():
        valid_competitors = []
        for pos_col, url_col in zip(position_cols, url_cols):
            if not pd.isna(row[pos_col]) and not pd.isna(row[url_col]):
                competitor_name = pos_col.replace("Position", "").strip()
                valid_competitors.append((competitor_name, float(row[pos_col]), normalize_url(row[url_col])))
        
        if len(valid_competitors) >= num_competitors:
            sorted_competitors = sorted(valid_competitors, key=lambda x: x[1])[:num_competitors]
            competitor_pair = tuple(sorted([comp[0] for comp in sorted_competitors]))
            urls_pair = tuple(sorted([comp[2] for comp in sorted_competitors]))
            
            group_key = (competitor_pair, urls_pair)
            grouped_keywords[group_key].append({
                'mot_cle': row['Mot-clé'],
                'positions': {comp[0]: comp[1] for comp in sorted_competitors}
            })
    
    final_groups = []
    for (competitors, urls), keywords in grouped_keywords.items():
        if len(keywords) >= min_similar_results:
            primary_keyword = keywords[0]['mot_cle']
            all_keywords = [kw['mot_cle'] for kw in keywords]
            positions = {comp: [kw['positions'][comp] for kw in keywords] for comp in competitors}

            final_groups.append({
                'Mot-clé de référence': primary_keyword,
                'Mots-clés regroupés': ', '.join(all_keywords),
                'Concurrents concernés': ', '.join(competitors),
                'URLs concernées': ', '.join(urls),
                'Positions des URLs concernées': ', '.join(
                    [f"{comp}: {positions[comp]}" for comp in competitors]
                )
            })
    
    return final_groups

def create_output_file(final_groups):
    df = pd.DataFrame(final_groups)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Grouped Keywords')
    return output.getvalue()

def main():
    st.title("Groupement de mots-clés")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel", type="xlsx")
    if uploaded_file is not None:
        data = load_data(uploaded_file)

        matched_cols = detect_url_position_columns(data)
        num_competitors = len(matched_cols)

        min_similar_results = st.slider("Nombre minimum de résultats similaires pour grouper", min_value=2, max_value=10, value=2)

        if st.button("Grouper les mots-clés"):
            if num_competitors < 2:
                st.error("Au moins 2 concurrents sont nécessaires pour le groupement.")
            else:
                url_cols = [col[0] for col in matched_cols]
                position_cols = [col[1] for col in matched_cols]
                final_groups = group_keywords(data, position_cols, url_cols, num_competitors, min_similar_results)
                results_excel = create_output_file(final_groups)
                st.download_button(
                    label="Télécharger les résultats en Excel",
                    data=results_excel,
                    file_name="grouped_keywords.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

if __name__ == "__main__":
    main()
