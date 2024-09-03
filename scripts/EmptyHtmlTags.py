import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import io
import re

def is_self_closing(tag):
    return tag.name in ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'path']

def find_empty_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    empty_tags = []

    for tag in re.finditer(r'<[^/][^>]*>(?:\s*</[^>]+>)?', html_content):
        tag_content = tag.group()
        if '/>' in tag_content:  # Ignorer les balises auto-fermantes
            continue
        
        parsed_tag = BeautifulSoup(tag_content, 'html.parser').find()
        if parsed_tag and not is_self_closing(parsed_tag):
            if not parsed_tag.contents or all(isinstance(child, str) and not child.strip() for child in parsed_tag.contents):
                empty_tags.append(tag_content)

    return empty_tags

def main():
    st.title("Analyseur de balises HTML vides")

    html_input = st.text_area("Collez votre code HTML ici:", height=300)

    if st.button("Analyser"):
        if html_input:
            empty_tags = find_empty_tags(html_input)
            
            if empty_tags:
                df = pd.DataFrame({"Balises vides": empty_tags})
                
                st.write("Balises vides trouvées:")
                st.dataframe(df)
                
                excel_file = io.BytesIO()
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_file.seek(0)
                
                st.download_button(
                    label="Télécharger le fichier Excel",
                    data=excel_file,
                    file_name="balises_vides.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.write("Aucune balise vide trouvée.")
        else:
            st.write("Veuillez entrer du code HTML à analyser.")

if __name__ == "__main__":
    main()
