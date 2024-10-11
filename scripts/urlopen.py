import streamlit as st
import pandas as pd
import requests
import time

def process_urls_in_batches(urls, batch_size=8, delay=3):
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        st.write(f"Traitement du lot {i//batch_size + 1}")
        
        for url in batch:
            st.write(f"Ouverture de : {url}")
            try:
                response = requests.get(url, timeout=3)
                st.write(f"Statut : {response.status_code}")
            except requests.RequestException as e:
                st.write(f"Erreur : {e}")
        
        if i + batch_size < len(urls):
            st.write(f"Attente de {delay} secondes avant le prochain lot...")
            time.sleep(delay)

def main():
    st.title("URL Opener par lots")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel ou CSV", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        columns = df.columns.tolist()
        selected_column = st.selectbox("Sélectionnez la colonne contenant les URLs", columns)
        
        if st.button("Ouvrir les URLs"):
            urls = df[selected_column].tolist()
            process_urls_in_batches(urls)
            
            st.success("Toutes les URLs ont été traitées.")

if __name__ == "__main__":
    main()
