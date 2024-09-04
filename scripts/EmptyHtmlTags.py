import streamlit as st
import pandas as pd
import lxml.html
import io

def is_self_closing(tag):
    return tag.tag in ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'path']

def is_empty_tag(tag):
    # Vérifier si l'élément a un contenu texte vide et pas d'enfants
    if tag.text is None or not tag.text.strip():
        return len(tag) == 0  # Vérifie si l'élément n'a pas d'enfants
    return False

def find_empty_tags(html_content):
    tree = lxml.html.fromstring(html_content)
    empty_tags = []

    for element in tree.iter():
        if is_self_closing(element):
            continue
        
        if is_empty_tag(element):
            # Utiliser lxml pour récupérer le code source d'origine de l'élément
            empty_tags.append(lxml.html.tostring(element, encoding='unicode'))

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
