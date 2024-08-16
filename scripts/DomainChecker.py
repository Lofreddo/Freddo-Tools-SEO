import streamlit as st
import pandas as pd
import requests
import json
import datetime
import io
from tldextract import extract

def check_domain_expiration():
    st.title('Domain Expiration Checker')

    input_option = st.radio("Choose input method:", ("Upload an Excel file", "Enter domains manually"))
    domains = []

    if input_option == "Upload an Excel file":
        uploaded_file = st.file_uploader("Upload your Excel file with domains", type=["xlsx"])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                column_name = st.selectbox("Select the column with domains", df.columns.tolist())
                domains = df[column_name].dropna().tolist()
            except Exception as e:
                st.error(f"Error reading the Excel file: {e}")
                return
    else:
        text_input = st.text_area("Enter domains (one per line):")
        if text_input:
            domains = text_input.splitlines()

    if domains and st.button('Check Expiration'):
        with st.spinner('Checking domain expiration...'):
            clean_domains = []

            for domain in domains:
                domain = domain.lstrip('www.')
                extracted_domain = extract(domain)
                domain = f"{extracted_domain.domain}.{extracted_domain.suffix}"
                clean_domains.append(domain)

            unique_domains = list(set(clean_domains))

            results = process_in_batches(unique_domains, batch_size=100)

            results_df = pd.DataFrame(results, columns=['Domain', 'Status'])
            st.dataframe(results_df)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False)

            st.download_button(
                label="Download Results",
                data=buffer.getvalue(),
                file_name="domain_expiration_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def process_in_batches(domains, batch_size=100):
    results = []
    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        batch_results = [perform_single_domain_check(domain) for domain in batch]
        results.extend(batch_results)
    return results

def perform_single_domain_check(domain):
    try:
        server = "https://rdap.org"
        response = requests.get(f"{server}/domain/{domain}", timeout=10)
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

        return (domain, status)

    except requests.exceptions.RequestException as e:
        return (domain, f"Error: {e}")
    except Exception as e:
        return (domain, f"Error: {e}")

def main():
    check_domain_expiration()

if __name__ == "__main__":
    main()
