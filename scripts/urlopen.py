import streamlit as st
import pandas as pd
import time

def open_urls_automatically(urls, batch_size=8, delay=3):
    st.write("Ouverture automatique des URLs...")
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        
        js_code = """
        <script>
        function openURLs() {
            var urls = %s;
            urls.forEach(function(url) {
                window.open(url, '_blank');
            });
        }
        openURLs();
        </script>
        """ % str(batch)
        
        st.components.v1.html(js_code, height=0)
        
        if i + batch_size < len(urls):
            time.sleep(delay)

def main():
    st.title("Ouverture automatique d'URLs")

    uploaded_file = st.file_uploader("Choisissez un fichier Excel ou CSV", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        columns = df.columns.tolist()
        selected_column = st.selectbox("Sélectionnez la colonne contenant les URLs", columns)
        
        if st.button("Ouvrir les URLs automatiquement"):
            urls = df[selected_column].tolist()
            open_urls_automatically(urls)
            
            st.success("Tentative d'ouverture de toutes les URLs terminée.")

if __name__ == "__main__":
    main()
