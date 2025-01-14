import re
import streamlit as st
from openai import OpenAI
from faker import Faker

# =========================================================================
# CONFIGURATION
# =========================================================================

MODEL = "gpt-4o-mini"  # Ou ton modèle
MAX_TOKENS = 800
TEMPERATURE = 0.7

# L'objet client OpenAI sera créé dans main()
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
    Retourne une liste de dicos : [{"name": ..., "validated": False}, ...]
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
    """Régénère uniquement les identités non validées."""
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
    au format texte brut (sans balises HTML ni Markdown).

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

def generate_short_summary(full_text, theme, tone):
    """
    Génère une version courte (2-3 phrases) du texte 'Qui sommes-nous ?'.
    Se base sur 'full_text' et les consignes (theme, tone).
    """
    prompt_user = f"""
    Tu as le texte "Qui sommes-nous ?" suivant :

    {full_text}

    Résume-le en 2 ou 3 phrases maximum, en texte brut, sans balises HTML,
    afin de pouvoir l'afficher sur une page d'accueil. 
    Conserve la même tonalité (actuellement : {tone if tone else "non spécifié"}).
    Thématique : {theme if theme else "non spécifiée"}.
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant spécialisé en rédaction SEO. "
                        "Ta mission : faire un résumé très court, en texte brut."
                    )
                },
                {
                    "role": "user",
                    "content": prompt_user
                }
            ],
            max_tokens=300,
            temperature=TEMPERATURE
        )
        short_text = response.choices[0].message.content.strip()
        short_text = strip_html_tags(short_text)
    except Exception as e:
        short_text = f"Erreur lors de la génération du résumé : {str(e)}"

    return short_text

def generate_authors_descriptions(names_list, main_text, authors_notes):
    """
    Génère un paragraphe descriptif pour chaque auteur validé, en se basant
    sur le texte principal 'main_text' et sur des instructions spécifiques 'authors_notes'.
    Retourne une liste de dictionnaires : [{"name": ..., "paragraph": ...}, ...]
    """
    results = []
    # On ne décrit que les auteurs validés
    validated_authors = [item for item in names_list if item["validated"]]

    for author in validated_authors:
        author_name = author["name"]
        prompt_user = f"""
        Voici le texte principal "Qui sommes-nous ?" : 
        {main_text}

        Maintenant, rédige un court paragraphe (texte brut) pour présenter l'auteur suivant : {author_name}.
        Si possible, garde une cohérence avec ce qui a été dit dans le texte principal.

        Notes ou précisions sur l'auteur (ou style à adopter) : {authors_notes if authors_notes else "Aucune précision"}

        Ne mets aucune balise HTML ou Markdown.
        """
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un assistant spécialisé en rédaction SEO. "
                            "Tu dois créer une petite présentation (un paragraphe) "
                            "pour un auteur, en texte brut."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt_user
                    }
                ],
                max_tokens=300,
                temperature=TEMPERATURE
            )
            paragraph = response.choices[0].message.content.strip()
            paragraph = strip_html_tags(paragraph)
        except Exception as e:
            paragraph = f"Erreur : {str(e)}"

        results.append({"name": author_name, "paragraph": paragraph})

    return results

# =========================================================================
# APPLICATION STREAMLIT
# =========================================================================

def main():
    st.title("Générateur de page \"Qui sommes-nous ?\" (Texte brut) + Extras")

    global client
    # Récupération de la clé API
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # Variables de session
    if "names_list" not in st.session_state:
        st.session_state["names_list"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""
    # Nouveau : stocker un résumé court
    if "short_summary" not in st.session_state:
        st.session_state["short_summary"] = ""
    # Nouveau : stocker les descriptions individuelles
    if "authors_descriptions" not in st.session_state:
        st.session_state["authors_descriptions"] = []

    # =======================
    # 1) IDENTITÉS
    # =======================

    num_people = st.number_input(
        "Nombre de personnes à présenter",
        min_value=1, max_value=20, value=3
    )

    renseigner_manuellement = st.checkbox("Renseigner manuellement les auteurs ?", value=False)

    if renseigner_manuellement:
        st.write("**Veuillez saisir les auteurs :**")

        # Afficher un champ text_input pour chaque auteur
        for i in range(num_people):
            key_name = f"manual_author_{i}"
            st.text_input(
                label=f"Auteur {i+1}",
                key=key_name
            )

        if st.button("Valider auteurs manuels"):
            new_list = []
            for i in range(num_people):
                k = f"manual_author_{i}"
                val = st.session_state.get(k, "")
                new_list.append({"name": val, "validated": True})
            st.session_state["names_list"] = new_list
            st.session_state["description"] = ""
            st.session_state["short_summary"] = ""
            st.session_state["authors_descriptions"] = []

    else:
        also_lastname = st.checkbox("Générer aussi des noms (en plus des prénoms)", value=False)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Générer identités"):
                st.session_state["names_list"] = generate_names(num_people, also_lastname)
                st.session_state["description"] = ""
                st.session_state["short_summary"] = ""
                st.session_state["authors_descriptions"] = []
        with col2:
            if st.button("Régénérer identités (non validées)"):
                st.session_state["names_list"] = regenerate_unvalidated(st.session_state["names_list"], also_lastname)
                st.session_state["description"] = ""
                st.session_state["short_summary"] = ""
                st.session_state["authors_descriptions"] = []

    # Liste des identités
    if st.session_state["names_list"]:
        st.subheader("Identités générées / renseignées :")
        for index, item in enumerate(st.session_state["names_list"]):
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"{index+1}. {item['name']}")
            with cols[1]:
                is_checked = st.checkbox(
                    "Valider",
                    value=item["validated"],
                    key=f"validate_{index}"
                )
                item["validated"] = is_checked

    # =======================
    # 2) PAGE "QUI SOMMES-NOUS ?" 
    # =======================

    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")
    paragraphs = st.number_input("Nombre de paragraphes (2 par défaut si non renseigné)",
                                 min_value=1, max_value=10, value=2)
    tone = st.text_input("Tonalité du texte (ex. humoristique, formel, sérieux...)")
    custom_instructions = st.text_area(
        "Instructions supplémentaires (optionnel)",
        help="Donnez des consignes précises : style, vocabulaire, etc."
    )

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
            # On réinitialise le résumé court et les descriptions auteurs
            st.session_state["short_summary"] = ""
            st.session_state["authors_descriptions"] = []
    with col_desc_2:
        if st.button("Régénérer la description"):
            st.session_state["description"] = generate_description(
                st.session_state["names_list"],
                theme,
                paragraphs,
                tone,
                custom_instructions
            )
            st.session_state["short_summary"] = ""
            st.session_state["authors_descriptions"] = []

    # Affichage principal
    st.markdown("### Description (texte brut) - Page \"Qui sommes-nous ?\"")
    st.text_area(label="", value=st.session_state["description"], height=300)

    # =======================
    # 3) RÉSUMÉ COURT (2-3 PHRASES)
    # =======================

    st.markdown("### Résumé court (2-3 phrases)")
    if st.session_state["description"]:
        # Bouton pour générer le résumé
        if st.button("Générer un résumé court"):
            st.session_state["short_summary"] = generate_short_summary(
                st.session_state["description"],
                theme,
                tone
            )
        st.text_area(
            label="Résumé de la page (2-3 phrases)",
            value=st.session_state["short_summary"],
            height=150
        )
    else:
        st.info("Générez d'abord la page 'Qui sommes-nous ?' pour créer un résumé court.")

    # =======================
    # 4) DESCRIPTIONS AUTEURS
    # =======================

    st.markdown("### Descriptions individuelles des auteurs")
    if st.session_state["description"]:
        authors_notes = st.text_area(
            "Précisions sur les auteurs (optionnel)",
            help="Donnez des consignes particulières : style d'écriture, contexte, etc."
        )

        if st.button("Générer descriptions individuelles"):
            # On génère un paragraphe par auteur validé
            st.session_state["authors_descriptions"] = generate_authors_descriptions(
                st.session_state["names_list"],
                st.session_state["description"],
                authors_notes
            )

        # Afficher les paragraphes
        if st.session_state["authors_descriptions"]:
            for author_info in st.session_state["authors_descriptions"]:
                author_name = author_info["name"]
                paragraph = author_info["paragraph"]
                st.subheader(f"Description pour {author_name}")
                st.text_area(label="", value=paragraph, height=150)
    else:
        st.info("Générez d'abord la page 'Qui sommes-nous ?' pour créer des descriptions auteurs.")

if __name__ == "__main__":
    main()
