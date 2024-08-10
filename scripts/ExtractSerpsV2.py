import requests
import pandas as pd
import io
import streamlit as st
import time

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
        "Sélectionnez la location:",
        ["France", "United Kingdom", "United States", "Spain", "Germany"]
    )

    # Fonction pour créer une demande batch
    def create_batch_request(keywords):
        batch_payload = {
            'api_key': '81293DFA2CEF4FE49DB08E002D947143',
            'searches': []
        }

        for keyword in keywords:
            search_params = {
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
            batch_payload['searches'].append(search_params)

        response = requests.post('https://api.valueserp.com/batches', json=batch_payload)
        
        if response.status_code == 200:
            return response.json()['batch_id']
        else:
            st.error(f"Erreur lors de la création du batch: {response.status_code} - {response.text}")
            return None

    # Fonction pour vérifier le statut du batch
    def check_batch_status(batch_id):
        status_url = f"https://api.valueserp.com/batches/{batch_id}/status?api_key=81293DFA2CEF4FE49DB08E002D947143"
        response = requests.get(status_url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erreur lors de la vérification du statut du batch: {response.status_code} - {response.text}")
            return None

    # Fonction pour récupérer les résultats du batch
    def fetch_batch_results(batch_id):
        results_url = f"https://api.valueserp.com/batches/{batch_id}/results?api_key=81293DFA2CEF4FE49DB08E002D947143"
        response = requests.get(results_url)
        if response.status_code == 200:
            result_df = pd.read_csv(io.StringIO(response.text), encoding='utf-8')
            return result_df
        else:
            st.error(f"Erreur lors de la récupération des résultats du batch: {response.status_code} - {response.text}")
            return None

    # Fonction pour nettoyer et réencoder les données en UTF-8
    def clean_dataframe(df):
        for column in df.columns:
            df[column] = df[column].apply(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)
        return df

    # Bouton pour lancer la recherche
    if st.button("Lancer la recherche"):
        if keywords:
            # Créez un batch et récupérez l'ID
            batch_id = create_batch_request(keywords)

            if batch_id:
                st.info("Batch créé avec succès. En attente des résultats...")

                # Attente des résultats du batch
                batch_status = check_batch_status(batch_id)
                while batch_status and batch_status['status'] != 'completed':
                    time.sleep(5)  # Attendre 5 secondes avant de vérifier à nouveau
                    batch_status = check_batch_status(batch_id)

                # Récupérer les résultats une fois le batch terminé
                if batch_status['status'] == 'completed':
                    all_results = fetch_batch_results(batch_id)

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
                    st.error("Le batch n'a pas pu être complété avec succès.")
        else:
            st.error("Veuillez entrer au moins un mot-clé.")

if __name__ == '__main__':
    main()
