import streamlit as st
import pandas as pd
import re
import io
from collections import defaultdict

# Liste des balises auto-fermantes
self_closing_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'path'}

def find_unclosed_tags(html_content):
    # Minification du code HTML pour supprimer les espaces inutiles
    html_content = re.sub(r'>\s+<', '><', html_content.strip())

    tag_pattern = re.compile(r'<(/?)(\w+)([^>]*)>')
    stack = []
    unclosed_tags = defaultdict(list)
    
    for match in tag_pattern.finditer(html_content):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        full_tag = match.group(0)
        
        # Vérifier si la balise est auto-fermante
        if tag_name in self_closing_tags or full_tag.endswith('/>'):
            continue
        
        if not is_closing:
            stack.append((tag_name, full_tag))
        else:
            while stack and stack[-1][0] != tag_name:
                unclosed_tag = stack.pop()
                unclosed_tags[unclosed_tag[0]].append(unclosed_tag[1])
            if stack and stack[-1][0] == tag_name:
                stack.pop()
            else:
                # Extra closing tag
                unclosed_tags[tag_name].append(f"Extra closing tag: {full_tag}")
    
    # Any tags left in the stack are unclosed
    for tag_name, full_tag in reversed(stack):
        unclosed_tags[tag_name].append(full_tag)
    
    return unclosed_tags

def main():
    st.title("HTML Unclosed Tags Finder")

    html_content = st.text_area("Enter HTML content:")

    if st.button("Find Unclosed Tags"):
        unclosed_tags = find_unclosed_tags(html_content)
        
        if unclosed_tags:
            # Flatten the dictionary into a list of tuples
            flat_list = [(tag, item) for tag, items in unclosed_tags.items() for item in items]
            df = pd.DataFrame(flat_list, columns=["Tag Name", "Unclosed Tag"])
            
            # Create an in-memory Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Unclosed Tags')
            
            # Offer the file for download
            st.download_button(
                label="Download Excel file",
                data=output.getvalue(),
                file_name="unclosed_tags.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No unclosed tags found.")

if __name__ == "__main__":
    main()
