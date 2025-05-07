import streamlit as st
from scripts import MyTextGuru, MyTextGuruBulk, ExtractSerps, MasterSpinGenerator, Scrapping, ExtractSerpsV2, PointsChauds, DomainChecker, SiteAnalyzer, Scrapython, HtmlTagsChecker, EmptyHtmlTags, SpinChecker, UnusedCSSDetector, AuditSemantique, GscExtract, SimilarityText, TitleGenerator, KeywordClustering, LiensSortants, Audittechexpress, TableSF, urlopen, DomainCheckerV2, Keywordsimilarity, AuditSemGroup, ImageResizer, QuiSommesNous, ImageNameGenerator

# Configuration des pages
PAGES = {
    "MyTextGuru": MyTextGuru,
    "MyTextGuruBulk": MyTextGuruBulk,
    "ExtractSerps": ExtractSerps,
    "ExtractSerpsV2": ExtractSerpsV2,
    "MasterSpinGenerator": MasterSpinGenerator,  # Correction ici
    "Scrapping": Scrapping,
    "PointsChauds": PointsChauds,
    "DomainChecker": DomainChecker,
    "SiteAnalyzer": SiteAnalyzer,
    "Scrapython": Scrapython,
    "HtmlTagsChecker": HtmlTagsChecker,
    "EmptyHtmlTags": EmptyHtmlTags,
    "SpinChecker": SpinChecker,
    "UnusedCSSDetector": UnusedCSSDetector,
    "AuditSemantique": AuditSemantique,
    "GscExtract": GscExtract,
    "SimilarityText": SimilarityText,
    "TitleGenerator": TitleGenerator,
    "KeywordClustering": KeywordClustering,
    "LiensSortants": LiensSortants,
    "Audit Tech Express": Audittechexpress,
    "TableSF": TableSF,
    "urlopen": urlopen,
    "DomainCheckerV2": DomainCheckerV2,
    "Keywordsimilarity": Keywordsimilarity,
    "AuditSemGroup": AuditSemGroup,
    "ImageResizer": ImageResizer,
    "QuiSommesNous": QuiSommesNous,
    "ImageNameGenerator": ImageNameGenerator
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
