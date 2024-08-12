import streamlit as st
from scripts import MyTextGuru, MyTextGuruBulk, ExtractSerps, MasterSpinGenerator, Scrapping, ExtractSerpsV2

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru,
    "MyTextGuruBulk": MyTextGuruBulk,
    "ExtractSerps": ExtractSerps,
    "ExtractSerpsV2": ExtractSerpsV2,
    "MasterSpinGenerator": MasterSpinGenerator,
    "Scrapping": Scrapping
}

# Créer une sidebar pour la navigation
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Charger la page sélectionnée
page = PAGES[selection]
page.main()
