import streamlit as st
from scripts import MyTextGuru

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru
}

# Affichage du script sélectionné
page = PAGES[selection]
page.app()
