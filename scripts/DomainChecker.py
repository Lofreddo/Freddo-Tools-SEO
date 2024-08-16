import requests
import json
import datetime
import time
import logging
import streamlit as st

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def perform_single_domain_check(domain, retry_count=3):
    try:
        server = "https://rdap.org"
        response = requests.get(f"{server}/domain/{domain}", timeout=10)

        # Gérer les limitations de trafic
        if response.status_code == 429:
            logging.warning(f"Rate limit exceeded for domain {domain}. Retrying...")
            time.sleep(10)  # Attendre 10 secondes avant de réessayer
            if retry_count > 0:
                return perform_single_domain_check(domain, retry_count - 1)
            else:
                return (domain, "Error: Too many requests, exceeded retry limit")

        response.raise_for_status()
        rdap = response.json()

        expiration_date = None
        for event in rdap.get("events", []):
            if event["eventAction"] == "expiration":
                expiration_date = datetime.datetime.strptime(event["eventDate"], "%Y-%m-%dT%H:%M:%SZ")
                break

        if expiration_date:
            now = datetime.datetime.now()
            days_left = (expiration_date - now).days
            status = f"Expires in {days_left} days ({expiration_date.strftime('%Y-%m-%d')})"
            if days_left < 0:
                status += " (Expired)"
            elif days_left <= 30:
                status += " (Expiring Soon)"
        else:
            status = "Unknown Expiration Date"

        # Ajout d'un délai pour éviter la surcharge du serveur RDAP
        time.sleep(1)

        return (domain, status)

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for domain {domain}: {e}")
        return (domain, f"Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error for domain {domain}: {e}")
        return (domain, f"Error: {e}")

def check_domain_expiration():
    st.title('Domain Expiration Checker')

    input_option = st.radio("Choose input method:", ("Upload an Excel file", "Enter domains manually"))

    if input_option == "Upload an Excel file":
        uploaded_file = st.file_uploader("Upload your Excel file with domains", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            column_name = st.selectbox("Select the column with domains", df.columns.tolist())
            domains = df[column_name].dropna().tolist()
    else:
        domains_input = st.text_area("Enter domains, one per line")
        domains = domains_input.strip().splitlines()

    if domains and st.button('Check Expiration'):
        with st.spinner('Checking domain expiration...'):
            results = [perform_single_domain_check(domain) for domain in domains]

            # Convertir les résultats en DataFrame pour exportation
            results_df = pd.DataFrame(results, columns=['Domain', 'Status'])
            st.write(results_df)

            # Télécharger les résultats
            @st.cache_data
            def convert_df(df):
                return df.to_excel(index=False, engine='xlsxwriter')

            excel_data = convert_df(results_df)
            st.download_button(label="Download Results", data=excel_data, file_name="domain_expiration_results.xlsx")

def main():
    check_domain_expiration()

if __name__ == "__main__":
    main()
