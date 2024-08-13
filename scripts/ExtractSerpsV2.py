import requests
import pandas as pd
import io
import streamlit as st
import uuid
import time
import zipfile
import json

API_KEY = '81293DFA2CEF4FE49DB08E002D947143'

def main():
    st.title("Recherche de mots-clés avec ValueSERP en Batches")

    # Entrée de l'utilisateur
    keywords_input = st.text_area("Entrez vos mots-clés, un par ligne:")
    keywords = keywords_input.strip().split('\n')

    google_domain = st.selectbox(
        "Sélectionnez le domaine Google:",
        ["google.fr", "google.com", "google.co.uk", "google.de", "google.es"]
    )

    device = st.selectbox(
        "Sélectionnez le dispositif:",
        ["desktop", "mobile"]
    )

    num = st.selectbox(
        "Sélectionnez le nombre de résultats:",
        ["10", "20", "30", "40", "50", "100"]
    )

    gl = st.selectbox(
        "Sélectionnez le pays:",
        ["fr", "es", "de", "en"]
    )

    hl = st.selectbox(
        "Sélectionnez la langue:",
        ["fr", "es", "de", "en"]
    )

    location = st.selectbox(
        "Sélectionnez la location:",
        ["France", "United Kingdom", "United States", "Spain", "Germany"]
    )

    batch_prefix = st.text_input("Entrez un préfixe pour les Batchs:")
    notification_email = st.text_input("Entrez une adresse email pour les notifications:")

    def create_batch_with_keywords(batch_name, keyword_batch):
        searches = []
        for keyword in keyword_batch:
            search_params = {
                'q': keyword,
                'location': location,
                'google_domain': google_domain,
                'gl': gl,
                'hl': hl,
                'device': device,
                'num': num,
            }
            searches.append(search_params)

        body = {
            "name": batch_name,
            "enabled": True,
            "schedule_type": "manual",
            "priority": "normal",
            "notification_as_csv": True,
            "searches_type": "web",
            "searches": searches,
            "notification_email": notification_email
        }
        
        api_result = requests.post(f'https://api.valueserp.com/batches?api_key={API_KEY}', json=body)
        
        if api_result.status_code == 200:
            api_response = api_result.json()
            return api_response['batch']['id']
        else:
            st.error(f"Erreur lors de la création du batch '{batch_name}'. Code d'état : {api_result.status_code}")
            st.write(api_result.json())  # Affiche la réponse de l'API pour diagnostic
            return None

    def start_batch(batch_id):
        params = {
            'api_key': API_KEY
        }
        start_url = f'https://api.valueserp.com/batches/{batch_id}/start'
        api_result = requests.get(start_url, params=params)
        
        if api_result.status_code != 200:
            st.error(f"Échec du démarrage du batch {batch_id}. Code d'état : {api_result.status_code}")

    def list_batches(prefix):
        params = {
            'api_key': API_KEY
        }
        all_batches = []
        page = 1
        
        while True:
            response = requests.get(f'https://api.valueserp.com/batches?page={page}', params=params)
            if response.status_code == 200:
                batch_page = response.json().get('batches', [])
                if not batch_page:  # Si la page est vide, sortir de la boucle
                    break
                all_batches.extend(batch_page)
                page += 1
            else:
                st.error(f"Erreur lors de la récupération des batches: {response.status_code}")
                break
        
        filtered_batches = [batch for batch in all_batches if prefix.lower() in batch['name'].lower()]
        return filtered_batches

    def get_latest_result_set_id(batch_id):
        params = {
            'api_key': API_KEY
        }
        response = requests.get(f'https://api.valueserp.com/batches/{batch_id}/results', params=params)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                latest_result_set = results[0]  # Le plus récent est en premier
                return latest_result_set['id']
        else:
            st.error(f"Erreur lors de la récupération des Result Sets pour le batch {batch_id}: {response.status_code}")
        return None

    def get_result_set_data(batch_id, result_set_id):
        params = {
            'api_key': API_KEY
        }
        response = requests.get(f'https://api.valueserp.com/batches/{batch_id}/results/{result_set_id}', params=params)
        
        if response.status_code == 200:
            result_set = response.json().get('result', {})
            if 'download_links' in result_set:
                csv_link = result_set['download_links']['all_pages']
                csv_response = requests.get(csv_link)
                
                if csv_link.endswith('.json'):
                    return extract_serp_data(io.StringIO(csv_response.text))
                elif csv_link.endswith('.zip'):
                    with zipfile.ZipFile(io.BytesIO(csv_response.content)) as z:
                        file_names = z.namelist()
                        with z.open(file_names[0]) as f:
                            json_data = json.load(f)
                            df = extract_serp_data(json_data)
                            return df
                else:
                    st.write("Format de fichier inattendu.")
                    st.write(csv_response.text)
        else:
            st.error(f"Erreur lors de la récupération des données du Result Set {result_set_id}: {response.status_code}")
        return pd.DataFrame()

    def extract_serp_data(json_data):
        """Extraire les données SERP organiques du JSON et les structurer en DataFrame."""
        extracted_data = []
        for result in json_data:
            keyword = result.get('search', {}).get('q', '')
            organic_results = result.get('result', {}).get('organic_results', [])
            for org_result in organic_results:
                extracted_data.append({
                    'search.q': keyword,
                    'result.organic_results.position': org_result.get('position', ''),
                    'result.organic_results.title': org_result.get('title', ''),
                    'result.organic_results.link': org_result.get('link', ''),
                    'result.organic_results.domain': org_result.get('domain', '')
                })
        df = pd.DataFrame(extracted_data)
        # Reorder columns
        return df[['search.q', 'result.organic_results.position', 'result.organic_results.link', 'result.organic_results.title', 'result.organic_results.domain']]

    def split_keywords(keywords, batch_size=100):
        for i in range(0, len(keywords), batch_size):
            yield keywords[i:i + batch_size]

    def normalize_columns(df1, df2):
        """Aligne les colonnes de deux DataFrames et remplit les colonnes manquantes par NaN."""
        combined_columns = list(set(df1.columns).union(set(df2.columns)))
        df1 = df1.reindex(columns=combined_columns)
        df2 = df2.reindex(columns=combined_columns)
        return df1, df2

    if st.button("Lancer la recherche"):
        if keywords:
            all_results = pd.DataFrame()

            for keyword_batch in split_keywords(keywords):
                batch_name = f"{batch_prefix}_{uuid.uuid4()}"
                batch_id = create_batch_with_keywords(batch_name, keyword_batch)

                if batch_id:
                    start_batch(batch_id)

                    # Attendre un peu plus longtemps pour permettre la synchronisation
                    time.sleep(60)

            # Récupérer les résultats des batches existants
            batches = list_batches(batch_prefix)

            if batches:
                for batch in batches:
                    batch_id = batch['id']
                    result_set_id = get_latest_result_set_id(batch_id)
                    
                    if result_set_id:
                        result_data = get_result_set_data(batch_id, result_set_id)
                        if not result_data.empty:
                            if all_results.empty:
                                all_results = result_data
                            else:
                                all_results, result_data = normalize_columns(all_results, result_data)
                                all_results = pd.concat([all_results, result_data], ignore_index=True)

                            # Convertir les types de données pour compatibilité avec Arrow
                            all_results = all_results.convert_dtypes()

                if not all_results.empty:
                    @st.cache_data
                    def convert_df(df):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                        return output.getvalue()

                    excel_data = convert_df(all_results)
                    st.download_button(
                        label="Télécharger les résultats fusionnés",
                        data=excel_data,
                        file_name='results_fusionnes.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    st.write("Aucun résultat à fusionner.")
            else:
                st.write(f"Aucun batch trouvé avec le préfixe '{batch_prefix}'.")
        else:
            st.write("Veuillez entrer un préfixe de batch.")

if __name__ == '__main__':
    main()
