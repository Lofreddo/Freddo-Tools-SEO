import streamlit as st
import pandas as pd
import re
import io

def find_unclosed_tags(html_content):
    stack = []
    unclosed_tags = []
    tag_pattern = re.compile(r'<[^>]+>')
    
    for match in tag_pattern.finditer(html_content):
        tag = match.group()
        if tag.startswith('</'):
            # Closing tag
            if stack and stack[-1].split()[0][1:] == tag[2:-1]:
                stack.pop()
            else:
                # Mismatched closing tag, ignore it
                pass
        elif not tag.endswith('/>'):
            # Opening tag
            stack.append(tag)
    
    # Any tags left in the stack are unclosed
    unclosed_tags = stack
    
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
