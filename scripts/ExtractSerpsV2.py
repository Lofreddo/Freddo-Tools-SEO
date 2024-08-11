import requests
import pandas as pd
import io
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

    # Adresse email pour l'envoi des notifications
    notification_email = st.text_input("Entrez une adresse email pour les notifications:")

    def create_batch_with_keywords(batch_name, keyword_batch):
        # Création du batch avec les mots-clés ajoutés directement
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
            "searches_type": "web",  # Définit explicitement le type de recherche
            "searches": searches,  # Ajoute les recherches directement dans la création du batch
            "notification_email": notification_email  # Ajoute l'email pour les notifications
        }
        
        api_result = requests.post(f'https://api.valueserp.com/batches?api_key=81293DFA2CEF4FE49DB08E002D947143', json=body)
        api_response = api_result.json()
        if api_result.status_code == 200:
            st.write(f"Batch {batch_name} créé avec succès avec les mots-clés.")
        else:
            st.error(f"Erreur lors de la création du batch '{batch_name}'. Code d'état : {api_result.status_code}")
        return api_response['batch']['id']

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

    def list_batch_results(batch_id):
        # Lister les jeux de résultats pour un batch
        params = {
            'api_key': '81293DFA2CEF4FE49DB08E002D947143'
        }
        results_url = f'https://api.valueserp.com/batches/{batch_id}/results'
        for attempt in range(10):  # Essayer jusqu'à 10 fois
            api_result = requests.get(results_url, params=params)
            if api_result.status_code == 200:
                results = api_result.json().get("results", [])
                if results:
                    st.write(f"Résultats trouvés pour le batch {batch_id} à la tentative {attempt + 1}")
                    return results
                else:
                    st.write(f"Aucun résultat disponible pour le batch {batch_id}, tentative {attempt + 1}")
            else:
                st.error(f"Erreur lors de la récupération des résultats pour le batch {batch_id}. Code d'état : {api_result.status_code}")
            time.sleep(60)  # Attendre une minute avant de réessayer
        return []

    def fetch_result_set(result_set_id):
        # Récupérer les données pour un jeu de résultats spécifique
        result_url = f'https://api.valueserp.com/result_sets/{result_set_id}?api_key=81293DFA2CEF4FE49DB08E002D947143&output=csv'
        api_result = requests.get(result_url)
        if api_result.status_code == 200 and api_result.text.strip():
            result_df = pd.read_csv(io.StringIO(api_result.text), encoding='utf-8')
            return result_df
        else:
            st.error(f"Échec de la récupération du jeu de résultats '{result_set_id}'.")
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
                # Création d'un batch avec un nom unique et ajout des mots-clés directement
                batch_name = f"{batch_prefix}_{uuid.uuid4()}"
                batch_id = create_batch_with_keywords(batch_name, keyword_batch)

                # Démarrage du batch
                start_batch(batch_id)

                # Lister les résultats disponibles pour ce batch
                result_sets = list_batch_results(batch_id)

                for result_set in result_sets:
                    result_set_id = result_set.get("id")
                    if result_set_id:
                        result_df = fetch_result_set(result_set_id)
                        if result_df is not None and not result_df.empty:
                            all_results = pd.concat([all_results, result_df], ignore_index=True)

            if not all_results.empty:
                # Nettoyer et réencoder les données
                all_results = all_results.applymap(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)

                # Affiche les résultats dans Streamlit
                st.dataframe(all_results)

                # Ajoutez un bouton pour télécharger le fichier Excel fusionné
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
