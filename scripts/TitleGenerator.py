import streamlit as st
import pandas as pd
import re
from io import BytesIO
from product_category import ProductCategoryClassifier
from polyglot.detect import Detector
import spacy

# Charger les modèles
product_classifier = ProductCategoryClassifier()
nlp = spacy.load("en_core_web_sm")  # Modèle anglais de spaCy

# Dictionnaire étendu pour les genres
GENDERS = {
    'en': {
        'men': ['men', 'man', 'male', 'gentleman', 'gent'],
        'women': ['women', 'woman', 'female', 'lady', 'ladies'],
        'children': ['children', 'child', 'kid', 'kids', 'youth', 'junior', 'juniors'],
        'unisex': ['unisex', 'universal', 'all gender']
    },
    'es': {
        'hombre': ['hombre', 'hombres', 'masculino', 'caballero', 'caballeros'],
        'mujer': ['mujer', 'mujeres', 'femenino', 'dama', 'damas'],
        'niños': ['niño', 'niña', 'niños', 'niñas', 'infantil', 'juvenil'],
        'unisex': ['unisex', 'universal']
    },
    'it': {
        'uomo': ['uomo', 'uomini', 'maschile', 'maschio'],
        'donna': ['donna', 'donne', 'femminile', 'femmina'],
        'bambini': ['bambino', 'bambina', 'bambini', 'bambine', 'ragazzo', 'ragazza', 'ragazzi', 'ragazze'],
        'unisex': ['unisex', 'universale']
    },
    'fr': {
        'homme': ['homme', 'hommes', 'masculin', 'monsieur', 'messieurs'],
        'femme': ['femme', 'femmes', 'féminin', 'madame', 'mesdames'],
        'enfants': ['enfant', 'enfants', 'garçon', 'garçons', 'fille', 'filles', 'junior', 'juniors'],
        'unisexe': ['unisexe', 'universel']
    }
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
    
    # Si la langue n'est pas dans notre dictionnaire, on utilise l'anglais par défaut
    gender_dict = GENDERS.get(language, GENDERS['en'])
    
    for main_gender, variations in gender_dict.items():
        for variation in variations:
            # Utilisation d'une expression régulière pour trouver le mot entier
            if re.search(r'\b' + variation + r'\b', lower_text):
                return main_gender
    
    return ''  # Retourne une chaîne vide si aucun genre n'est trouvé

def extract_color(text):
    doc = nlp(text)
    colors = [ent.text for ent in doc.ents if ent.label_ == 'COLOR']
    return colors[0] if colors else ''

if __name__ == "__main__":
    main()
