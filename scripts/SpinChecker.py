import streamlit as st

def check_unbalanced_brackets(text):
    stack = []
    unbalanced = []
    
    for i, char in enumerate(text):
        if char == '{':
            stack.append((char, i))
        elif char == '}':
            if stack and stack[-1][0] == '{':
                stack.pop()
            else:
                unbalanced.append((char, i))
        elif char == '|':
            if not stack:
                unbalanced.append((char, i))
    
    unbalanced.extend(stack)
    return sorted(unbalanced, key=lambda x: x[1])

def main():
    st.title("Master Spin Bracket Checker")
    
    spin_text = st.text_area("Enter your master spin text here:")
    
    if st.button("Check Brackets"):
        unbalanced = check_unbalanced_brackets(spin_text)
        
        if unbalanced:
            st.error("Unbalanced brackets found:")
            for char, pos in unbalanced:
                st.write(f"Unbalanced '{char}' at position {pos}")
                st.text(spin_text[:pos] + "👉" + spin_text[pos] + "👈" + spin_text[pos+1:])
        else:
            st.success("All brackets are balanced!")

if __name__ == "__main__":
    main()
