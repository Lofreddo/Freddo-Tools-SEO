import requests
import pandas as pd
import io
import streamlit as st
import uuid
import time

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
        
        api_result = requests.post(f'https://api.valueserp.com/batches?api_key=81293DFA2CEF4FE49DB08E002D947143', json=body)
        
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
            'api_key': '81293DFA2CEF4FE49DB08E002D947143'
        }
        start_url = f'https://api.valueserp.com/batches/{batch_id}/start'
        api_result = requests.get(start_url, params=params)
        
        if api_result.status_code == 200:
            st.write(f"Batch {batch_id} démarré avec succès.")
        else:
            st.error(f"Échec du démarrage du batch {batch_id}. Code d'état : {api_result.status_code}")

    def get_batch_csv_links(batch_id):
        params = {
            'api_key': '81293DFA2CEF4FE49DB08E002D947143'
        }
        csv_url = f'https://api.valueserp.com/batches/{batch_id}/results/{batch_id}/csv'
        api_result = requests.get(csv_url, params=params)
        
        if api_result.status_code == 200:
            csv_info = api_result.json()
            download_links = csv_info.get('result', {}).get('download_links', {}).get('all_pages', [])
            return download_links
        else:
            st.error(f"Erreur lors de la récupération des liens de téléchargement CSV pour le batch {batch_id}. Code d'état : {api_result.status_code}")
            return []

    def download_and_merge_results(batch_id):
        all_results = pd.DataFrame()
        csv_links = get_batch_csv_links(batch_id)

        for link in csv_links:
            csv_result = requests.get(link)
            if csv_result.status_code == 200:
                result_df = pd.read_csv(io.StringIO(csv_result.text), encoding='utf-8')
                all_results = pd.concat([all_results, result_df], ignore_index=True)
            else:
                st.error(f"Erreur lors de la récupération du fichier CSV depuis '{link}'. Code d'état : {csv_result.status_code}")
        
        return all_results

    def split_keywords(keywords, batch_size=100):
        for i in range(0, len(keywords), batch_size):
            yield keywords[i:i + batch_size]

    if st.button("Lancer la recherche"):
        if keywords:
            all_results = pd.DataFrame()

            for keyword_batch in split_keywords(keywords):
                batch_name = f"{batch_prefix}_{uuid.uuid4()}"
                batch_id = create_batch_with_keywords(batch_name, keyword_batch)

                if batch_id:
                    start_batch(batch_id)

                    # Attendre un peu plus longtemps avant de vérifier les résultats
                    time.sleep(120)

                    batch_results = download_and_merge_results(batch_id)
                    all_results = pd.concat([all_results, batch_results], ignore_index=True)

            if not all_results.empty:
                st.dataframe(all_results)

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
                        label="Télécharger les résultats fusionnés",
                        data=excel_data,
                        file_name='results_fusionnes.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
            else:
                st.error("Aucun résultat à fusionner. Vérifiez les Batchs ou réessayez plus tard.")
        else:
            st.error("Veuillez entrer au moins un mot-clé.")

if __name__ == '__main__':
    main()
