import streamlit as st
import pandas as pd
import time

def open_urls_in_batches(urls, batch_size=8, delay=3):
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        st.write(f"Lot {i//batch_size + 1}")
        
        for url in batch:
            st.link_button(f"Ouvrir : {url}", url)
        
        if i + batch_size < len(urls):
            with st.spinner(f"Attente de {delay} secondes avant le prochain lot..."):
                time.sleep(delay)

def main():
    st.title("Ouverture d'URLs par lots")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel ou CSV", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            columns = df.columns.tolist()
            selected_column = st.selectbox("Sélectionnez la colonne contenant les URLs", columns)
            
            if st.button("Générer les liens"):
                urls = df[selected_column].tolist()
                open_urls_in_batches(urls)
                
                st.success("Tous les liens ont été générés.")
        except Exception as e:
            st.error(f"Une erreur s'est produite lors du traitement du fichier : {str(e)}")

if __name__ == "__main__":
    main()
