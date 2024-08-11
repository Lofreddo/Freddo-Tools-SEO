import requests
import pandas as pd
import io
import concurrent.futures
import streamlit as st
import uuid
import time

def main():
    # Titre de l'application
    st.title("Recherche de mots-clés avec ValueSERP en Batches")

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

    # Préfixe pour les Batchs
    batch_prefix = st.text_input("Entrez un préfixe pour les Batchs:")

    def create_batch(keyword_batch, batch_name):
        # Création du batch
        body = {
            "name": batch_name,
            "enabled": True,
            "schedule_type": "manual",
            "priority": "normal",
            "notification_as_csv": True
        }
        
        api_result = requests.post(f'https://api.valueserp.com/batches?api_key=81293DFA2CEF4FE49DB08E002D947143', json=body)
        api_response = api_result.json()
        batch_id = api_response['batch']['id']

        # Ajout des recherches dans le batch
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
            requests.post(f'https://api.valueserp.com/batches/{batch_id}/searches?api_key=81293DFA2CEF4FE49DB08E002D947143', json=search_params)

        # Démarrage du batch après l'avoir créé et rempli
        start_batch(batch_id)

        return batch_id

    def start_batch(batch_id):
        # Démarrage du batch
        params = {
            'api_key': '81293DFA2CEF4FE49DB08E002D947143'
        }
        start_url = f'https://api.valueserp.com/batches/{batch_id}/start'
        api_result = requests.get(start_url, params=params)
        
        if api_result.status_code == 200:
            st.write(f"Batch {batch_id} démarré avec succès.")
        else:
            st.error(f"Échec du démarrage du batch {batch_id}. Code d'état : {api_result.status_code}")

    def fetch_batch_results(batch_id):
        # Récupération des résultats une fois le batch terminé
        time.sleep(60)  # Temps d'attente pour que le batch se termine
        results_url = f'https://api.valueserp.com/batches/{batch_id}/results?api_key=81293DFA2CEF4FE49DB08E002D947143&output=csv'
        api_result = requests.get(results_url)
        
        if api_result.status_code == 200:
            result_df = pd.read_csv(io.StringIO(api_result.text), encoding='utf-8')
            return result_df
        else:
            st.error(f"La récupération des résultats pour le batch '{batch_id}' a échoué avec le code d'état {api_result.status_code}.")
            return None

    def split_keywords(keywords, batch_size=100):
        # Découpe la liste de mots-clés en sous-listes de taille batch_size
        for i in range(0, len(keywords), batch_size):
            yield keywords[i:i + batch_size]

    # Bouton pour lancer la recherche
    if st.button("Lancer la recherche"):
        if keywords:
            all_results = pd.DataFrame()

            for keyword_batch in split_keywords(keywords):
                # Création d'un batch avec un nom unique
                batch_name = f"{batch_prefix}_{uuid.uuid4()}"
                batch_id = create_batch(keyword_batch, batch_name)

                # Récupération des résultats du batch
                result_df = fetch_batch_results(batch_id)
                if result_df is not None:
                    all_results = pd.concat([all_results, result_df], ignore_index=True)

            # Nettoyer et réencoder les données
            all_results = all_results.applymap(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)

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
