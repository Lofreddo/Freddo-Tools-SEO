import streamlit as st
import re
import pandas as pd
from io import BytesIO

def find_unclosed_tags(html):
    tag_pattern = re.compile(r'<([^/\s>]+)[^>]*>')  # Regex to find opening tags
    closing_tag_pattern = re.compile(r'</([^>]+)>')  # Regex to find closing tags
    tags = re.findall(tag_pattern, html)
    closing_tags = re.findall(closing_tag_pattern, html)
    
    stack = []
    unclosed_tags = []

    for match in re.finditer(tag_pattern, html):
        tag_str = match.group(0)
        tag_name = match.group(1)
        stack.append((tag_name, tag_str))

    for match in re.finditer(closing_tag_pattern, html):
        closing_tag_name = match.group(1)
        if stack and stack[-1][0] == closing_tag_name:
            stack.pop()
    
    unclosed_tags = [tag[1] for tag in stack]
    
    return unclosed_tags

def find_empty_tags(html):
    empty_tag_pattern = re.compile(r'<(\w+)([^>]*)/?>')
    empty_tags = []

    for match in re.finditer(empty_tag_pattern, html):
        tag_str = match.group(0)
        if match.group(0).endswith('/>') or not re.search(r'</\s*' + re.escape(match.group(1)) + r'\s*>', html):
            empty_tags.append(tag_str.strip())

    return empty_tags

def generate_excel(unclosed_tags, empty_tags):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Unclosed Tags: Chaque balise dans une cellule distincte
        df_unclosed = pd.DataFrame({'Unclosed Tag': unclosed_tags})
        df_empty = pd.DataFrame({'Empty Tag': empty_tags})

        df_unclosed.to_excel(writer, index=False, sheet_name='Unclosed Tags')
        df_empty.to_excel(writer, index=False, sheet_name='Empty Tags')

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
