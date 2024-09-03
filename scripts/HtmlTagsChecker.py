import re
from collections import defaultdict

def find_unclosed_tags(html_content):
    # Minification du code HTML pour supprimer les espaces inutiles
    html_content = re.sub(r'>\s+<', '><', html_content.strip())

    tag_pattern = re.compile(r'<(/?)(\w+)([^>]*?)(/?)>')
    tag_count = defaultdict(lambda: {'open': 0, 'close': 0, 'positions': []})
    unclosed_tags = defaultdict(list)

    # Premier passage : comptage et enregistrement des positions
    for match in tag_pattern.finditer(html_content):
        is_closing = match.group(1) == '/'
        is_self_closing = match.group(4) == '/'
        tag_name = match.group(2).lower()
        full_tag = match.group(0)
        position = match.start()

        if is_self_closing:
            continue

        if is_closing:
            tag_count[tag_name]['close'] += 1
        else:
            tag_count[tag_name]['open'] += 1

        tag_count[tag_name]['positions'].append((position, full_tag, is_closing))

    # Deuxième passage : analyse des balises non fermées
    for tag_name, info in tag_count.items():
        if info['open'] != info['close']:
            diff = info['open'] - info['close']
            if diff > 0:
                unclosed_tags[tag_name].append(f"{diff} unclosed {tag_name} tag(s)")
            else:
                unclosed_tags[tag_name].append(f"{-diff} extra closing {tag_name} tag(s)")

            # Trier les positions pour respecter l'ordre d'apparition dans le code
            sorted_positions = sorted(info['positions'])
            stack = []
            for pos, full_tag, is_closing in sorted_positions:
                if is_closing:
                    if stack:
                        stack.pop()
                    else:
                        unclosed_tags[tag_name].append(f"Extra closing tag at position {pos}: {full_tag}")
                else:
                    stack.append((pos, full_tag))

            # Les balises restantes dans la pile sont non fermées
            for pos, full_tag in stack:
                unclosed_tags[tag_name].append(f"Unclosed tag at position {pos}: {full_tag}")

    return unclosed_tags

# Fonction principale pour Streamlit (inchangée)
def main():
    st.title("HTML Unclosed Tags Finder")

    html_content = st.text_area("Enter HTML content:")

    if st.button("Find Unclosed Tags"):
        unclosed_tags = find_unclosed_tags(html_content)
        
        if unclosed_tags:
            flat_list = [(tag, item) for tag, items in unclosed_tags.items() for item in items]
            df = pd.DataFrame(flat_list, columns=["Tag Name", "Issue"])
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Unclosed Tags')
            
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
