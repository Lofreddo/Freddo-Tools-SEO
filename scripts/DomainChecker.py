import streamlit as st
import pandas as pd
import pythonwhois
import time
from datetime import datetime, timedelta
from tldextract import extract

def check_domain_expiration():
    st.title('Domain Expiration Checker')

    uploaded_file = st.file_uploader("Upload your Excel file with domains", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Columns found in your file:", df.columns.tolist())

        column_name = st.selectbox("Select the column with domains", df.columns.tolist())

        if st.button('Check Expiration'):
            with st.spinner('Checking domain expiration...'):
                domains = df[column_name].dropna().tolist()

                # Retirer le préfixe "www." des domaines et traiter les sous-domaines
                clean_domains = []
                for domain in domains:
                    domain = domain.lstrip('www.')
                    
                    # Extraire le domaine principal (enlever le sous-domaine)
                    extracted_domain = extract(domain)
                    domain = f"{extracted_domain.domain}.{extracted_domain.suffix}"
                    
                    clean_domains.append(domain)

                # Supprimer les doublons après tout le traitement
                unique_domains = list(set(clean_domains))

                results = perform_domain_expiration_check(unique_domains)

                # Convertir les résultats en DataFrame pour exportation
                results_df = pd.DataFrame(results, columns=['Domain', 'Status'])
                st.write(results_df)

                # Télécharger les résultats
                result_file = results_df.to_excel(index=False, engine='xlsxwriter')
                st.download_button(label="Download Results",
                                   data=result_file,
                                   file_name="domain_expiration_results.xlsx")

def perform_domain_expiration_check(domains):
    results = []
    soon_expire_threshold = timedelta(days=30)  # Notifier si le domaine expire dans moins de 30 jours

    for domain in domains:
        try:
            details = pythonwhois.get_whois(domain)
            expiration_date = details.get('expiration_date')

            if expiration_date:
                expiration_date = expiration_date[0] if isinstance(expiration_date, list) else expiration_date
                status = expiration_date.strftime('%Y-%m-%d')
                if expiration_date < datetime.now():
                    status += " (Expired)"
                elif expiration_date < datetime.now() + soon_expire_threshold:
                    status += " (Expiring Soon)"
            else:
                status = "Unknown Expiration Date"

            results.append((domain, status))
            time.sleep(2)  # Pause de 2 secondes pour éviter de surcharger les serveurs WHOIS

        except Exception as e:
            results.append((domain, f"Error: {e}"))

    return results

def main():
    check_domain_expiration()

if __name__ == "__main__":
    main()
