import streamlit as st
from scripts import MyTextGuru, ExtractSerps, MasterSpinGenerator

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru,
    "ExtractSerps": ExtractSerps,
    'MasterSpinGenerator": MasterSpinGenerator
}

# Créer une sidebar pour la navigation
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Charger la page sélectionnée
page = PAGES[selection]
page.main()
