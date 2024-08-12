import streamlit as st
import pandas as pd
import re
import random
import unidecode
import time
from io import BytesIO

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

    # Option to upload a TXT file or enter text manually
    text_input_option = st.radio("Choisir la méthode pour fournir le texte maître", ("Télécharger un fichier TXT", "Entrer le texte manuellement"))

    master_spin_text = ""
    
    if text_input_option == "Télécharger un fichier TXT":
        uploaded_txt_file = st.file_uploader("Importer le fichier texte avec les options", type=["txt"])
        if uploaded_txt_file is not None:
            master_spin_text = uploaded_txt_file.read().decode("utf-8")
    else:
        master_spin_text = st.text_area("Entrer le texte maître ici", height=300)

    # Text input for URL prefix
    url_prefix = st.text_input("Définir le préfixe pour l'URL", "pompes-funebres")

    # Dropdown to select 1 to 5 keys for URL
    if uploaded_excel_file is not None:
        df = pd.read_excel(uploaded_excel_file)
        selected_keys = st.multiselect("Sélectionner 1 à 5 clés à utiliser pour l'URL", df.columns, max_selections=5)

        if st.button("Générer le fichier de sortie"):
            if uploaded_excel_file is not None and (text_input_option == "Télécharger un fichier TXT" and master_spin_text.strip() != "") or (text_input_option == "Entrer le texte manuellement" and master_spin_text.strip() != ""):
                results = []

                # Setup a progress bar
                progress_bar = st.progress(0)
                total_rows = len(df)

                for index, row in df.iterrows():
                    # Récupérer les valeurs des clés sélectionnées pour construire l'URL
                    url_components = []
                    for key in selected_keys:
                        value = row[key]
                        if pd.isna(value) or value == "":
                            st.warning(f"La valeur de la clé {key} pour la ligne {index + 1} est vide ou non valide. Ignorée.")
                            continue
                        url_components.append(transform_text(value))
                    
                    if len(url_components) == 0:
                        st.warning(f"Aucune valeur valide pour les clés sélectionnées à la ligne {index + 1}. Ignorée.")
                        continue

                    replacements = {key: '' if pd.isna(value) else str(value) for key, value in row.items()}
                    
                    text = master_spin(master_spin_text, replacements)
                    url_component = "-".join(url_components)
                    h1_content = extract_h1_content(text)
                    results.append([url_component, text, f"{url_prefix}-{url_component}", h1_content])

                    # Update progress bar
                    progress_bar.progress((index + 1) / total_rows)

                output_df = pd.DataFrame(results, columns=["URL_Components", "Texte", "URL", "H1_Content"])

                # Convert DataFrame to Excel and save to BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    output_df.to_excel(writer, index=False)
                buffer.seek(0)

                # Create download button
                st.success("Génération terminée !")
                st.download_button(
                    label="Télécharger le fichier de sortie",
                    data=buffer,
                    file_name="textes-villes-pf.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Veuillez importer les fichiers requis ou entrer le texte maître.")

if __name__ == "__main__":
    main()
