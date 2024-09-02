import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import re

def find_unclosed_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    stack = []
    unclosed_tags = []

    # Regex pour identifier les balises ouvrantes et fermantes
    tag_regex = re.compile(r'<(/?[\w\s=\"\'\-:;]*)>')

    # Extraire toutes les balises dans l'ordre où elles apparaissent
    for match in tag_regex.finditer(html):
        tag_str = match.group(0)
        is_closing_tag = tag_str.startswith("</")
        tag_name = tag_str.split()[0].replace("</", "").replace("<", "").replace(">", "")

        if not is_closing_tag:
            # Balise ouvrante, ajouter à la pile
            stack.append(tag_str)
        else:
            # Balise fermante, vérifier si elle correspond à la dernière balise ouvrante
            if stack and tag_name in stack[-1]:
                stack.pop()  # Balise fermée correctement, enlever de la pile
            else:
                unclosed_tags.append(tag_str)  # Balise fermante sans balise ouvrante correspondante

    # Toutes les balises restantes dans la pile sont non fermées
    unclosed_tags.extend(stack)
    
    return unclosed_tags

def find_empty_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    empty_tags = []

    for tag in soup.find_all(True):
        # Vérifie si la balise est vide et récupère la balise complète avec attributs dans l'ordre
        if not tag.text.strip() and not tag.find_all(True):
            empty_tags.append(str(tag))

    return empty_tags

def generate_excel(unclosed_tags, empty_tags):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Unclosed Tags: Chaque balise dans une cellule distincte
    df_unclosed = pd.DataFrame({'Unclosed Tag': unclosed_tags})
    
    # Empty Tags: Lister les balises vides en entier avec attributs
    df_empty = pd.DataFrame({'Empty Tag': empty_tags})

    df_unclosed.to_excel(writer, index=False, sheet_name='Unclosed Tags')
    df_empty.to_excel(writer, index=False, sheet_name='Empty Tags')

    writer.close()  # Utiliser close() au lieu de save()
    output.seek(0)
    return output

def main():
    st.title("HTML Tags Checker")

    html_code = st.text_area("Paste your HTML code here:")

    if st.button("Analyze HTML"):
        unclosed_tags = find_unclosed_tags(html_code)
        empty_tags = find_empty_tags(html_code)

        if unclosed_tags or empty_tags:
            excel_file = generate_excel(unclosed_tags, empty_tags)
            st.download_button(
                label="Download Excel file",
                data=excel_file,
                file_name="html_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.write("No unclosed or empty tags found.")
