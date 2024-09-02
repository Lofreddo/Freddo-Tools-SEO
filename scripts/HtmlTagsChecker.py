import streamlit as st
import pandas as pd
import re
import io

htmlRegex = '<[^\!][^>]*>'
openingTagRegex = '<[^/]'
closingTagRegex = '</'

def get_tag_list(html):
    tags = re.compile(htmlRegex, flags=re.I | re.M)
    tag_list = re.findall(tags, html)
    return tag_list

def get_opening_tag_list(tag_list):
    opening_tag = list(
        filter(
            lambda tag: re.match(openingTagRegex, tag),
            tag_list
        )
    )
    return opening_tag

def get_closing_tag_list(tag_list):
    closing_tag_list = list(
        filter(
            lambda tag: re.match(closingTagRegex, tag),
            tag_list
        )
    )
    return closing_tag_list

def clean_html(raw_html):
    cleantext = re.sub(r'\W+', '', raw_html)
    return cleantext

def clean_list(the_list):
    return [clean_html(val) for val in the_list]

def find_unclosed_tags(html_content):
    tag_list = get_tag_list(html_content)
    opening_tag_list = get_opening_tag_list(tag_list)
    closing_tag_list = get_closing_tag_list(tag_list)
    
    clean_opening = clean_list(opening_tag_list)
    clean_closing = clean_list(closing_tag_list)
    
    unclosed_tags = []
    for tag in clean_opening:
        if tag not in clean_closing:
            unclosed_tags.append(tag)
    
    return unclosed_tags

def main():
    st.title("HTML Unclosed Tags Finder")

    html_content = st.text_area("Enter HTML content:")

    if st.button("Find Unclosed Tags"):
        unclosed_tags = find_unclosed_tags(html_content)
        
        if unclosed_tags:
            df = pd.DataFrame(unclosed_tags, columns=["Unclosed Tags"])
            
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
