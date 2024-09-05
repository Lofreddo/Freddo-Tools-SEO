import streamlit as st
from bs4 import BeautifulSoup
import re
import pandas as pd
import requests
from urllib.parse import urljoin

def extract_css_classes(css_content):
    """Extraire toutes les classes CSS du contenu CSS"""
    class_regex = r'\.([a-zA-Z0-9_-]+)\s*\{'
    return re.findall(class_regex, css_content)

def extract_html_classes(html_content):
    """Extraire toutes les classes HTML du contenu HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    classes_in_html = []
    elements_with_classes = []

    for element in soup.find_all(True):  # Trouver toutes les balises
        class_list = element.get('class', [])
        if class_list:
            classes_in_html.extend(class_list)
            elements_with_classes.append((element, class_list))
    
    return set(classes_in_html), elements_with_classes

def get_css_from_url(html_url):
    """Télécharger le contenu HTML et récupérer tous les fichiers CSS liés"""
    response = requests.get(html_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Trouver tous les liens vers les fichiers CSS
    css_files = []
    for link in soup.find_all('link', rel='stylesheet'):
        css_url = link.get('href')
        full_css_url = urljoin(html_url, css_url)
        css_response = requests.get(full_css_url)
        if css_response.status_code == 200:
            css_files.append((full_css_url, css_response.text))
    
    return response.text, css_files

def detect_unused_css(css_files, html_content):
    """Détecter les classes CSS non utilisées dans le fichier HTML"""
    html_classes, elements_with_classes = extract_html_classes(html_content)

    unused_classes = []
    for css_url, css_content in css_files:
        css_classes = set(extract_css_classes(css_content))
        unused_in_file = css_classes - html_classes
        for unused_class in unused_in_file:
            unused_classes.append((unused_class, css_url))
    
    return unused_classes

def generate_unused_report_excel(unused_classes):
    """Générer un fichier Excel listant les classes CSS inutilisées et leur URL d'origine"""
    if unused_classes:
        # Créer un DataFrame avec les classes CSS inutilisées et leurs URLs
        df = pd.DataFrame(unused_classes, columns=["Classes CSS non utilisées", "URL du fichier CSS"])

        # Écrire dans un fichier Excel
        df.to_excel("unused_css_report.xlsx", index=False)
        return "unused_css_report.xlsx"
    return None

# Fonction principale appelée depuis main.py
def main():
    st.title("Détecteur de classes CSS inutilisées")
    
    # Sélection entre URL ou code HTML/CSS manuel
    option = st.radio("Choisissez l'option d'analyse :", ('URL', 'Manuel'))
    
    if option == 'URL':
        # Champ pour entrer l'URL
        html_url = st.text_input("Entrez l'URL de la page HTML à analyser")
        
        if st.button("Analyser"):
            if html_url:
                try:
                    # Récupérer le contenu HTML et les fichiers CSS
                    html_content, css_files = get_css_from_url(html_url)
                    
                    # Analyser les fichiers CSS
                    unused_classes = detect_unused_css(css_files, html_content)

                    # Générer un fichier Excel avec les classes CSS inutilisées et leurs URLs
                    excel_file = generate_unused_report_excel(unused_classes)

                    if excel_file:
                        st.success("Le fichier Excel a été généré avec succès !")

                        # Télécharger le fichier Excel
                        with open(excel_file, "rb") as f:
                            st.download_button("Télécharger le rapport Excel", f, file_name=excel_file)
                    else:
                        st.info("Aucune classe CSS inutilisée n'a été détectée.")
                except Exception as e:
                    st.error(f"Erreur lors de la récupération des données : {e}")
            else:
                st.error("Veuillez entrer une URL valide.")
    
    elif option == 'Manuel':
        # Champs pour entrer le contenu HTML et CSS manuellement
        html_content = st.text_area("Collez votre code HTML ici", height=300)
        css_content = st.text_area("Collez votre code CSS ici", height=300)

        if st.button("Analyser"):
            if html_content and css_content:
                css_files = [("CSS manuel", css_content)]
                unused_classes = detect_unused_css(css_files, html_content)

                # Générer un fichier Excel avec les classes CSS inutilisées
                excel_file = generate_unused_report_excel(unused_classes)

                if excel_file:
                    st.success("Le fichier Excel a été généré avec succès !")

                    # Télécharger le fichier Excel
                    with open(excel_file, "rb") as f:
                        st.download_button("Télécharger le rapport Excel", f, file_name=excel_file)
                else:
                    st.info("Aucune classe CSS inutilisée n'a été détectée.")
            else:
                st.error("Veuillez entrer du contenu HTML et CSS.")
