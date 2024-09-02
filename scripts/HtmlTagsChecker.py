import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

def find_unclosed_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    unclosed_tags = []

    # Garder trace des balises ouvertes non fermées
    open_tags_stack = []

    for tag in soup.find_all(True):
        # Ajouter la balise au stack lorsqu'elle est ouverte
        open_tags_stack.append(tag)

        # Si une balise fermante est trouvée, enlever la balise correspondante du stack
        if tag.find_all(True):
            for child in tag.find_all(True):
                if child in open_tags_stack:
                    open_tags_stack.remove(child)

    # Toutes les balises restantes dans le stack sont des balises ouvertes non fermées
    for tag in open_tags_stack:
        unclosed_tags.append(str(tag))

    return unclosed_tags

def find_empty_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    empty_tags = []

    for tag in soup.find_all(True):
        # Vérifie si la balise est vide et récupère la balise complète
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

    writer.close()
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
