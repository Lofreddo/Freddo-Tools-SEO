import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import re

def find_unclosed_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    stack = []
    unclosed_tags = []

    # Parcourir toutes les balises dans l'ordre
    for tag in soup.find_all(True):
        if not tag.name.startswith("/"):  # Ignorer les balises fermantes
            stack.append(tag)
        else:
            # Retirer de la pile la balise ouvrante correspondante
            if stack and stack[-1].name == tag.name.replace("/", ""):
                stack.pop()
    
    # Les balises restantes dans la pile sont les balises non fermées
    for tag in stack:
        unclosed_tags.append(str(tag))

    return unclosed_tags

def find_empty_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    empty_tags = []

    for tag in soup.find_all(True):
        if not tag.text.strip() and not tag.find_all(True):
            # Utilisation de la méthode prettify pour conserver l'ordre des attributs
            empty_tags.append(tag.prettify(formatter=None).strip())

    return empty_tags

def generate_excel(unclosed_tags, empty_tags):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Unclosed Tags: Chaque balise dans une cellule distincte
    df_unclosed = pd.DataFrame({'Unclosed Tag': unclosed_tags})
    
    # Empty Tags: Lister les balises vides en entier avec attributs dans l'ordre
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
