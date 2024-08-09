import streamlit as st
import pandas as pd
import re
import random
import unidecode
import time

def master_spin(text, replacements):
    def replace_condition(match):
        options = match.group(1).split("|")
        return random.choice(options)

    while re.search(r'\{([^{}]+)\}', text):
        text = re.sub(r'\{([^{}]+)\}', replace_condition, text)
    
    for key, value in replacements.items():
        value_str = '' if pd.isna(value) else str(value)
        text = text.replace(f"${key}", value_str)
        
    text = re.sub(' +', ' ', text)
    return text

def transform_text(text):
    if text is None or text == "":
        return ""
    if "'" in text:
        text = text.split("'")[1].strip()
    text = text.lower()
    text = text.replace(" ", "-")
    text = unidecode.unidecode(text)
    return text

def extract_h1_content(text):
    h1_content = re.findall(r'<h1>(.*?)</h1>', text)
    return ' '.join(h1_content)

def main():
    st.title("Générateur de Texte Dynamique")

    # Upload Excel file
    uploaded_excel_file = st.file_uploader("Importer le fichier Excel avec les variables ($key)", type=["xlsx"])

    # Upload TXT file
    uploaded_txt_file = st.file_uploader("Importer le fichier texte avec les options", type=["txt"])

    # Text input for URL prefix
    url_prefix = st.text_input("Définir le préfixe pour l'URL", "pompes-funebres")

    # Dropdown to select key for URL
    if uploaded_excel_file is not None:
        df = pd.read_excel(uploaded_excel_file)
        selected_key = st.selectbox("Sélectionner la clé à utiliser pour l'URL", df.columns)

        if st.button("Générer le fichier de sortie"):
            if uploaded_excel_file is not None and uploaded_txt_file is not None:
                # Read the text template
                master_spin_text = uploaded_txt_file.read().decode("utf-8")

                results = []
                for index, row in df.iterrows():
                    # Récupérer la valeur de la clé sélectionnée pour construire l'URL
                    url_component_value = row[selected_key]
                    if pd.isna(url_component_value) or url_component_value == "":
                        st.warning(f"La valeur de la clé sélectionnée pour la ligne {index + 1} est vide ou non valide. Ignorée.")
                        continue
                    
                    start_time = time.time()

                    replacements = {key: '' if pd.isna(value) else str(value) for key, value in row.items()}
                    
                    text = master_spin(master_spin_text, replacements)
                    url_component = transform_text(url_component_value)
                    h1_content = extract_h1_content(text)
                    end_time = time.time()
                    st.write(f"Texte généré pour {url_component_value} en {end_time - start_time} secondes.")
                    results.append([url_component_value, text, f"{url_prefix}-{url_component}", h1_content])

                output_df = pd.DataFrame(results, columns=[selected_key, "Texte", "URL", "H1_Content"])

                # Create download button
                st.success("Génération terminée !")
                st.download_button(
                    label="Télécharger le fichier de sortie",
                    data=output_df.to_excel(index=False, engine='openpyxl'),
                    file_name="textes-villes-pf.xlsx"
                )
            else:
                st.error("Veuillez importer les fichiers requis.")

if __name__ == "__main__":
    main()
