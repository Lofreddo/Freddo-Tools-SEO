import streamlit as st
import requests
import pandas as pd

def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    response = requests.get(url)
    return response.status_code == 200

def check_sitemap(domain):
    sitemaps = ["sitemap.xml", "sitemap_index.xml", "index_sitemap.xml"]
    for sitemap in sitemaps:
        url = f"{domain}/{sitemap}"
        response = requests.get(url)
        if response.status_code == 200:
            return True
    return False

def main():
    st.title("Site Analyzer")

    domain = st.text_input("Entrez l'URL du domaine (incluez http:// ou https://)")

    if st.button("Analyser"):
        if domain:
            # Vérifier robots.txt
            robots_exists = check_robots_txt(domain)
            st.write(f"Robots.txt exists: {'Oui' if robots_exists else 'Non'}")

            # Vérifier sitemap
            sitemap_exists = check_sitemap(domain)
            st.write(f"Sitemap exists: {'Oui' if sitemap_exists else 'Non'}")

            # Vous pouvez ajouter ici d'autres analyses et stocker les résultats dans un DataFrame
            results = {
                "Critère": ["Robots.txt", "Sitemap"],
                "Présence": ["Oui" if robots_exists else "Non", "Oui" if sitemap_exists else "Non"]
            }
            df = pd.DataFrame(results)
            st.dataframe(df)

            # Exporter les résultats au format Excel
            if st.button("Exporter en Excel"):
                df.to_excel("site_analysis_results.xlsx", index=False)
                st.write("Fichier exporté avec succès.")
        else:
            st.error("Veuillez entrer une URL valide.")

# Le script peut être ajouté à votre configuration principale
