import streamlit as st
from scripts import MyTextGuru

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru
}

# Sélection de la page
selection = st.sidebar.selectbox("Choisissez une page", list(PAGES.keys()))

# Affichage du script sélectionné
page = PAGES[selection]
page.app()
