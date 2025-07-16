# scripts/ImageNameGenerator.py

import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import unicodedata
from io import BytesIO

# --- Fonctions Utilitaires (inchangées) ---

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
    
    nfkd_form = unicodedata.normalize('NFKD', name)
    cleaned_name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    cleaned_name = cleaned_name.lower()
    cleaned_name = re.sub(r'[\s_]+', '-', cleaned_name)
    cleaned_name = re.sub(r'[^a-z0-9-]', '', cleaned_name)
    cleaned_name = re.sub(r'-+', '-', cleaned_name)
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

# --- Fonction Principale de l'Application (modifiée) ---

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
    2.  Chargez votre fichier Excel (`.xlsx`).
    3.  **Sélectionnez les colonnes contenant les descriptions** de vos produits (nom, type, couleur, description, etc.).
    4.  Lancez la génération et téléchargez les résultats !
    """)

    # --- Barre latérale pour la configuration ---
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Clé API OpenAI", type="password", help="Votre clé est nécessaire pour communiquer avec l'IA. Elle n'est pas stockée.")
        st.markdown("---")
        uploaded_file = st.file_uploader("Chargez votre fichier Excel", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("Fichier chargé avec succès !")
            st.dataframe(df.head())

            # --- NOUVEAU : Sélection de plusieurs colonnes ---
            st.header("2. Sélection des Colonnes Descriptives")
            st.info("Sélectionnez toutes les colonnes contenant des informations qui décrivent le produit. L'IA les analysera ensemble.")
            
            all_columns = df.columns.tolist()
            # Pré-sélectionne la première colonne par défaut si elle existe
            default_selection = [all_columns[0]] if all_columns else []
            
            selected_columns = st.multiselect(
                "Choisissez les colonnes à analyser",
                options=all_columns,
                default=default_selection
            )
            
            # Bouton de génération
            if st.button("🚀 Générer les noms d'images", use_container_width=True):
                if not api_key:
                    st.error("Veuillez entrer votre clé API OpenAI dans la barre latérale.")
                elif not selected_columns:
                    st.warning("Veuillez sélectionner au moins une colonne à analyser.")
                else:
                    try:
                        client = OpenAI(api_key=api_key)
                        
                        generated_names = []
                        progress_bar = st.progress(0, text="Génération en cours...")

                        # Itération sur chaque ligne du DataFrame
                        for i, row in df.iterrows():
                            # --- NOUVEAU : Concaténation des informations des colonnes sélectionnées ---
                            info_parts = [str(row[col]) for col in selected_columns if pd.notna(row[col]) and str(row[col]).strip()]
                            product_info = ", ".join(info_parts)
                            
                            if not product_info:
                                generated_names.append("") # Ligne vide si aucune info
                                progress_bar.progress((i + 1) / len(df), text=f"Génération en cours... {i+1}/{len(df)}")
                                continue

                            # --- NOUVEAU : Prompt pour OpenAI adapté à l'analyse de texte ---
                            system_prompt = "Tu es un assistant expert en SEO e-commerce. Ta mission est de créer des noms de fichiers d'images concis et optimisés à partir d'une description."
                            user_prompt = f"""
                            Analyse le texte descriptif suivant sur un produit : "{product_info}".

                            Ta tâche est d'extraire de ce texte les 4 informations suivantes :
                            1.  **Type de produit** (ex: robe, t-shirt, pantalon)
                            2.  **Couleur** principale (ex: rouge, bleu, noir)
                            3.  **Caractéristique** distinctive (ex: soie, coton, long, à capuche)
                            4.  **Genre** ou cible (ex: femme, homme, enfant, unisexe)

                            Combine ces informations pour créer un nom de fichier en respectant IMPÉRATIVEMENT ces règles :
                            - **Structure** : `type-produit-couleur-caracteristique-genre`. Si une information n'est pas trouvée, ignore cette partie.
                            - **Longueur** : 4 mots maximum au total.
                            - **Format** : Uniquement des minuscules, pas d'accents, pas de caractères spéciaux. Mots séparés par un tiret "-".

                            Ne retourne QUE le nom de fichier final, sans aucune autre explication.
                            Exemple de sortie attendue : `robe-rouge-soie-femme`
                            """
                            
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                temperature=0.1, # Température basse pour une sortie plus prédictible
                                max_tokens=25
                            )
                            
                            raw_name = response.choices[0].message.content
                            cleaned_name = clean_filename(raw_name)
                            generated_names.append(cleaned_name)

                            # Mise à jour de la barre de progression
                            progress_bar.progress((i + 1) / len(df), text=f"Génération en cours... {i+1}/{len(df)}")
                        
                        progress_bar.empty()
                        st.success("Génération terminée !")
                        
                        df_results = df.copy()
                        df_results['nom_image_genere'] = generated_names
                        
                        st.header("✅ Résultats")
                        st.dataframe(df_results)
                        
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

if __name__ == '__main__':
    main()
