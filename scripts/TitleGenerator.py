import streamlit as st
import pandas as pd
from openai import OpenAI
from io import BytesIO
import threading
import queue
import time

# Initialisation du client OpenAI
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Définir une file d'attente thread-safe pour stocker les résultats
result_queue = queue.Queue()

# Limiter le nombre de threads simultanés pour ne pas surcharger l'API
MAX_THREADS = 5
thread_semaphore = threading.Semaphore(MAX_THREADS)

def create_embedding(text):
    """Crée un embedding pour le texte donné."""
    try:
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception as e:
        st.error(f"Erreur lors de la création de l'embedding : {str(e)}")
        return None

def title_case(s):
    """Met en majuscule la première lettre de chaque mot."""
    return ' '.join(word.capitalize() for word in s.split())

def generate_title_with_gpt(product_info, embedding, language, title_structure, exemple_title):
    """Génère un titre SEO en utilisant GPT-3.5-turbo sans balises HTML."""
    try:
        prompt = f"""
        Utilise les éléments trouvés dans {product_info} pour créer une balise title structurée comme ceci : "{title_structure}"
        Voici un exemple en anglais : {exemple_title}
        La balise title doit être générée en {language}.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Vous êtes un expert en SEO qui génère des balises title en {language}."},
                {"role": "user", "content": prompt}
            ]
        )
        title = response.choices[0].message.content.strip()
        # Exclure les balises HTML <title> et appliquer le title case
        title = title_case(title.replace('<title>', '').replace('</title>', '').strip())
        return title
    except Exception as e:
        st.error(f"Erreur lors de la génération du titre : {str(e)}")
        return None

def threaded_title_generation(row, language, title_structure, exemple_title):
    with thread_semaphore:
        embedding = create_embedding(f"{row['Titre actuel']} {row['H1']} {row['Description']}")
        title = generate_title_with_gpt(
            f"URL: {row['URL']}, Produit: {row['H1']}, Description: {row['Description']}", 
            embedding,
            language,
            title_structure,
            exemple_title
        )
        result_queue.put((row['URL'], title))

def process_dataframe_multithreading(df, language, title_structure, exemple_title):
    threads = []
    for index, row in df.iterrows():
        thread = threading.Thread(target=threaded_title_generation, args=(row, language, title_structure, exemple_title))
        threads.append(thread)
        thread.start()
    
    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()

    # Collecter les résultats de la file d'attente
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    return pd.DataFrame(results, columns=['URL', 'Nouveau Titre'])

def update_progress_and_count():
    count = 0
    total = st.session_state['total_titles']
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while count < total:
        time.sleep(1)  # Attendre 1 seconde
        count = result_queue.qsize()
        progress = count / total
        progress_bar.progress(progress)
        status_text.text(f"Titres générés : {count}/{total}")
        
    progress_bar.progress(1.0)
    status_text.text(f"Génération terminée ! {total}/{total} titres générés.")

def main():
    st.title("Générateur de balises title optimisées avec OpenAI")

    language = st.selectbox(
        "Choisissez la langue pour les balises title",
        ["Anglais", "Français", "Espagnol", "Italien"]
    )

    title_structure = st.text_input(
        "Définissez la structure du titre",
        '"Product type" "Gender" "Product Name" "Color"'
    )

    exemple_title = st.text_input(
        "Donnez un exemple de titre",
        "Jacket Woman Le Vrai Claude 3.0 Red"
    )

    uploaded_file = st.file_uploader("Choisissez un fichier XLSX", type="xlsx")
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        
        required_columns = ['URL', 'Titre actuel', 'H1', 'Description']
        if not all(col in df.columns for col in required_columns):
            st.error("Le fichier Excel doit contenir les colonnes : URL, Titre actuel, H1, Description")
            return

        if st.button("Générer les titres"):
            st.session_state['total_titles'] = len(df)
            
            # Créer un thread pour mettre à jour la progression
            progress_thread = threading.Thread(target=update_progress_and_count)
            progress_thread.start()
            
            # Traitement du DataFrame avec multithreading
            result_df = process_dataframe_multithreading(df, language, title_structure, exemple_title)
            
            # Attendre que le thread de progression se termine
            progress_thread.join()
            
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
