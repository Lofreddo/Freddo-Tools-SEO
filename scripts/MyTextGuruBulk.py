import pandas as pd
import nltk
from nltk import ngrams, pos_tag, word_tokenize
from bs4 import BeautifulSoup
from collections import Counter
import string
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO  # Import nécessaire pour gérer le buffer en mémoire

# Téléchargement de la liste de stop words et de 'punkt'
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

# Définir les listes de mots d'arrêt et de lettres de l'alphabet
french_stopwords_list = nltk.corpus.stopwords.words('french')
alphabet_list = list(string.ascii_lowercase)

# Fonction pour nettoyer le texte HTML
def clean_html(text):
    if isinstance(text, str):
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text().lower()
    else:
        return ""

# Fonction pour extraire les mots et les n-grams
def extract_words_ngrams(text, n):
    tokens = word_tokenize(text)
    pos_tokens = pos_tag(tokens)
    
    # Ignorer les mots vides, non alphabétiques, les verbes, les auxiliaires et les lettres seules
    filtered_tokens = [token for token, pos in pos_tokens if token not in french_stopwords_list and token.isalpha() and pos not in ['VB', 'VBP', 'VBZ', 'VBD', 'VBG', 'VBN'] and token not in alphabet_list]
    
    if n > 1:
        n_grams = ngrams(filtered_tokens, n)
        return [' '.join(grams) for grams in n_grams]
    else:
        return filtered_tokens

def process_text(texts):
    cleaned_texts = [clean_html(text) for text in texts]
    all_words = []
    all_bigrams = []
    all_trigrams = []
    
    for cleaned in cleaned_texts:
        words = extract_words_ngrams(cleaned, 1)
        bigrams = extract_words_ngrams(cleaned, 2)
        trigrams = extract_words_ngrams(cleaned, 3)
        
        all_words.extend(words)
        all_bigrams.extend(bigrams)
        all_trigrams.extend(trigrams)
    
    return all_words, all_bigrams, all_trigrams

def main():
    st.title("MyTextGuru")

    # Étape 1: Importer le fichier
    uploaded_file = st.file_uploader("Importer un fichier Excel", type=["xlsx"])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        st.write("Aperçu du fichier importé:")
        st.dataframe(df)

        # Étape 2: Sélectionner la colonne de clé ou d'ID
        id_column = st.selectbox("Sélectionner la colonne de clé ou d'ID", df.columns)
        
        # Étape 3: Sélectionner la colonne contenant les contenus HTML
        content_column = st.selectbox("Sélectionner la colonne contenant les contenus HTML", df.columns)

        if id_column and content_column:
            # Étape 4: Choisir le nombre de lignes à traiter par lot
            lines_per_batch = st.number_input("Nombre de lignes par lot à traiter", min_value=1, value=20)

            # Étape 5: Choisir le nombre de mots à garder
            num_words = st.number_input("Nombre de mots uniques à garder", min_value=1, value=50)
            num_bigrams = st.number_input("Nombre de bigrammes à garder", min_value=1, value=30)
            num_trigrams = st.number_input("Nombre de trigrammes à garder", min_value=1, value=30)

            # Bouton pour lancer le traitement
            if st.button("Lancer l'analyse"):
                # Afficher une barre de progression
                progress_bar = st.progress(0)
                grouped = df.groupby(id_column)
                output_data = []

                total_groups = len(grouped)
                for idx, (group_id, group_data) in enumerate(grouped, start=1):
                    # Limiter le nombre de lignes par lot
                    group_data = group_data.head(lines_per_batch)
                    html_content = group_data[content_column].dropna().tolist()
                    
                    if not html_content:
                        # Si le contenu HTML est vide, passer au groupe suivant
                        output_data.append({
                            'ID': group_id,
                            'Mots Uniques': '',
                            'Duos de Mots': '',
                            'Trios de Mots': ''
                        })
                        progress_bar.progress(idx / total_groups)
                        continue
                    
                    # Traiter le texte
                    words, bigrams, trigrams = process_text(html_content)
                    
                    # Compter les occurrences
                    words_counter = Counter(words)
                    bigrams_counter = Counter(bigrams)
                    trigrams_counter = Counter(trigrams)
                    
                    # Prendre les mots/n-grams les plus courants
                    most_common_words = ', '.join([word for word, count in words_counter.most_common(num_words)])
                    most_common_bigrams = ', '.join([bigram for bigram, count in bigrams_counter.most_common(num_bigrams)])
                    most_common_trigrams = ', '.join([trigram for trigram, count in trigrams_counter.most_common(num_trigrams)])
                    
                    # Ajouter les résultats au tableau de sortie
                    output_data.append({
                        'ID': group_id,
                        'Mots Uniques': most_common_words,
                        'Duos de Mots': most_common_bigrams,
                        'Trios de Mots': most_common_trigrams
                    })
                    
                    # Mettre à jour la barre de progression
                    progress_bar.progress(idx / total_groups)

                # Créer un DataFrame pour le fichier de sortie
                output_df = pd.DataFrame(output_data)

                # Écrire le DataFrame dans un buffer en mémoire
                towrite = BytesIO()
                with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                    output_df.to_excel(writer, index=False)
                towrite.seek(0)  # Remettre le curseur au début du buffer

                # Étape 6: Enregistrer le fichier de sortie
                st.download_button(
                    label="Télécharger les résultats",
                    data=towrite,
                    file_name="resultats.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
