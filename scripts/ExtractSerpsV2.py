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
            st.write(f"Batch {batch_name} créé avec succès avec les mots-clés.")
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
        
        if api_result.status_code == 200:
            st.write(f"Batch {batch_id} démarré avec succès.")
        else:
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
        
        st.write(f"Nombre total de batches récupérés : {len(all_batches)}")
        filtered_batches = [batch for batch in all_batches if prefix.lower() in batch['name'].lower()]
        st.write(f"Batches filtrés avec le préfixe '{prefix}' : {[batch['name'] for batch in filtered_batches]}")
        return filtered_batches

    def get_latest_result_set_id(batch_id):
        params = {
            'api_key': API_KEY
        }
        response = requests.get(f'https://api.valueserp.com/batches/{batch_id}/results', params=params)
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            st.write(f"Result Sets pour le batch {batch_id} : {results}")
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
            st.write(f"Détails du Result Set {result_set_id} : {result_set}")
            if 'download_links' in result_set:
                csv_link = result_set['download_links']['all_pages']
                csv_response = requests.get(csv_link)
                
                if csv_link.endswith('.json'):
                    st.write("Le fichier téléchargé est au format JSON.")
                    return pd.read_json(io.StringIO(csv_response.text))
                elif csv_link.endswith('.zip'):
                    st.write("Le fichier téléchargé est un fichier ZIP.")
                    with zipfile.ZipFile(io.BytesIO(csv_response.content)) as z:
                        file_names = z.namelist()
                        st.write(f"Fichiers dans l'archive ZIP : {file_names}")
                        with z.open(file_names[0]) as f:
                            st.write("Décompression et lecture du fichier JSON...")
                            json_data = json.load(f)
                            df = pd.json_normalize(json_data)  # Convertir JSON en DataFrame
                            st.write(f"DataFrame chargé avec succès : {df.shape[0]} lignes, {df.shape[1]} colonnes")
                            return df
                else:
                    st.write("Format de fichier inattendu.")
                    st.write(csv_response.text)
        else:
            st.error(f"Erreur lors de la récupération des données du Result Set {result_set_id}: {response.status_code}")
        return pd.DataFrame()

    def split_keywords(keywords, batch_size=100):
        for i in range(0, len(keywords), batch_size):
            yield keywords[i:i + batch_size]

    def normalize_columns(df1, df2):
        """Aligne les colonnes de deux DataFrames et remplit les colonnes manquantes par NaN."""
        combined_columns = list(set(df1.columns).union(set(df2.columns)))
        df1 = df1.reindex(columns=combined_columns)
        df2 = df2.reindex(columns=combined_columns)
        return df1, df2

    def convert_dtypes(df):
        """Convertit les colonnes du DataFrame à des types de données compatibles avec Arrow."""
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype('string')
            elif df[col].dtype == 'int64':
                df[col] = df[col].astype('float64')
        return df

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
                    st.write(f"Traitement du batch {batch['name']} avec ID: {batch_id}")
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
                            all_results = convert_dtypes(all_results)
                        else:
                            st.write(f"Aucun résultat disponible pour le Result Set {result_set_id} du batch {batch_id}")
                    else:
                        st.write(f"Pas de Result Set disponible pour le batch {batch_id}")

                if not all_results.empty:
                    st.dataframe(all_results)

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
