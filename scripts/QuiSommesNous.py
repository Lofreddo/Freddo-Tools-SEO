import streamlit as st
import openai
import streamlit.components.v1 as components
from faker import Faker

# Créer une instance Faker avec la locale française
fake = Faker('fr_FR')

def random_name():
    """Génère un nom complet francophone."""
    # Faker génère par défaut un 'nom complet' : ex. "Marie Dupont"
    return fake.name()

def generate_names(num_people: int):
    """Génère un certain nombre de noms/prénoms."""
    names_list = [random_name() for _ in range(num_people)]
    return names_list

def generate_description(names, theme, paragraphs, tone):
    """
    Génère le texte "Qui sommes-nous ?" au format HTML en interrogeant l’API OpenAI.
    """
    # Construisons le prompt
    prompt = f"""
    Rédige une présentation au format HTML pour la page "Qui sommes-nous ?" d'un site.
    Il y a {len(names)} auteur(s) : {', '.join(names)}.
    Thématique du site : {theme if theme else "non spécifiée"}.
    Ton : {tone if tone else "non spécifié"}.
    Nombre de paragraphes souhaités : {paragraphs}.

    Génère {paragraphs} paragraphes et fais en sorte que le texte soit utilisable directement en HTML.
    """

    # Appel à l'API OpenAI
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Ou gpt-3.5-turbo / gpt-4 selon tes accès
            prompt=prompt,
            max_tokens=600,
            temperature=0.7
        )
        generated_text = response.choices[0].text.strip()
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
    st.title("Générateur de page \"Qui sommes-nous ?\"")

    # Configuration de la clé API OpenAI
    # => À adapter selon ta gestion des secrets (env, st.secrets, etc.)
    if "OPENAI_API_KEY" not in st.secrets:
        st.warning("Veuillez configurer votre clé OPENAI_API_KEY dans Streamlit secrets.")
        return
    else:
        openai.api_key = st.secrets["OPENAI_API_KEY"]

    # Instancier/initialiser des variables de session pour stocker noms & description
    if "names" not in st.session_state:
        st.session_state["names"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""

    # 1) Saisie du nombre de personnes
    num_people = st.number_input("Nombre de personnes à présenter", min_value=1, max_value=20, value=3)

    # 2) Boutons pour générer/régénérer les identités
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Générer noms"):
            st.session_state["names"] = generate_names(num_people)
    with col2:
        if st.button("Régénérer noms"):
            st.session_state["names"] = generate_names(num_people)

    # Affichage des noms générés
    st.subheader("Identités générées :")
    if st.session_state["names"]:
        for i, name in enumerate(st.session_state["names"], start=1):
            st.write(f"{i}. {name}")

    # 3) Champ pour la thématique du site
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")

    # 4) Champ pour le nombre de paragraphes, avec valeur par défaut
    paragraphs = st.number_input(
        "Nombre de paragraphes (2 par défaut si non renseigné)",
        min_value=1, max_value=10, value=2
    )

    # 5) Champ optionnel pour préciser la tonalité
    tone = st.text_input("Tonalité du texte (optionnel) (ex. humoristique, formel, sérieux...)")

    # 6) Bouton pour générer la description
    if st.button("Générer la description"):
        st.session_state["description"] = generate_description(
            st.session_state["names"],
            theme,
            paragraphs,
            tone
        )

    # 7) Affichage de la description générée
    st.markdown("### Description générée")
    st.markdown(st.session_state["description"], unsafe_allow_html=True)

    # 8) Boutons supplémentaires
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
