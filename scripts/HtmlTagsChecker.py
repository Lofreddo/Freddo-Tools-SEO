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
        opened_tags.append(tag.name)
        if tag.find_all(True):
            closed_tags.extend([child.name for child in tag.find_all(True)])

    for tag in opened_tags:
        if opened_tags.count(tag) != closed_tags.count(tag):
            unclosed_tags.append(tag)

    return list(set(unclosed_tags))

def find_empty_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    empty_tags = []

    for tag in soup.find_all(True):
        if not tag.text.strip() and not tag.find_all(True):
            empty_tags.append(str(tag))

    return empty_tags

def generate_excel(unclosed_tags, empty_tags):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    df_unclosed = pd.DataFrame(unclosed_tags, columns=["Unclosed Tags"])
    df_empty = pd.DataFrame(empty_tags, columns=["Empty Tags"])

    df_unclosed.to_excel(writer, index=False, sheet_name='Unclosed Tags')
    df_empty.to_excel(writer, index=False, sheet_name='Empty Tags')

    writer.save()
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
