import streamlit as st
import pandas as pd
import re
from io import BytesIO

def main():
    st.title("Générateur de balises title")

    # Upload du fichier Excel
    uploaded_file = st.file_uploader("Choisissez un fichier XLSX", type="xlsx")
    
    if uploaded_file is not None:
        # Lecture du fichier Excel
        df = pd.read_excel(uploaded_file)
        
        # Vérification des colonnes requises
        required_columns = ['URL', 'Titre actuel', 'H1', 'Description']
        if not all(col in df.columns for col in required_columns):
            st.error("Le fichier Excel doit contenir les colonnes : URL, Titre actuel, H1, Description")
            return

        # Sélection de la langue
        language = st.selectbox("Langue", ["en", "es", "it"])
        
        # Bouton pour générer les titres
        if st.button("Générer les titres"):
            df['Nouveau Titre'] = df.apply(generate_title, axis=1, language=language)
            
            # Création d'un nouveau DataFrame avec seulement URL et Nouveau Titre
            result_df = df[['URL', 'Nouveau Titre']]
            
            # Affichage des résultats
            st.dataframe(result_df)
            
            # Bouton pour télécharger les résultats
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

def generate_title(row, language):
    # Structure du titre
    structure = {
        'en': "{Product Kind} {Gender} {Product Name} {Color}",
        'es': "{Tipo de Producto} {Género} {Nombre del Producto} {Color}",
        'it': "{Tipo di Prodotto} {Genere} {Nome del Prodotto} {Colore}"
    }
    
    # Extraction des informations
    product_kind = extract_product_kind(row['Description'])
    gender = extract_gender(row['Description'])
    product_name = extract_product_name(row['H1'])
    color = extract_color(row['Description'])
    
    # Génération du titre
    return structure[language].format(
        **{'Product Kind': product_kind, 'Gender': gender, 'Product Name': product_name, 'Color': color}
    )

def extract_product_kind(description):
    # Implémentez la logique d'extraction du type de produit
    product_types = ['shirt', 'pants', 'shoes', 'jacket', 'dress']
    for product in product_types:
        if product in description.lower():
            return product
    return ''

def extract_gender(description):
    # Implémentez la logique d'extraction du genre
    if 'men' in description.lower():
        return 'Men'
    elif 'women' in description.lower():
        return 'Women'
    return ''

def extract_product_name(h1):
    # Implémentez la logique d'extraction du nom du produit
    # Exemple : prendre les mots après le type de produit et le genre
    words = h1.split()
    for i, word in enumerate(words):
        if word.lower() in ['men', 'women', 'shirt', 'pants', 'shoes', 'jacket', 'dress']:
            return ' '.join(words[i+1:i+4])  # Prend les 3 mots suivants
    return ' '.join(words[:3])  # Si rien n'est trouvé, prend les 3 premiers mots

def extract_color(description):
    # Implémentez la logique d'extraction de la couleur
    colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'purple', 'pink', 'orange', 'brown']
    for color in colors:
        if color in description.lower():
            return color
    return ''

if __name__ == "__main__":
    main()
