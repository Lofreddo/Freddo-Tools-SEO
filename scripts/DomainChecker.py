import streamlit as st
import pandas as pd
import whois
import time
import concurrent.futures
from datetime import datetime, timedelta
from tldextract import extract

def check_domain_expiration():
    st.title('Domain Expiration Checker')

    # Option pour choisir entre fichier d'import et champ de texte libre
    input_option = st.radio("Choose input method:", ("Upload an Excel file", "Enter domains manually"))

    domains = []

    if input_option == "Upload an Excel file":
        uploaded_file = st.file_uploader("Upload your Excel file with domains", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            column_name = st.selectbox("Select the column with domains", df.columns.tolist())
            domains = df[column_name].dropna().tolist()
    else:
        text_input = st.text_area("Enter domains (one per line):")
        if text_input:
            domains = text_input.splitlines()

    if domains and st.button('Check Expiration'):
        with st.spinner('Checking domain expiration...'):
            clean_domains = []

            # Retirer le préfixe "www." des domaines et traiter les sous-domaines
            for domain in domains:
                domain = domain.lstrip('www.')
                extracted_domain = extract(domain)
                domain = f"{extracted_domain.domain}.{extracted_domain.suffix}"
                clean_domains.append(domain)

            # Supprimer les doublons après tout le traitement
            unique_domains = list(set(clean_domains))

            # Utilisation d'un ThreadPoolExecutor pour paralléliser les requêtes WHOIS
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(perform_single_domain_check, unique_domains))

            # Convertir les résultats en DataFrame pour exportation
            results_df = pd.DataFrame(results, columns=['Domain', 'Status'])
            st.dataframe(results_df)  # Affichage propre des résultats

            # Télécharger les résultats
            result_file = results_df.to_excel(index=False, engine='xlsxwriter')
            st.download_button(label="Download Results",
                               data=result_file,
                               file_name="domain_expiration_results.xlsx")

def perform_single_domain_check(domain):
    soon_expire_threshold = timedelta(days=30)  # Notifier si le domaine expire dans moins de 30 jours
    try:
        details = whois.whois(domain)
        expiration_date = details.expiration_date

        if expiration_date:
            expiration_date = expiration_date[0] if isinstance(expiration_date, list) else expiration_date
            status = expiration_date.strftime('%Y-%m-%d')
            if expiration_date < datetime.now():
                status += " (Expired)"
            elif expiration_date < datetime.now() + soon_expire_threshold:
                status += " (Expiring Soon)"
        else:
            status = "Unknown Expiration Date"

        return (domain, status)

    except Exception as e:
        return (domain, f"Error: {e}")

def main():
    check_domain_expiration()

if __name__ == "__main__":
    main()
