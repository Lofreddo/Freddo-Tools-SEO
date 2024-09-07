import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import openpyxl

# Fonction principale qui sera appelée depuis main.py
def main():
    # Interface Streamlit
    st.title("Analyse de similarité de textes")

    # Upload du fichier
    uploaded_file = st.file_uploader("Téléchargez un fichier CSV ou Excel", type=["csv", "xlsx"])

    if uploaded_file:
        # Lire le fichier uploadé
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Sélectionner la colonne contenant les textes
        colonnes = df.columns.tolist()
        colonne_texte = st.selectbox("Sélectionnez la colonne contenant les textes à analyser", colonnes)

        # Sélection du seuil de similarité
        seuil_similarite = st.selectbox("Sélectionnez un pourcentage de similarité", [10, 20, 30, 40, 50, 60, 70, 80, 90])

        if st.button("Lancer l'analyse"):
            # Extraire les textes de la colonne sélectionnée
            textes = df[colonne_texte].astype(str).tolist()

            # Calcul de la matrice de similarité cosinus
            vecteur = TfidfVectorizer().fit_transform(textes)
            matrice_similarite = cosine_similarity(vecteur, vecteur)

            # Trouver les deux textes les plus similaires
            similarite_max = np.max(matrice_similarite[np.triu_indices(len(textes), k=1)])
            indices_max = np.unravel_index(np.argmax(matrice_similarite, axis=None), matrice_similarite.shape)
            texte_1 = textes[indices_max[0]]
            texte_2 = textes[indices_max[1]]

            # Calculer la similarité moyenne
            similarite_moyenne = np.mean(matrice_similarite[np.triu_indices(len(textes), k=1)])

            # Filtrer les textes avec une similarité supérieure au seuil
            seuil_similarite_normalise = seuil_similarite / 100
            indices_textes_similaires = np.where(matrice_similarite > seuil_similarite_normalise)
            resultat = set()
            for i, j in zip(indices_textes_similaires[0], indices_textes_similaires[1]):
                if i != j:
                    resultat.add(i)
                    resultat.add(j)

            # Générer le fichier de sortie
            generer_fichier_sortie(df, similarite_moyenne, texte_1, texte_2, similarite_max, seuil_similarite, resultat)


# Fonction pour générer le fichier de sortie
def generer_fichier_sortie(df, similarite_moyenne, texte_1, texte_2, taux_max, seuil, resultat):
    # Créer un fichier Excel avec deux onglets
    with pd.ExcelWriter('resultats_similarite.xlsx', engine='openpyxl') as writer:
        # Onglet 1 : Statistiques de similarité
        stats = pd.DataFrame({
            'Taux de similarité moyen': [similarite_moyenne],
            'Taux de similarité maximum': [taux_max],
            'Texte 1': [texte_1],
            'Texte 2': [texte_2]
        })
        stats.to_excel(writer, sheet_name='Statistiques', index=False)
        
        # Onglet 2 : Résultats filtrés
        df_resultat = df.loc[resultat]
        df_resultat.to_excel(writer, sheet_name=f'Textes > {seuil}%', index=False)

    st.success("Le fichier a été généré avec succès : resultats_similarite.xlsx")
