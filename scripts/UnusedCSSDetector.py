import streamlit as st
from bs4 import BeautifulSoup
import re
import pandas as pd  # Import de pandas pour générer des fichiers Excel

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

def detect_unused_css(css_content, html_content):
    """Détecter les classes CSS non utilisées dans le fichier HTML"""
    css_classes = set(extract_css_classes(css_content))
    html_classes, elements_with_classes = extract_html_classes(html_content)

    # Classes CSS non utilisées
    unused_classes = css_classes - html_classes

    # Identifier les éléments HTML qui utilisent des classes non utilisées
    unused_elements = []
    for element, class_list in elements_with_classes:
        unused = set(class_list).intersection(unused_classes)
        if unused:
            unused_elements.append((element, list(unused)))

    return list(unused_classes), unused_elements

def generate_unused_report_excel(unused_classes):
    """Générer un fichier Excel listant les classes CSS inutilisées"""
    if unused_classes:
        # Créer un DataFrame avec une colonne "Classes CSS non utilisées"
        df = pd.DataFrame(unused_classes, columns=["Classes CSS non utilisées"])

        # Écrire dans un fichier Excel
        df.to_excel("unused_css_report.xlsx", index=False)
        return "unused_css_report.xlsx"
    return None

# Fonction principale appelée depuis main.py
def main():
    st.title("Détecteur de classes CSS inutilisées")
    
    # Champs pour entrer le contenu HTML et CSS
    html_content = st.text_area("Collez votre code HTML ici", height=300)
    css_content = st.text_area("Collez votre code CSS ici", height=300)

    # Bouton pour lancer l'analyse
    if st.button("Analyser"):
        if html_content and css_content:
            unused_classes, unused_elements = detect_unused_css(css_content, html_content)

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
            st.error("Veuillez entrer du contenu HTML et CSS avant de lancer l'analyse.")
