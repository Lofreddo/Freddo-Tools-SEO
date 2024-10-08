import requests
import pandas as pd
import io
import concurrent.futures
import streamlit as st

def main():
    # Titre de l'application
    st.title("Recherche de mots-clés avec ValueSERP")

    # Zone de texte pour entrer les mots-clés
    keywords_input = st.text_area("Entrez vos mots-clés, un par ligne:")

    # Conversion des mots-clés en liste
    keywords = keywords_input.strip().split('\n')

    # Menu déroulant pour sélectionner le domaine Google
    google_domain = st.selectbox(
        "Sélectionnez le domaine Google:",
        ["google.fr", "google.com", "google.co.uk", "google.de", "google.es"]
    )

    # Menu déroulant pour sélectionner le dispositif
    device = st.selectbox(
        "Sélectionnez le dispositif:",
        ["desktop", "mobile"]
    )

 # Menu déroulant pour sélectionner le nombre de résultats par mots-clés
    num = st.selectbox(
        "Sélectionnez le nombre de résultats:",
        ["10", "20", "30", "40", "50", "100"]
    )

# Menu déroulant pour sélectionner le pays
    gl = st.selectbox(
        "Sélectionnez le pays:",
        ["fr", "es", "de", "en"]
    )

# Menu déroulant pour sélectionner la langue
    hl = st.selectbox(
        "Sélectionnez la langue:",
        ["fr", "es", "de", "en"]
    )

# Menu déroulant pour sélectionner la location
    location = st.selectbox(
        "Sélectionnez la langue:",
        ["France", "United Kingdom", "United States", "Spain", "Germany"]
    )
    
    # Fonction pour récupérer les résultats de recherche
    def fetch_results(keyword):
        params = {
            'api_key': '81293DFA2CEF4FE49DB08E002D947143',
            'q': keyword,
            'location': location,
            'google_domain': google_domain,
            'gl': gl,
            'hl': hl,
            'device': device,
            'num': num,
            'page': '1',
            'output': 'csv',
            'csv_fields': 'search.q,organic_results.position,organic_results.title,organic_results.link,organic_results.domain,organic_results.page'
        }
        api_result = requests.get('https://api.valueserp.com/search', params)
        
        if api_result.status_code == 200:
            # Lire les données dans un DataFrame en spécifiant explicitement l'encodage
            result_df = pd.read_csv(io.StringIO(api_result.text), encoding='utf-8')
            return result_df
        else:
            st.error(f"La requête pour le mot-clé '{keyword}' a échoué avec le code d'état {api_result.status_code}.")
            return None

    # Fonction pour nettoyer et réencoder les données en UTF-8
    def clean_dataframe(df):
        for column in df.columns:
            df[column] = df[column].apply(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)
        return df

    # Bouton pour lancer la recherche
    if st.button("Lancer la recherche"):
        if keywords:
            # Créez un DataFrame vide pour stocker tous les résultats
            all_results = pd.DataFrame()

            # Utilisez un ThreadPoolExecutor pour effectuer les requêtes en parallèle
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(fetch_results, keywords)

            # Ajoutez les DataFrames de résultats au DataFrame de tous les résultats
            for result_df in results:
                if result_df is not None:
                    all_results = pd.concat([all_results, result_df], ignore_index=True)

            # Nettoyer et réencoder les données
            all_results = clean_dataframe(all_results)

            # Affiche les résultats dans Streamlit
            st.dataframe(all_results)

            # Ajoutez un bouton pour télécharger le fichier Excel
            if not all_results.empty:
                @st.cache_data
                def convert_df(df):
                    try:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        processed_data = output.getvalue()
                        return processed_data
                    except Exception as e:
                        st.error(f"Erreur lors de la conversion du DataFrame en Excel: {e}")
                        return None

                excel_data = convert_df(all_results)
                if excel_data:
                    st.download_button(
                        label="Télécharger les résultats",
                        data=excel_data,
                        file_name='results.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
        else:
            st.error("Veuillez entrer au moins un mot-clé.")

if __name__ == '__main__':
    main()
