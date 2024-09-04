import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup, Tag, NavigableString
import io

def is_self_closing(tag):
    return tag.name in ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'path']

def is_empty_tag(tag):
    if isinstance(tag, Tag):
        # Vérifier si la balise est vide ou ne contient que des espaces/sauts de ligne
        return not tag.contents or all(
            (isinstance(child, NavigableString) and not child.strip()) or
            (isinstance(child, Tag) and is_empty_tag(child))
            for child in tag.contents
        )
    return False

def find_empty_tags(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    empty_tags = []

    for tag in soup.find_all():
        if is_self_closing(tag):
            continue
        
        if is_empty_tag(tag):
            # Récupérer la balise complète avec son contenu original
            empty_tags.append(str(tag))

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
