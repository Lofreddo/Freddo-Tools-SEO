import streamlit as st
import pandas as pd
from collections import defaultdict
from urllib.parse import urlparse
import io

def load_data(file):
    data = pd.read_excel(file, sheet_name="Copie de Mots-clés")
    data.columns = data.columns.str.strip()
    return data

def normalize_url(url):
    if pd.isna(url) or not isinstance(url, str):
        return None
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}"

def group_keywords(data, position_cols, url_cols, num_competitors):
    grouped_keywords = defaultdict(list)
    
    for index, row in data.iterrows():
        valid_competitors = []
        for pos_col, url_col in zip(position_cols, url_cols):
            if not pd.isna(row[pos_col]) and not pd.isna(row[url_col]):
                competitor_name = pos_col
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

        st.write("Colonnes détectées :", data.columns.tolist())

        num_competitors = st.selectbox("Nombre de concurrents à étudier", options=range(1, 11))

        position_cols = []
        url_cols = []
        for i in range(1, 11):
            col1, col2 = st.columns(2)
            with col1:
                pos_col = st.selectbox(f"Concurrent {i}", options=[""] + data.columns.tolist(), key=f"pos_{i}")
            with col2:
                url_col = st.selectbox(f"URL {i}", options=[""] + data.columns.tolist(), key=f"url_{i}")
            if pos_col and url_col:
                position_cols.append(pos_col)
                url_cols.append(url_col)

        if st.button("Grouper les mots-clés"):
            if len(position_cols) < 2 or len(url_cols) < 2:
                st.error("Veuillez sélectionner au moins 2 concurrents et 2 URLs.")
            else:
                final_groups = group_keywords(data, position_cols, url_cols, num_competitors)
                results_excel = create_output_file(final_groups)
                st.download_button(
                    label="Télécharger les résultats en Excel",
                    data=results_excel,
                    file_name="grouped_keywords.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

if __name__ == "__main__":
    main()
