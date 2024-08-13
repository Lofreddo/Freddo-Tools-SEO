import requests
import pandas as pd
import io
import streamlit as st

API_KEY = '81293DFA2CEF4FE49DB08E002D947143'

def main():
    st.title("Recherche de mots-clés avec ValueSERP en Batches")

    batch_prefix = st.text_input("Entrez un préfixe pour les Batchs:")

    if st.button("Récupérer et fusionner les résultats"):
        if batch_prefix:
            # Étape 1: Lister les Batches
            batches = list_batches(batch_prefix)

            if batches:
                all_results = pd.DataFrame()

                # Étape 2 à 4: Récupérer les informations et données de chaque batch
                for batch in batches:
                    batch_id = batch['id']
                    st.write(f"Traitement du batch {batch['name']} avec ID: {batch_id}")
                    result_set_id = get_latest_result_set_id(batch_id)
                    
                    if result_set_id:
                        result_data = get_result_set_data(batch_id, result_set_id)
                        if not result_data.empty:
                            all_results = pd.concat([all_results, result_data], ignore_index=True)
                        else:
                            st.write(f"Aucun résultat disponible pour le Result Set {result_set_id} du batch {batch_id}")
                    else:
                        st.write(f"Pas de Result Set disponible pour le batch {batch_id}")

                # Étape 5: Fusionner et télécharger
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

def list_batches(prefix):
    params = {
        'api_key': API_KEY
    }
    response = requests.get(f'https://api.valueserp.com/batches', params=params)
    
    if response.status_code == 200:
        all_batches = response.json().get('batches', [])
        filtered_batches = [batch for batch in all_batches if batch['name'].startswith(prefix)]
        return filtered_batches
    else:
        st.error(f"Erreur lors de la récupération des batches: {response.status_code}")
        return []

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
            if csv_response.status_code == 200:
                return pd.read_csv(io.StringIO(csv_response.text), encoding='utf-8')
    else:
        st.error(f"Erreur lors de la récupération des données du Result Set {result_set_id}: {response.status_code}")
    return pd.DataFrame()

if __name__ == '__main__':
    main()
