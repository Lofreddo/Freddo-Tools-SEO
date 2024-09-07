import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pandas as pd
import os
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Fonction d'authentification à l'API Google Search Console
def authenticate_gsc():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('webmasters', 'v3', credentials=creds)

# Sélectionner la propriété Google Search Console
def select_property(service):
    site_list = service.sites().list().execute()
    sites = [site['siteUrl'] for site in site_list['siteEntry']]
    selected_site = st.selectbox("Sélectionner une propriété", sites)
    return selected_site

# Sélectionner la plage de dates
def select_dates():
    start_date = st.date_input('Sélectionnez la date de début', datetime.now())
    end_date = st.date_input('Sélectionnez la date de fin', datetime.now())
    return start_date, end_date

# Sélectionner les types de données (Page, Query ou les deux)
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

# Récupération des données depuis Google Search Console
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

# Télécharger les données en fichier Excel
def download_data(data):
    if 'rows' in data:
        df = pd.DataFrame(data['rows'])
        df.columns = ['Position', 'Clicks', 'Impressions', 'CTR'] + [dim for dim in data['dimensionHeaders']]
        st.write(df)  # Affiche les données dans l'interface Streamlit
        
        # Exportation au format Excel
        excel_data = df.to_excel(index=False)
        st.download_button(
            label="Télécharger les données au format Excel",
            data=excel_data,
            file_name='gsc_data.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        st.write("Aucune donnée disponible pour les critères sélectionnés.")

# Fonction pour exécuter tout le script Google Search Console
def run_gsc_script():
    st.title('Récupération de données Google Search Console')

    service = authenticate_gsc()
    selected_site = select_property(service)
    
    start_date, end_date = select_dates()
    data_type = select_data_type()
    filters = add_filters()
    
    if st.button('Lancer la récupération des données'):
        data = fetch_data(service, selected_site, start_date, end_date, data_type, filters)
        download_data(data)
