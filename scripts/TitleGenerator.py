import streamlit as st
import pandas as pd
import openai
from io import BytesIO

# Initialisation de la clé API OpenAI
openai.api_key = st.secrets["openai_api_key"]

def create_embedding(text):
    """Crée un embedding pour le texte donné."""
    try:
        # Utilisation de la nouvelle méthode embeddings
        response = openai.embeddings.create(input=text, model="text-embedding-3-small")
        return response['data'][0]['embedding']
    except Exception as e:
        st.error(f"Erreur lors de la création de l'embedding : {str(e)}")
        return None

def generate_title_with_gpt(product_info, embedding):
    """Génère un titre SEO en utilisant GPT-3.5-turbo."""
    try:
        prompt = f"""
        Utilise les éléments trouvés dans {product_info} pour créer une balise title structurée comme ceci : "Product type" "Gender" "Product Name" "Color"
        Voici un exemple en anglais : Jacket Woman Le Vrai Claude 3.0 Red
        La balise title doit être générée dans la langue identifiée dans l'URL dans {product_info}.
        .com/products/ = anglais
        .com/it/products/ = italien
        .com/es/products/ = espagnol
        .fr/products/ = français
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un expert en SEO qui génère des balises title pour un site français, anglais, espagnol et italien."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        st.error(f"Erreur lors de la génération du titre : {str(e)}")
        return None

def process_dataframe(df):
    """Traite le DataFrame pour créer les embeddings et générer les titres."""
    # Création des embeddings
    df['embedding'] = df.apply(lambda row: create_embedding(f"{row['Titre actuel']} {row['H1']} {row['Description']}"), axis=1)
    
    # Génération des nouveaux titres
    df['Nouveau Titre'] = df.apply(lambda row: generate_title_with_gpt(
        f"Produit: {row['H1']}, Description: {row['Description']}", 
        row['embedding']
    ), axis=1)
    
    return df[['URL', 'Nouveau Titre']]

def main():
    st.title("Générateur de balises title optimisées avec OpenAI")

    uploaded_file = st.file_uploader("Choisissez un fichier XLSX", type="xlsx")
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        required_columns = ['URL', 'Titre actuel', 'H1', 'Description']
        if not all(col in df.columns for col in required_columns):
            st.error("Le fichier Excel doit contenir les colonnes : URL, Titre actuel, H1, Description")
            return

        if st.button("Générer les titres"):
            with st.spinner('Génération des titres en cours...'):
                result_df = process_dataframe(df)
            
            st.success("Génération terminée !")
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

if __name__ == "__main__":
    main()
