import streamlit as st
import pandas as pd
from openai import OpenAI
from io import BytesIO
import threading
import queue
import time

# --- Configuration OpenAI ---
client = OpenAI(api_key=st.secrets["openai_api_key"])

# File d’attente thread-safe pour collecter les noms générés
result_queue = queue.Queue()

# Limitation du nombre de threads simultanés
MAX_THREADS = 80
thread_semaphore = threading.Semaphore(MAX_THREADS)

def create_embedding(text):
    """(Optionnel) Crée un embedding pour enrichir le prompt."""
    try:
        resp = client.embeddings.create(input=text, model="text-embedding-3-small")
        return resp.data[0].embedding
    except Exception as e:
        st.error(f"Erreur embedding : {e}")
        return None

def clean_filename(s):
    """Nettoie et met en snake_case le nom généré."""
    # Remplace tout caractère non-alphanumérique par un underscore
    safe = ''.join(c if c.isalnum() else '_' for c in s)
    # Uniformise en minuscules et retire doublons de underscores
    parts = [p for p in safe.lower().split('_') if p]
    return '_'.join(parts)

def generate_image_name(product_info, embedding, structure, exemple_name):
    """Appelle GPT pour générer un nom de fichier d’image EN FRANÇAIS."""
    try:
        prompt = f"""
        À partir des informations suivantes : {product_info}
        Génère un nom de fichier d’image **en français**, sans extension, structuré ainsi : {structure}
        Exemple de nom en français : {exemple_name}
        Utilise uniquement des lettres minuscules, des chiffres et des underscores (_).
        """
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                  "role": "system",
                  "content": (
                    "Vous êtes un assistant expert qui génère des noms de fichiers d’images "
                    "clairs, optimisés SEO et rédigés en français."
                  )
                },
                {"role": "user", "content": prompt}
            ]
        )
        raw_name = resp.choices[0].message.content.strip()
        return clean_filename(raw_name)
    except Exception as e:
        st.error(f"Erreur génération nom : {e}")
        return None

def worker(row, structure, exemple_name, url_col, crit_cols):
    """Thread worker : construit le prompt, génère et stocke le résultat."""
    with thread_semaphore:
        info = f"{url_col}: {row[url_col]}, " + ", ".join(f"{c}: {row[c]}" for c in crit_cols if c)
        emb = create_embedding(info)
        name = generate_image_name(info, emb, structure, exemple_name)
        result_queue.put((row[url_col], name))

def process_df(df, structure, exemple_name, url_col, crit_cols):
    threads = []
    for _, row in df.iterrows():
        t = threading.Thread(
            target=worker,
            args=(row, structure, exemple_name, url_col, crit_cols)
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
    return pd.DataFrame(results, columns=[url_col, "nom_image"])

def show_progress(total):
    """Affiche une barre de progression mise à jour chaque seconde."""
    bar = st.progress(0)
    status = st.empty()
    while True:
        count = result_queue.qsize()
        bar.progress(min(count/total, 1.0))
        status.text(f"Noms générés : {count}/{total}")
        if count >= total:
            break
        time.sleep(1)
    status.text(f"Terminé ! {total}/{total} noms générés.")

def main():
    st.title("Générateur de noms d’images (EN FRANÇAIS) avec OpenAI")

    # Structure et exemple en français
    structure = st.text_input(
        "Structure du nom (snake_case, ex. sujet_couleur_angle)",
        "sujet_couleur_angle"
    )
    exemple_name = st.text_input(
        "Exemple de nom (ex. tournesol_jaune_vue_haut)",
        "tournesol_jaune_vue_haut"
    )

    uploaded = st.file_uploader("Chargez votre fichier Excel (.xlsx)", type="xlsx")
    if not uploaded:
        return

    df = pd.read_excel(uploaded)
    url_col = st.selectbox("Colonne contenant le chemin/URL de l’image", df.columns)

    crit_cols = []
    for i in range(1, 6):
        col = st.selectbox(f"Critère #{i}", [""] + list(df.columns), key=f"crit_{i}")
        if col:
            crit_cols.append(col)
    if not crit_cols:
        st.error("Sélectionnez au moins un critère")
        return

    if st.button("Générer les noms d’images"):
        total = len(df)
        st.session_state['total'] = total

        # Démarre la barre de progression
        prog_thread = threading.Thread(target=show_progress, args=(total,))
        prog_thread.start()

        # Génération en multithreading
        result_df = processDf = process_df(df, structure, exemple_name, url_col, crit_cols)
        prog_thread.join()

        st.success("Tous les noms sont prêts !")
        st.dataframe(result_df)

        # Préparation du fichier à télécharger
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False)
        out.seek(0)
        st.download_button(
            "Télécharger les noms d’images",
            data=out,
            file_name="noms_images_fr.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
