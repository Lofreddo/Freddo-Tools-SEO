# scripts/ImageNameGenerator.py

import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import unicodedata
from io import BytesIO

# --- Fonctions Utilitaires ---

def clean_filename(name: str) -> str:
    """
    Nettoie une chaîne de caractères pour la transformer en nom de fichier valide.
    - Supprime les accents
    - Met en minuscules
    - Remplace les espaces et autres séparateurs par des tirets
    - Ne conserve que les caractères alphanumériques et les tirets
    """
    if not isinstance(name, str):
        return ""
    
    # 1. Normalisation pour supprimer les accents
    nfkd_form = unicodedata.normalize('NFKD', name)
    cleaned_name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # 2. Mise en minuscules
    cleaned_name = cleaned_name.lower()
    
    # 3. Remplacement des espaces et de certains caractères par des tirets
    cleaned_name = re.sub(r'[\s_]+', '-', cleaned_name)
    
    # 4. Suppression de tous les caractères non-valides
    cleaned_name = re.sub(r'[^a-z0-9-]', '', cleaned_name)
    
    # 5. Suppression des tirets multiples
    cleaned_name = re.sub(r'-+', '-', cleaned_name)
    
    # 6. Suppression des tirets en début ou fin de chaîne
    cleaned_name = cleaned_name.strip('-')
    
    return cleaned_name

@st.cache_data(show_spinner=False)
def convert_df_to_excel(df):
    """Convertit un DataFrame en objet BytesIO pour le téléchargement Excel."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Noms_Images')
    processed_data = output.getvalue()
    return processed_data

# --- Fonction Principale de l'Application ---

def main():
    """
    Fonction principale de l'application Streamlit pour générer des noms d'images.
    """
    st.set_page_config(layout="wide")
    st.title("🤖 Générateur de Noms d'Images (IA)")
    st.markdown("""
    Cet outil utilise l'IA (OpenAI `gpt-4o-mini`) pour générer des noms de fichiers optimisés pour vos images de produits.
    
    **Instructions :**
    1.  Entrez votre clé API OpenAI.
    2.  Chargez votre fichier Excel (`.xlsx`) contenant les descriptions de vos produits.
    3.  Sélectionnez les colonnes correspondant aux informations requises.
    4.  Lancez la génération et téléchargez les résultats !
    """)

    # --- Barre latérale pour la configuration ---
    with st.sidebar:
        st.header("Configuration")
        
        # Saisie de la clé API OpenAI
        api_key = st.text_input("Clé API OpenAI", type="password", help="Votre clé est nécessaire pour communiquer avec l'IA. Elle n'est pas stockée.")
        
        st.markdown("---")
        # Uploader de fichier
        uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("Fichier chargé avec succès !")
            st.dataframe(df.head())

            # --- Sélection des colonnes ---
            st.header("2. Mappage des Colonnes")
            st.info("Sélectionnez les colonnes de votre fichier qui contiennent les informations pour la génération.")
            
            cols = df.columns.tolist()
            # Option pour indiquer qu'une information n'est pas disponible
            options = ["Ne pas utiliser"] + cols 

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                col_produit = st.selectbox("Type de produit*", options=options)
            with col2:
                col_couleur = st.selectbox("Couleur", options=options)
            with col3:
                col_caracteristiques = st.selectbox("Caractéristiques", options=options)
            with col4:
                col_genre = st.selectbox("Genre", options=options)
            
            # Bouton de génération
            if st.button("🚀 Générer les noms d'images", use_container_width=True):
                if not api_key:
                    st.error("Veuillez entrer votre clé API OpenAI dans la barre latérale.")
                elif col_produit == "Ne pas utiliser":
                    st.warning("Veuillez sélectionner au moins la colonne 'Type de produit'.")
                else:
                    try:
                        client = OpenAI(api_key=api_key)
                        
                        generated_names = []
                        progress_bar = st.progress(0, text="Génération en cours...")

                        # Itération sur chaque ligne du DataFrame
                        for i, row in df.iterrows():
                            # Construction de la chaîne d'information pour l'IA
                            info_parts = []
                            if col_produit != "Ne pas utiliser" and pd.notna(row[col_produit]):
                                info_parts.append(f"Type de produit: {row[col_produit]}")
                            if col_couleur != "Ne pas utiliser" and pd.notna(row[col_couleur]):
                                info_parts.append(f"Couleur: {row[col_couleur]}")
                            if col_caracteristiques != "Ne pas utiliser" and pd.notna(row[col_caracteristiques]):
                                info_parts.append(f"Caractéristiques: {row[col_caracteristiques]}")
                            if col_genre != "Ne pas utiliser" and pd.notna(row[col_genre]):
                                info_parts.append(f"Genre: {row[col_genre]}")
                            
                            product_info = ", ".join(info_parts)
                            
                            if not product_info:
                                generated_names.append("") # Ligne vide si aucune info
                                continue

                            # --- Prompt pour OpenAI ---
                            system_prompt = "Tu es un assistant expert en SEO e-commerce. Ta mission est de créer des noms de fichiers d'images concis et optimisés."
                            user_prompt = f"""
                            À partir des informations suivantes : "{product_info}".
                            
                            Crée un nom de fichier pour une image de ce produit en respectant IMPÉRATIVEMENT ces règles :
                            1. Structure : `type-produit-couleur-caracteristiques-genre`.
                            2. Maximum 4 mots au total.
                            3. Langue : français.
                            4. Format : Uniquement des minuscules, pas d'accents, pas de caractères spéciaux. Mots séparés par un tiret "-".
                            
                            Ne me donne QUE le nom de fichier final, sans aucune autre explication.
                            Exemple de sortie attendue : robe-rouge-soie-femme
                            """
                            
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                temperature=0.2,
                                max_tokens=20
                            )
                            
                            raw_name = response.choices[0].message.content
                            cleaned_name = clean_filename(raw_name)
                            generated_names.append(cleaned_name)

                            # Mise à jour de la barre de progression
                            progress_bar.progress((i + 1) / len(df), text=f"Génération en cours... {i+1}/{len(df)}")
                        
                        progress_bar.empty()
                        st.success("Génération terminée !")
                        
                        # Ajout de la nouvelle colonne et affichage
                        df_results = df.copy()
                        df_results['nom_image_genere'] = generated_names
                        
                        st.header("✅ Résultats")
                        st.dataframe(df_results)
                        
                        # Téléchargement des résultats
                        excel_data = convert_df_to_excel(df_results)
                        st.download_button(
                            label="📥 Télécharger le fichier Excel avec les noms",
                            data=excel_data,
                            file_name="resultats_noms_images.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    except Exception as e:
                        st.error(f"Une erreur est survenue lors de la communication avec OpenAI : {e}")

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier Excel : {e}")

# Permet de tester le script en l'exécutant directement (optionnel)
if __name__ == '__main__':
    main()
