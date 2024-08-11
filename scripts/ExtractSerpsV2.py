import requests
import pandas as pd
import io
import time
import uuid
import streamlit as st

# Étape 1 : Création d'un batch avec les mots-clés
def create_batch_with_keywords(name, keywords, google_domain, device, num, gl, hl, location, notification_email):
    body = {
        "name": name,
        "enabled": True,
        "schedule_type": "manual",
        "priority": "normal",
        "notification_email": notification_email,
        "notification_as_csv": True,
        "keywords": [
            {
                "q": keyword,
                "location": location,
                "google_domain": google_domain,
                "gl": gl,
                "hl": hl,
                "device": device,
                "num": num
            } for keyword in keywords
        ]
    }
    
    params = {
        'api_key': '81293DFA2CEF4FE49DB08E002D947143'
    }
    
    api_result = requests.post('https://api.valueserp.com/batches', json=body, params=params)
    
    if api_result.status_code == 200:
        api_response = api_result.json()
        batch_id = api_response['batch']['id']
        st.write(f"Batch {name} créé avec succès avec les mots-clés.")
        return batch_id
    else:
        st.error(f"Erreur lors de la création du batch '{name}'. Code d'état : {api_result.status_code}")
        return None

# Étape 2 : Démarrage du batch
def start_batch(batch_id):
    params = {
        'api_key': '81293DFA2CEF4FE49DB08E002D947143'
    }
    
    api_result = requests.get(f'https://api.valueserp.com/batches/{batch_id}/start', params=params)
    
    if api_result.status_code == 200:
        st.write(f"Batch {batch_id} démarré avec succès.")
    else:
        st.error(f"Erreur lors du démarrage du batch {batch_id}. Code d'état : {api_result.status_code}")

# Étape 3 : Récupération de la liste des sets de résultats
def list_result_sets(batch_id, max_attempts=10, delay=60):
    params = {
        'api_key': '81293DFA2CEF4FE49DB08E002D947143'
    }
    results_url = f'https://api.valueserp.com/batches/{batch_id}/results'
    
    for attempt in range(max_attempts):
        st.write(f"Vérification des résultats pour le batch {batch_id}, tentative {attempt + 1}")
        api_result = requests.get(results_url, params=params)
        
        if api_result.status_code == 200:
            results = api_result.json().get("results", [])
            if results:
                st.write(f"Résultats trouvés pour le batch {batch_id} à la tentative {attempt + 1}")
                return results
            else:
                st.write(f"Aucun résultat disponible pour le batch {batch_id} à la tentative {attempt + 1}")
        else:
            st.error(f"Erreur lors de la récupération des résultats pour le batch {batch_id}. Code d'état : {api_result.status_code}")
        
        time.sleep(delay)
    
    st.error(f"Échec de la récupération des résultats pour le batch {batch_id} après {max_attempts} tentatives.")
    return []

# Étape 4 : Récupération des données d'un set de résultats
def get_result_set_data(batch_id, result_set_id):
    params = {
        'api_key': '81293DFA2CEF4FE49DB08E002D947143'
    }
    result_url = f'https://api.valueserp.com/batches/{batch_id}/results/{result_set_id}/data'
    api_result = requests.get(result_url, params=params)
    
    if api_result.status_code == 200:
        return api_result.text
    else:
        st.error(f"Erreur lors de la récupération des données du jeu de résultats '{result_set_id}'. Code d'état : {api_result.status_code}")
        return None

# Étape 5 : Fonction principale pour exécuter le processus
def main():
    st.title("Recherche de mots-clés avec ValueSERP en Batches")

    # Entrée des mots-clés
    keywords_input = st.text_area("Entrez vos mots-clés, un par ligne:")

    # Conversion des mots-clés en liste
    keywords = keywords_input.strip().split('\n')

    # Sélection des options
    google_domain = st.selectbox("Sélectionnez le domaine Google:", ["google.fr", "google.com", "google.co.uk", "google.de", "google.es"])
    device = st.selectbox("Sélectionnez le dispositif:", ["desktop", "mobile"])
    num = st.selectbox("Sélectionnez le nombre de résultats:", ["10", "20", "30", "40", "50", "100"])
    gl = st.selectbox("Sélectionnez le pays:", ["fr", "es", "de", "en"])
    hl = st.selectbox("Sélectionnez la langue:", ["fr", "es", "de", "en"])
    location = st.selectbox("Sélectionnez la location:", ["France", "United Kingdom", "United States", "Spain", "Germany"])
    batch_prefix = st.text_input("Entrez un préfixe pour les Batchs:", "batch_prefix")
    notification_email = st.text_input("Entrez une adresse email pour les notifications:", "email@example.com")

    if st.button("Lancer la recherche"):
        if keywords:
            # Diviser la liste des mots-clés en lots de 100
            keyword_batches = [keywords[i:i + 100] for i in range(0, len(keywords), 100)]
            
            all_results = pd.DataFrame()

            for keyword_batch in keyword_batches:
                batch_name = f"{batch_prefix}_{uuid.uuid4()}"
                batch_id = create_batch_with_keywords(batch_name, keyword_batch, google_domain, device, num, gl, hl, location, notification_email)

                if batch_id:
                    start_batch(batch_id)
                    result_sets = list_result_sets(batch_id)

                    for result_set in result_sets:
                        result_set_id = result_set['id']
                        result_data = get_result_set_data(batch_id, result_set_id)
                        
                        if result_data:
                            result_df = pd.read_csv(io.StringIO(result_data), encoding='utf-8')
                            all_results = pd.concat([all_results, result_df], ignore_index=True)

            if not all_results.empty:
                @st.cache_data
                def convert_df(df):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    return output.getvalue()

                excel_data = convert_df(all_results)
                
                st.download_button(
                    label="Télécharger les résultats",
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
