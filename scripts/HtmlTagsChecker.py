import streamlit as st
import pandas as pd
from html.parser import HTMLParser

class UnclosedTagFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.open_tags = []

    def handle_starttag(self, tag, attrs):
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in self.open_tags:
            self.open_tags.remove(tag)

    def get_unclosed_tags(self):
        return self.open_tags

def find_unclosed_tags(html_content):
    parser = UnclosedTagFinder()
    parser.feed(html_content)
    return parser.get_unclosed_tags()

def main():
    st.title("HTML Unclosed Tags Finder")

    # Input text area for HTML content
    html_content = st.text_area("Enter HTML content:")

    if st.button("Find Unclosed Tags"):
        unclosed_tags = find_unclosed_tags(html_content)
        if unclosed_tags:
            st.write("Unclosed tags found:", unclosed_tags)

            # Create a DataFrame and export to Excel
            df = pd.DataFrame(unclosed_tags, columns=["Unclosed Tags"])
            df.to_excel("unclosed_tags.xlsx", index=False)
            st.success("Excel file created: unclosed_tags.xlsx")
        else:
            st.write("No unclosed tags found.")

if __name__ == "__main__":
    main()
