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

def group_keywords(data, position_cols, url_cols, num_top_competitors):
    grouped_keywords = defaultdict(list)
    
    for index, row in data.iterrows():
        competitors = []
        for pos_col, url_col in zip(position_cols, url_cols):
            if not pd.isna(row[pos_col]) and not pd.isna(row[url_col]):
                competitor_name = pos_col.replace("Position", "").strip()
                competitors.append((competitor_name, float(row[pos_col]), normalize_url(row[url_col])))
        
        if competitors:
            sorted_competitors = sorted(competitors, key=lambda x: x[1])[:num_top_competitors]
            group_key = tuple((comp[0], comp[2]) for comp in sorted_competitors)
            
            # Récupération du volume si la colonne existe, sinon 0
            volume_value = float(row["Volume"]) if "Volume" in data.columns and not pd.isna(row["Volume"]) else 0
            
            grouped_keywords[group_key].append({
                'mot_cle': row['Mot-clé'],
                'volume': volume_value,
                'positions': {comp[0]: comp[1] for comp in sorted_competitors}
            })
    
    final_groups = []
    for competitors_urls, keywords in grouped_keywords.items():
        # Choisir le mot-clé principal basé sur le volume le plus élevé
        main_entry = max(keywords, key=lambda x: x.get('volume', 0))
        primary_keyword = main_entry['mot_cle']
        primary_volume = main_entry['volume']
        total_volume = sum(kw.get('volume', 0) for kw in keywords)
        
        all_keywords = [kw['mot_cle'] for kw in keywords]
        competitors = [comp for comp, _ in competitors_urls]
        urls = [url for _, url in competitors_urls]
        positions = {comp: [kw['positions'].get(comp, '-') for kw in keywords] for comp in competitors}

        final_groups.append({
            'Mot-clé de référence': primary_keyword,
            'Mots-clés regroupés': ', '.join(all_keywords),
            'Volume du mot-clé principal': primary_volume,
            'Volume total': total_volume,
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

        num_top_competitors = st.slider("Nombre de meilleurs concurrents à considérer pour le groupement", 
                                        min_value=1, max_value=num_competitors, value=min(2, num_competitors))

        if st.button("Grouper les mots-clés"):
            url_cols = [col[0] for col in matched_cols]
            position_cols = [col[1] for col in matched_cols]
            final_groups = group_keywords(data, position_cols, url_cols, num_top_competitors)
            results_excel = create_output_file(final_groups)
            st.download_button(
                label="Télécharger les résultats en Excel",
                data=results_excel,
                file_name="grouped_keywords.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

if __name__ == "__main__":
    main()
