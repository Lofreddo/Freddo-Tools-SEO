import streamlit as st
import openai
import streamlit.components.v1 as components
from faker import Faker

# Instancier Faker pour générer des noms francophones
fake = Faker('fr_FR')

def random_name():
    """Génère un nom complet francophone."""
    return fake.name()

def generate_names(num_people: int):
    """Génère un certain nombre de noms/prénoms."""
    return [random_name() for _ in range(num_people)]

def generate_description(names, theme, paragraphs, tone):
    """
    Génère un texte "Qui sommes-nous ?" au format HTML en utilisant
    la nouvelle interface openai>=1.0.0 : openai.chat_completions.create().
    """

    # Construisons le contenu (prompt) que l'on va passer en "user"
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
        response = openai.chat_completions.create(
            model="gpt-3.5-turbo",    # ou "gpt-4" si disponible
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant spécialisé en rédaction de texte "
                        "pour des pages web. Ta mission est de créer un texte "
                        "\"Qui sommes-nous ?\" selon les informations fournies."
                    )
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        generated_text = response.choices[0].message.content.strip()
    except Exception as e:
        generated_text = f"<p style='color:red;'>Erreur lors de la génération : {str(e)}</p>"

    return generated_text

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

def main():
    st.title("Générateur de page \"Qui sommes-nous ?\" - Nouvelle API OpenAI")

    # Récupération de la clé OpenAI depuis les secrets Streamlit
    openai.api_key = st.secrets["openai_api_key"]

    # Variables de session pour stocker les noms et la description
    if "names" not in st.session_state:
        st.session_state["names"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""

    # 1) Saisie du nombre de personnes
    num_people = st.number_input(
        "Nombre de personnes à présenter",
        min_value=1, max_value=20, value=3
    )

    # 2) Boutons pour générer ou régénérer les identités
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Générer noms"):
            st.session_state["names"] = generate_names(num_people)
    with col2:
        if st.button("Régénérer noms"):
            st.session_state["names"] = generate_names(num_people)

    # 3) Affichage des noms générés
    st.subheader("Identités générées :")
    if st.session_state["names"]:
        for i, name in enumerate(st.session_state["names"], start=1):
            st.write(f"{i}. {name}")

    # 4) Saisie de la thématique
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")

    # 5) Saisie du nombre de paragraphes
    paragraphs = st.number_input(
        "Nombre de paragraphes (2 par défaut si non renseigné)",
        min_value=1, max_value=10, value=2
    )

    # 6) Saisie du ton (optionnel)
    tone = st.text_input("Tonalité du texte (optionnel) (ex. humoristique, formel, sérieux...)")

    # 7) Bouton pour générer la description
    if st.button("Générer la description"):
        st.session_state["description"] = generate_description(
            st.session_state["names"],
            theme,
            paragraphs,
            tone
        )

    # 8) Affichage du texte généré
    st.markdown("### Description générée")
    st.markdown(st.session_state["description"], unsafe_allow_html=True)

    # 9) Boutons : Copier / Régénérer
    col_copy, col_regen = st.columns([1, 1])
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

if __name__ == "__main__":
    main()
