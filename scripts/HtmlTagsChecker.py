import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

def find_unclosed_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    opened_tags = []
    closed_tags = []
    unclosed_tags = []

    for tag in soup.find_all(True):
        tag_str = str(tag)
        opened_tags.append(tag_str)

        # Registre les balises fermées avec leur contenu complet
        if tag.find_all(True):
            closed_tags.extend([str(child) for child in tag.find_all(True)])

    # Identifier les balises non fermées en comparant les occurrences
    for tag in opened_tags:
        if opened_tags.count(tag) > closed_tags.count(tag):
            unclosed_tags.append(tag)

    return list(set(unclosed_tags))

def find_empty_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    empty_tags = []

    for tag in soup.find_all(True):
        # Vérifie si la balise est vide et récupère la balise complète
        if not tag.text.strip() and not tag.find_all(True):
            tag_details = {
                'tag': tag.name,
                'id': tag.get('id', ''),
                'class': tag.get('class', ''),
                'name': tag.get('name', ''),
                'rel': tag.get('rel', ''),
                'other_attributes': {k: v for k, v in tag.attrs.items() if k not in ['id', 'class', 'name', 'rel']}
            }
            empty_tags.append(tag_details)

    return empty_tags

def generate_excel(unclosed_tags, empty_tags):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Unclosed Tags: Chaque balise dans une cellule distincte
    df_unclosed = pd.DataFrame({'Unclosed Tag': unclosed_tags})
    
    # Empty Tags: Lister les attributs des balises vides
    empty_tags_data = []
    for tag in empty_tags:
        empty_tags_data.append([
            tag['tag'],
            tag['id'],
            tag['class'],
            tag['name'],
            tag['rel'],
            ', '.join([f"{k}={v}" for k, v in tag['other_attributes'].items()])
        ])
    
    df_empty = pd.DataFrame(empty_tags_data, columns=["Tag", "ID", "Class", "Name", "Rel", "Other Attributes"])

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
