import streamlit as st
from scripts import AspirateurScriptsPython, MyTextGuru, MyTextGuruBulk, ExtractSerps, MasterSpinGenerator, Scrapping, ExtractSerpsV2

# Configuration des pages
PAGES = {
    "AspirateurScriptsPython": AspirateurScriptsPython,
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
