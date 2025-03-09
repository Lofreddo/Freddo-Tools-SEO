import streamlit as st
import pandas as pd
import requests
import json
import datetime
import io
import concurrent.futures
import gc
import re  # Pour l'extraction de la date

def check_domain_expiration():
    st.title('Domain Expiration Checker')

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

            for domain in domains:
                domain = domain.strip()
                # Suppression du préfixe "www." si présent
                if domain.startswith("www."):
                    domain = domain[4:]
                # Extraction personnalisée du domaine :
                # Pour un domaine se terminant par ".co.uk", on conserve les trois derniers éléments
                if domain.endswith(".co.uk"):
                    parts = domain.split('.')
                    if len(parts) >= 3:
                        domain = '.'.join(parts[-3:])
                # Pour tous les autres domaines, on conserve les deux derniers éléments
                else:
                    parts = domain.split('.')
                    if len(parts) >= 2:
                        domain = '.'.join(parts[-2:])
                clean_domains.append(domain)

            unique_domains = list(set(clean_domains))

            # Ajustement dynamique du nombre de threads
            max_workers = min(20, len(unique_domains) // 10 + 1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(perform_single_domain_check, unique_domains))

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

            # Collecte des ordures pour libérer la mémoire
            gc.collect()

def perform_single_domain_check(domain):
    try:
        server = "https://rdap.org"
        response = requests.get(f"{server}/domain/{domain}", timeout=10)
        response.raise_for_status()
        rdap = json.loads(response.content)

        expiration_date = None
        # Parcours des événements pour trouver la date d'expiration
        for event in rdap.get("events", []):
            if event.get("eventAction") == "expiration":
                event_date = event.get("eventDate", "")
                # Recherche d'une chaîne de 10 caractères sous forme yyyy-mm-dd ou dd-mm-yyyy/mm-dd-yyyy
                match = re.search(r'((?:\d{4}-\d{2}-\d{2})|(?:\d{2}-\d{2}-\d{4}))', event_date)
                if match:
                    date_str = match.group(1)
                    parts = date_str.split('-')
                    # Si le premier segment a 4 chiffres, c'est le format ISO yyyy-mm-dd
                    if len(parts[0]) == 4:
                        expiration_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        # Ici on a un format 2-2-4, soit dd-mm-yyyy ou mm-dd-yyyy.
                        a, b, year = parts
                        a_int = int(a)
                        b_int = int(b)
                        # Si le premier nombre est supérieur à 12, c'est forcément le jour.
                        if a_int > 12 and b_int <= 12:
                            expiration_date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
                        # Si le deuxième nombre est supérieur à 12, c'est le jour dans un format mm-dd-yyyy.
                        elif b_int > 12 and a_int <= 12:
                            expiration_date = datetime.datetime.strptime(date_str, "%m-%d-%Y")
                        else:
                            # En cas d'ambiguïté (par exemple 05-06-2025), on choisit par défaut dd-mm-yyyy.
                            expiration_date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
                break

        if expiration_date:
            now = datetime.datetime.now()
            days_left = (expiration_date - now).days
            # Normalisation de la date au format yyyy-mm-dd
            formatted_date = expiration_date.strftime("%Y-%m-%d")
            status = f"Expires in {days_left} days ({formatted_date})"
            if days_left < 0:
                status += " (Expired)"
            elif days_left <= 30:
                status += " (Expiring Soon)"
        else:
            status = "Unknown Expiration Date"

        return (domain, status)

    except requests.exceptions.RequestException as e:
        return (domain, f"HTTP Error: {e}")
    except json.JSONDecodeError:
        return (domain, "Error: Unable to decode JSON response")
    except ValueError as e:
        return (domain, f"Error: {e}")
    except Exception as e:
        return (domain, f"Error: {e}")

def main():
    check_domain_expiration()

if __name__ == "__main__":
    main()
