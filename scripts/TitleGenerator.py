import streamlit as st
import pandas as pd
from io import BytesIO
from product_category import ProductCategoryClassifier
from polyglot.detect import Detector
import spacy

# Charger les modèles
product_classifier = ProductCategoryClassifier()
nlp = spacy.load("en_core_web_sm")  # Modèle anglais de spaCy

# Dictionnaire étendu pour les genres
GENDERS = {
    'en': ['men', 'women', 'children', 'kids', 'unisex'],
    'es': ['hombre', 'mujer', 'niños', 'unisex'],
    'it': ['uomo', 'donna', 'bambini', 'unisex'],
    'fr': ['homme', 'femme', 'enfants', 'unisexe']
}

def main():
    st.title("Générateur de balises title multilingue et multi-catégories")

    uploaded_file = st.file_uploader("Choisissez un fichier XLSX", type="xlsx")
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        required_columns = ['URL', 'Titre actuel', 'H1', 'Description']
        if not all(col in df.columns for col in required_columns):
            st.error("Le fichier Excel doit contenir les colonnes : URL, Titre actuel, H1, Description")
            return

        if st.button("Générer les titres"):
            df['Nouveau Titre'] = df.apply(generate_title, axis=1)
            
            result_df = df[['URL', 'Nouveau Titre']]
            
            st.dataframe(result_df)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False)
            output.seek(0)
            st.download_button(
                label="Télécharger les résultats",
                data=output,
                file_name="nouvelles_balises_title.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def generate_title(row):
    all_text = f"{row['Titre actuel']} {row['H1']} {row['Description']}"
    
    # Détection de la langue
    detector = Detector(all_text)
    language = detector.language.code
    
    # Classification du produit
    product_categories = product_classifier.predict(all_text)
    product_kind = product_categories[0] if product_categories else ''
    
    # Extraction du genre
    gender = extract_gender(all_text, language)
    
    # Extraction du nom du produit et de la couleur
    doc = nlp(row['H1'])
    product_name = ' '.join([token.text for token in doc if not token.is_stop and not token.is_punct])
    color = extract_color(all_text)
    
    # Génération du titre
    title_structure = "{Product Kind} {Gender} {Product Name} {Color}"
    return title_structure.format(
        Product_Kind=product_kind,
        Gender=gender,
        Product_Name=product_name,
        Color=color
    )

def extract_gender(text, language):
    lower_text = text.lower()
    for gender in GENDERS.get(language, GENDERS['en']):
        if gender in lower_text:
            return gender
    return ''

def extract_color(text):
    doc = nlp(text)
    colors = [ent.text for ent in doc.ents if ent.label_ == 'COLOR']
    return colors[0] if colors else ''

if __name__ == "__main__":
    main()
