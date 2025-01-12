import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
from faker import Faker

# =========================================================================
# CONFIGURATION
# =========================================================================

# Modèle, tokens, temperature, etc. adaptés selon tes besoins
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
        if not item["validated"]:  # si pas validé, on régénère
            if also_lastname:
                item["name"] = random_full_name()
            else:
                item["name"] = random_first_name()
    return names_list

def generate_description(names_list, theme, paragraphs, tone, custom_instructions):
    """
    Génère le texte "Qui sommes-nous ?" en texte brut.
    On utilise le client OpenAI (chat.completions.create) au même format
    que dans l’exemple fourni.
    """
    # Extraire la liste des noms
    only_names = [item["name"] for item in names_list]

    # Construisons le contenu (prompt) que l'on va passer en "user"
    user_content = f"""
    Rédige une présentation (texte brut) pour la page "Qui sommes-nous ?" d'un site.
    Nous avons {len(only_names)} auteur(s) : {', '.join(only_names)}.
    Thématique du site : {theme if theme else "non spécifiée"}.
    Ton : {tone if tone else "non spécifié"}.
    Nombre de paragraphes souhaités : {paragraphs}.

    Génère {paragraphs} paragraphes (séparés par des sauts de ligne).

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
    except Exception as e:
        generated_text = f"Erreur lors de la génération : {str(e)}"

    return generated_text

def copy_to_clipboard(text: str):
    """Copie le texte (brut) dans le presse-papiers via le navigateur."""
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
    global client
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # 2) Variables de session pour stocker les identités et la description
    if "names_list" not in st.session_state:
        st.session_state["names_list"] = []
    if "description" not in st.session_state:
        st.session_state["description"] = ""

    # 3) Saisie du nombre de personnes
    num_people = st.number_input(
        "Nombre de personnes à présenter",
        min_value=1, max_value=20, value=3
    )

    # 4) Case pour générer aussi les noms de famille
    also_lastname = st.checkbox("Générer aussi des noms (en plus des prénoms)", value=False)

    # 5) Boutons pour générer ou régénérer les identités
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Générer identités"):
            st.session_state["names_list"] = generate_names(num_people, also_lastname)
            st.session_state["description"] = ""  # Reset description si on régénère
    with col2:
        if st.button("Régénérer identités (non validées)"):
            st.session_state["names_list"] = regenerate_unvalidated(st.session_state["names_list"], also_lastname)
            st.session_state["description"] = ""  # Reset description si on régénère

    # 6) Affichage des identités générées, chacune avec une case à cocher
    if st.session_state["names_list"]:
        st.subheader("Identités générées :")
        # On va faire un formulaire ou juste des checkboxes
        for index, item in enumerate(st.session_state["names_list"]):
            # On crée une clé unique pour la checkbox
            checkbox_label = f"Valider ?_{index}"
            # Afficher la checkbox et le nom
            cols = st.columns([3, 1])  # nom + checkbox
            with cols[0]:
                st.write(f"{index+1}. {item['name']}")
            with cols[1]:
                # On stocke le statut de validation dans la session
                # pour chaque item, en fonction de la checkbox
                is_checked = st.checkbox(
                    label="",
                    value=item["validated"],
                    key=checkbox_label
                )
                item["validated"] = is_checked

    # 7) Thématique du site
    theme = st.text_input("Thématique du site (ex. cuisine, technologie, mode...)")

    # 8) Nombre de paragraphes
    paragraphs = st.number_input(
        "Nombre de paragraphes (2 par défaut si non renseigné)",
        min_value=1, max_value=10, value=2
    )

    # 9) Ton (optionnel)
    tone = st.text_input("Tonalité du texte (ex. humoristique, formel, sérieux...)")

    # 10) Instructions supplémentaires (optionnelles)
    custom_instructions = st.text_area(
        "Instructions supplémentaires (optionnel)",
        help="Donnez des consignes précises à OpenAI. Par ex. style littéraire, vocabulaire spécifique, etc."
    )

    # 11) Bouton pour générer la description (texte brut)
    if st.button("Générer la description"):
        st.session_state["description"] = generate_description(
            st.session_state["names_list"],
            theme,
            paragraphs,
            tone,
            custom_instructions
        )

    # 12) Affichage du texte en brut
    st.markdown("### Description générée (texte brut)")
    st.text(st.session_state["description"])

    # 13) Boutons : Copier / Régénérer
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

# Point d'entrée
if __name__ == "__main__":
    main()
