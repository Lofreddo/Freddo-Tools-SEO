import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from faker import Faker

# =========================================================================
# CONFIGURATION OPENAI
# =========================================================================

# Modèle, tokens, et temperature : adaptés selon tes besoins
MODEL = "gpt-4o-mini"
MAX_TOKENS = 800
TEMPERATURE = 0.7

# Le client sera initialisé dans main()
client = None

# =========================================================================
# FAKER POUR LES NOMS FRANCOPHONES
# =========================================================================

fake = Faker('fr_FR')

def random_name():
    """Génère un nom complet francophone."""
    return fake.name()

def generate_names(num_people: int):
    """Génère un certain nombre de noms."""
    return [random_name() for _ in range(num_people)]

# =========================================================================
# GENERATION DE LA DESCRIPTION
# =========================================================================

def generate_description(names, theme, paragraphs, tone):
    """
    Génère le texte "Qui sommes-nous ?" au format HTML.
    On utilise le client OpenAI (chat.completions.create) au même format
    que dans l'exemple fourni.
    """
    # Création du prompt (contenu "user")
    user_content = f"""
    Rédige une présentation au format HTML pour la page "Qui sommes-nous ?" d'un site.
    Nous avons {len(names)} auteur(s) : {', '.join(names)}.
    Thématique du site : {theme if theme else "non spécifiée"}.
    Ton : {tone if tone else "non spécifié"}.
    Nombre de paragraphes souhaités : {paragraphs}.

    Génère {paragraphs} paragraphes au format HTML.
    Assure-toi que le résultat soit utilisable directement dans une page web.
    """

    try:
        # Appel du client OpenAI, comme dans ton script de génération
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant spécialisé en rédaction SEO et structuration HTML. "
                        "Ta mission est de créer un texte Qui sommes-nous ? selon les informations fournies."
                    )
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )

        # Récupération du texte
        generated_text = response.choices[0].message.content.strip()
    except Exception as e:
        generated_text = f"<p style='color:red;'>Erreur lors de la génération : {str(e)}</p>"

    return generated_text

# =========================================================================
# FONCTION DE COPIE
# =========================================================================

def copy_to_clipboard(text: str):
    """Copie le texte dans le presse-papiers via le navigateur."""
    safe_text = text.replace("`", "\\`")
    components.html(
        f"""
        <script>
            navigator.clipboard.writeText(`{safe_text}`);
            alert("Description copiée dans le presse-papiers !");
        </script>
        """,
        height=0,
        width=0
    )

# =========================================================================
# APPLICATION STREAMLIT
# =========================================================================

def main():
    st.title("Générateur de page \"Qui sommes-nous ?\"")

    # 1) Initialisation du client OpenAI avec le même format que dans l'autre script
    #    On récupère la clé depuis st.secrets (adaptation selon ta config).
    global client
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # 2) Variables de session pour stocker les noms et la description
    if "names" not in st.session_state:
        st.session_state["names"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""

    # 3) Nombre de personnes à présenter
    num_people = st.number_input(
        "Nombre de personnes à présenter",
        min_value=1, max_value=20, value=3
    )

    # 4) Boutons pour générer ou régénérer les identités
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Générer noms"):
            st.session_state["names"] = generate_names(num_people)
    with col2:
        if st.button("Régénérer noms"):
            st.session_state["names"] = generate_names(num_people)

    # 5) Affichage des noms générés
    st.subheader("Identités générées :")
    if st.session_state["names"]:
        for i, name in enumerate(st.session_state["names"], start=1):
            st.write(f"{i}. {name}")

    # 6) Thématique du site
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")

    # 7) Nombre de paragraphes
    paragraphs = st.number_input(
        "Nombre de paragraphes (2 par défaut si non renseigné)",
        min_value=1, max_value=10, value=2
    )

    # 8) Ton (optionnel)
    tone = st.text_input("Tonalité du texte (ex. humoristique, formel, sérieux...)")

    # 9) Bouton pour générer la description
    if st.button("Générer la description"):
        st.session_state["description"] = generate_description(
            st.session_state["names"],
            theme,
            paragraphs,
            tone
        )

    # 10) Affichage de la description
    st.markdown("### Description générée")
    st.markdown(st.session_state["description"], unsafe_allow_html=True)

    # 11) Boutons : Copier / Régénérer
    col_copy, col_regen = st.columns(2)
    with col_copy:
        if st.button("Copier la description"):
            copy_to_clipboard(st.session_state["description"])
    with col_regen:
        if st.button("Régénérer la description"):
            st.session_state["description"] = generate_description(
                st.session_state["names"],
                theme,
                paragraphs,
                tone
            )

# Point d'entrée
if __name__ == "__main__":
    main()
