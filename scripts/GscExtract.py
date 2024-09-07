import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime
import pandas as pd

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Fonction d'authentification à l'API Google Search Console via OAuth
def authenticate_gsc():
    creds = None

    # Vérifie si un token existe déjà pour éviter de demander une nouvelle authentification
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Si pas de token ou token invalide, redirige vers l'authentification OAuth
    if not creds or not creds.valid:
        flow = Flow.from_client_secrets_file(
            'client_secrets.json',  # Remplace par ton fichier client_secret.json
            scopes=SCOPES
        )
        flow.redirect_uri = 'http://localhost:8501'  # L'URL où Streamlit est hébergé

        auth_url, _ = flow.authorization_url(prompt='consent')
        st.write(f"[Cliquez ici pour vous authentifier avec Google]({auth_url})")
        code = st.text_input("Entrez le code d'autorisation ici")

        if code:
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials

                # Sauvegarder les credentials pour une future utilisation
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                st.error(f"Erreur d'authentification : {str(e)}")

    if creds:
        return build('webmasters', 'v3', credentials=creds)
    else:
        return None

# Fonction pour sélectionner une propriété Google Search Console
def select_property(service):
    site_list = service.sites().list().execute()
    sites = [site['siteUrl'] for site in site_list['siteEntry']]
    selected_site = st.selectbox("Sélectionner une propriété", sites)
    return selected_site

# Sélection des dates
def select_dates():
    start_date = st.date_input('Sélectionnez la date de début', datetime.now())
    end_date = st.date_input('Sélectionnez la date de fin', datetime.now())
    return start_date, end_date

# Sélection du type de données à récupérer (Page, Query, Both)
def select_data_type():
    options = ['Page', 'Query', 'Both']
    selected_option = st.radio('Sélectionnez les données à récupérer', options)
    return selected_option

# Ajouter des filtres personnalisés
def add_filters():
    filters = []
    st.write("Ajouter des filtres (facultatif) :")
    filter_criteria = st.selectbox('Critère', ['Query', 'Page'])
    condition = st.selectbox('Condition', ['contains', 'do not contains'])
    filter_value = st.text_input('Valeur')
    
    if st.button('Ajouter le filtre'):
        filters.append((filter_criteria, condition, filter_value))
    
    st.write(f'Filtres actuels : {filters}')
    return filters

# Récupération des données via l'API Google Search Console
def fetch_data(service, site_url, start_date, end_date, data_type, filters):
    request = {
        'startDate': start_date.strftime('%Y-%m-%d'),
        'endDate': end_date.strftime('%Y-%m-%d'),
        'dimensions': [data_type.lower()] if data_type != 'Both' else ['page', 'query'],
    }
    
    if filters:
        request['dimensionFilterGroups'] = {
            'filters': [
                {
                    'dimension': f[0].lower(),
                    'operator': 'contains' if f[1] == 'contains' else 'notContains',
                    'expression': f[2]
                } for f in filters
            ]
        }
    
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    return response

# Télécharger les données au format Excel
def download_data(data):
    if 'rows' in data:
        df = pd.DataFrame(data['rows'])
        df.columns = ['Position', 'Clicks', 'Impressions', 'CTR'] + [dim for dim in data['dimensionHeaders']]
        st.write(df)  # Affiche les données dans Streamlit
        
        # Exporter au format Excel
        excel_data = df.to_excel(index=False)
        st.download_button(
            label="Télécharger les données au format Excel",
            data=excel_data,
            file_name='gsc_data.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        st.write("Aucune donnée disponible pour les critères sélectionnés.")

# Fonction principale de l'application
def main():
    st.title('Récupération de données Google Search Console')

    # Authentification
    service = authenticate_gsc()

    # Si authentification réussie, continuer
    if service:
        selected_site = select_property(service)
        
        start_date, end_date = select_dates()
        data_type = select_data_type()
        filters = add_filters()
        
        if st.button('Lancer la récupération des données'):
            data = fetch_data(service, selected_site, start_date, end_date, data_type, filters)
            download_data(data)
