import re
import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
from faker import Faker

# =========================================================================
# CONFIGURATION
# =========================================================================

# Modèle, tokens, température, etc.
MODEL = "gpt-4o-mini"
MAX_TOKENS = 800
TEMPERATURE = 0.7

# Le client sera initialisé dans main()
client = None

# Instancier Faker pour générer noms/prénoms francophones
fake = Faker('fr_FR')


# =========================================================================
# FONCTIONS
# =========================================================================

def random_first_name():
    """Génère uniquement un prénom en français."""
    return fake.first_name()

def random_full_name():
    """Génère un nom complet francophone (prénom + nom)."""
    return fake.name()

def generate_names(num_people: int, also_lastname: bool):
    """
    Génère un certain nombre d'identités :
      - soit prénoms uniquement (also_lastname=False)
      - soit nom + prénom (also_lastname=True)
    Retourne une liste de dictionnaires : [{"name": ..., "validated": False}, ...]
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
    On précise au modèle de NE PAS générer de HTML et on retire toute balise éventuelle.
    """
    # Extraire la liste des noms
    only_names = [item["name"] for item in names_list]

    # Construisons le contenu (prompt) que l'on va passer en "user"
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
                        "Ta mission est de créer un texte 'Qui sommes-nous ?' "
                        "selon les informations fournies, en texte brut (pas de HTML)."
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

def copy_to_clipboard(text: str):
    """
    Copie le texte (brut) dans le presse-papiers via le navigateur,
    en utilisant un code JavaScript plus robuste pour gérer la Clipboard API.
    """
    # Pour éviter que les backticks n'interfèrent, on échappe les simples guillemets
    safe_text = text.replace("'", "\\'")
    components.html(
        f"""
        <script>
            const textToCopy = '{safe_text}';
            if (navigator && navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(textToCopy)
                    .then(() => {{
                        window.alert("Description copiée dans le presse-papiers !");
                    }})
                    .catch(err => {{
                        console.error("Erreur lors de la copie :", err);
                        window.alert("Impossible de copier automatiquement. Veuillez copier manuellement.");
                    }});
            }} else {{
                console.error("Clipboard API non disponible sur ce navigateur.");
                window.alert("Clipboard API non disponible. Veuillez copier manuellement.");
            }}
        </script>
        """,
        height=0,
        width=0
    )


# =========================================================================
# APPLICATION STREAMLIT
# =========================================================================

def main():
    st.title("Générateur de page \"Qui sommes-nous ?\" (Texte pur, sans HTML)")

    global client
    # Récupérer la clé API depuis les secrets (adaptation selon ta config)
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

    # Nouveau : Case pour renseigner manuellement les auteurs
    renseigner_manuellement = st.checkbox("Renseigner manuellement les auteurs ?", value=False)

    if renseigner_manuellement:
        st.write("Veuillez renseigner ci-dessous chaque auteur :")
        # On crée un champ par auteur
        for i in range(num_people):
            # Utiliser session_state pour mémoriser la saisie
            key_name = f"manual_author_{i}"
            if key_name not in st.session_state:
                st.session_state[key_name] = ""
            st.session_state[key_name] = st.text_input(
                f"Auteur {i+1}",
                value=st.session_state[key_name],
                key=key_name
            )

        if st.button("Valider auteurs manuels"):
            # On remplace names_list par ces auteurs, marqués comme validés
            new_list = []
            for i in range(num_people):
                name_val = st.session_state[f"manual_author_{i}"]
                new_list.append({"name": name_val, "validated": True})
            st.session_state["names_list"] = new_list
            st.session_state["description"] = ""  # reset la description

        # Si on renseigne manuellement, on n'affiche pas les boutons de génération auto
    else:
        # Case pour générer aussi le nom de famille
        also_lastname = st.checkbox("Générer aussi des noms (en plus des prénoms)", value=False)

        # Boutons de génération / régénération
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Générer identités"):
                st.session_state["names_list"] = generate_names(num_people, also_lastname)
                st.session_state["description"] = ""  # reset
        with col2:
            if st.button("Régénérer identités (non validées)"):
                st.session_state["names_list"] = regenerate_unvalidated(st.session_state["names_list"], also_lastname)
                st.session_state["description"] = ""  # reset

    # Liste des identités + checkboxes (uniquement si on a quelque chose à afficher)
    if st.session_state["names_list"]:
        st.subheader("Identités générées / renseignées :")
        for index, item in enumerate(st.session_state["names_list"]):
            checkbox_label = f"Valider ?_{index}"
            cols = st.columns([3, 1])
            with cols[0]:
                st.write(f"{index+1}. {item['name']}")
            with cols[1]:
                is_checked = st.checkbox(
                    label="",
                    value=item["validated"],
                    key=checkbox_label
                )
                item["validated"] = is_checked

    # Inputs : Thématique, paragraphes, ton, instructions
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")
    paragraphs = st.number_input(
        "Nombre de paragraphes (2 par défaut si non renseigné)",
        min_value=1, max_value=10, value=2
    )
    tone = st.text_input("Tonalité du texte (ex. humoristique, formel, sérieux...)")
    custom_instructions = st.text_area(
        "Instructions supplémentaires (optionnel)",
        help="Donnez des consignes précises (ex. style littéraire, vocabulaire, etc.)"
    )

    # Génération de la description
    if st.button("Générer la description"):
        st.session_state["description"] = generate_description(
            st.session_state["names_list"],
            theme,
            paragraphs,
            tone,
            custom_instructions
        )

    st.markdown("### Description générée (texte pur)")
    st.text(st.session_state["description"])

    # Boutons : Copier / Régénérer
    col_copy, col_regen = st.columns([1, 1])
    with col_copy:
        if st.button("Copier la description"):
            copy_to_clipboard(st.session_state["description"])
    with col_regen:
        if st.button("Régénérer la description"):
            st.session_state["description"] = generate_description(
                st.session_state["names_list"],
                theme,
                paragraphs,
                tone,
                custom_instructions
            )

if __name__ == "__main__":
    main()
