import streamlit as st
from scripts import MyTextGuru, MyTextGuruBulk, ExtractSerps, MadterSpinGenerator, Scrapping, ExtractSerpsV2, PointsChauds, DomainChecker

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru,
    "MyTextGuruBulk": MyTextGuruBulk,
    "ExtractSerps": ExtractSerps,
    "ExtractSerpsV2": ExtractSerpsV2,
    "MasterSpinGenerator": MasterSpinGenerator,
    "Scrapping": Scrapping,
    "PointsChauds": PointsChauds,
    "DomainChecker": DomainChecker
}

# Créer une sidebar pour la navigation
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Charger la page sélectionnée avec une vérification
page = PAGES[selection]

# Vérification de l'existence de la fonction main()
if hasattr(page, 'main') and callable(getattr(page, 'main')):
    page.main()
else:
    st.error(f"La page sélectionnée ({selection}) ne contient pas de fonction 'main()'.")
