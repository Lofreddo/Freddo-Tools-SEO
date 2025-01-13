import re
import streamlit as st
from openai import OpenAI
from faker import Faker

# =========================================================================
# CONFIGURATION
# =========================================================================

MODEL = "gpt-4o-mini"  # ou ton modèle
MAX_TOKENS = 800
TEMPERATURE = 0.7

# Le client OpenAI sera créé dans main()
client = None

# Instancier Faker pour générer noms/prénoms francophones
fake = Faker('fr_FR')

# =========================================================================
# FONCTIONS
# =========================================================================

def random_first_name() -> str:
    """Génère uniquement un prénom en français."""
    return fake.first_name()

def random_full_name() -> str:
    """Génère un nom complet francophone (prénom + nom)."""
    return fake.name()

def generate_names(num_people: int, also_lastname: bool):
    """
    Génère un certain nombre d'identités.
    - soit prénoms uniquement (also_lastname=False)
    - soit nom + prénom (also_lastname=True)
    Retourne une liste de dicos: [{"name": ..., "validated": False}, ...]
    """
    names_list = []
    for _ in range(num_people):
        if also_lastname:
            generated = random_full_name()
        else:
            generated = random_first_name()
        names_list.append({"name": generated, "validated": False})
    return names_list

def regenerate_unvalidated(names_list, also_lastname: bool):
    """
    Régénère uniquement les identités non validées.
    """
    for item in names_list:
        if not item["validated"]:
            if also_lastname:
                item["name"] = random_full_name()
            else:
                item["name"] = random_first_name()
    return names_list

def strip_html_tags(text: str) -> str:
    """Supprime toute balise HTML (<...>) du texte."""
    return re.sub(r"<[^>]*>", "", text)

def generate_description(names_list, theme, paragraphs, tone, custom_instructions):
    """
    Génère un texte "Qui sommes-nous ?" en texte brut, sans balises HTML.
    """
    # Extraire la liste des noms (strings)
    only_names = [item["name"] for item in names_list]

    user_content = f"""
    Rédige une présentation pour la page "Qui sommes-nous ?" d'un site,
    au format texte brut (aucune balise HTML, aucune syntaxe Markdown).

    Nous avons {len(only_names)} auteur(s) : {', '.join(only_names)}.
    Thématique du site : {theme if theme else "non spécifiée"}.
    Ton : {tone if tone else "non spécifié"}.
    Nombre de paragraphes souhaités : {paragraphs}.

    Génère {paragraphs} paragraphes (séparés par des sauts de ligne),
    et n'inclus AUCUNE balise HTML ou autre code. Juste du texte pur.

    ---

    {f"INSTRUCTIONS SUPPLÉMENTAIRES : {custom_instructions}" if custom_instructions else ""}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant spécialisé en rédaction SEO. "
                        "Tu dois créer un texte 'Qui sommes-nous ?' "
                        "en texte brut (pas de HTML)."
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
        generated_text = response.choices[0].message.content.strip()

        # Supprimer toute balise HTML résiduelle
        generated_text = strip_html_tags(generated_text)

    except Exception as e:
        generated_text = f"Erreur lors de la génération : {str(e)}"

    return generated_text

# =========================================================================
# APPLICATION STREAMLIT
# =========================================================================

def main():
    st.title("Générateur de page \"Qui sommes-nous ?\" (Texte brut)")

    global client
    # Récupération de la clé API
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # Variables de session
    if "names_list" not in st.session_state:
        st.session_state["names_list"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""

    # Choix du nombre de personnes
    num_people = st.number_input(
        "Nombre de personnes à présenter",
        min_value=1, max_value=20, value=3
    )

    # Case : Renseigner manuellement les auteurs, ou non
    renseigner_manuellement = st.checkbox("Renseigner manuellement les auteurs ?", value=False)

    if renseigner_manuellement:
        # On affiche un champ text_input pour chaque auteur
        st.write("**Veuillez saisir les auteurs :**")
        for i in range(num_people):
            key_name = f"manual_author_{i}"
            # Crée le champ si non existant
            if key_name not in st.session_state:
                st.session_state[key_name] = ""
            # Input
            st.session_state[key_name] = st.text_input(
                label=f"Auteur {i+1}",
                value=st.session_state[key_name],
                key=key_name
            )

        if st.button("Valider auteurs manuels"):
            # On construit la liste "names_list"
            new_list = []
            for i in range(num_people):
                k = f"manual_author_{i}"
                val = st.session_state.get(k, "")
                new_list.append({"name": val, "validated": True})
            st.session_state["names_list"] = new_list
            st.session_state["description"] = ""

    else:
        # Case pour générer aussi le nom de famille
        also_lastname = st.checkbox("Générer aussi des noms (en plus des prénoms)", value=False)

        # Boutons de génération / régénération
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Générer identités"):
                st.session_state["names_list"] = generate_names(num_people, also_lastname)
                st.session_state["description"] = ""
        with col2:
            if st.button("Régénérer identités (non validées)"):
                st.session_state["names_list"] = regenerate_unvalidated(st.session_state["names_list"], also_lastname)
                st.session_state["description"] = ""

    # Si on a des identités, on les affiche
    if st.session_state["names_list"]:
        st.subheader("Identités générées / renseignées :")
        for index, item in enumerate(st.session_state["names_list"]):
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"{index+1}. {item['name']}")
            with cols[1]:
                # On crée une checkbox pour valider l'item
                is_checked = st.checkbox(
                    "Valider",
                    value=item["validated"],
                    key=f"validate_{index}"
                )
                item["validated"] = is_checked

    # Inputs : Thématique, paragraphes, ton, instructions
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")
    paragraphs = st.number_input("Nombre de paragraphes (2 par défaut si non renseigné)",
                                 min_value=1, max_value=10, value=2)
    tone = st.text_input("Tonalité du texte (ex. humoristique, formel, sérieux...)")
    custom_instructions = st.text_area(
        "Instructions supplémentaires (optionnel)",
        help="Donnez des consignes précises : style, vocabulaire, etc."
    )

    # Boutons de génération / régénération de la description
    col_desc_1, col_desc_2 = st.columns([1, 1])
    with col_desc_1:
        if st.button("Générer la description"):
            st.session_state["description"] = generate_description(
                st.session_state["names_list"],
                theme,
                paragraphs,
                tone,
                custom_instructions
            )
    with col_desc_2:
        if st.button("Régénérer la description"):
            st.session_state["description"] = generate_description(
                st.session_state["names_list"],
                theme,
                paragraphs,
                tone,
                custom_instructions
            )

    # Affichage de la description en texte brut
    st.markdown("### Description générée (texte brut)")
    st.text_area(label="", value=st.session_state["description"], height=300)

if __name__ == "__main__":
    main()
