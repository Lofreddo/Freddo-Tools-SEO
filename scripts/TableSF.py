import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import os

def list_tables(uploaded_file):
    temp_file_path = None
    conn = None
    try:
        # Sauvegarder le fichier uploadé dans un emplacement temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dbseospider') as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name

        # Connexion à la base de données SQLite
        conn = sqlite3.connect(temp_file_path)
        cursor = conn.cursor()

        # Lister toutes les tables dans la base de données
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        return tables

    except sqlite3.Error as e:
        st.error(f"Erreur SQLite : {e}")
    except Exception as e:
        st.error(f"Une erreur inattendue s'est produite : {e}")
    finally:
        if conn:
            conn.close()
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    
    return []

def display_table_info(uploaded_file, table_name):
    temp_file_path = None
    conn = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dbseospider') as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name

        conn = sqlite3.connect(temp_file_path)
        
        # Obtenir les informations sur les colonnes
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns_info = cursor.fetchall()

        st.write(f"Colonnes de la table '{table_name}':")
        for col in columns_info:
            st.write(f"- {col[1]} ({col[2]})")

        # Afficher un aperçu des données
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
        st.write("Aperçu des données:")
        st.dataframe(df)

    except sqlite3.Error as e:
        st.error(f"Erreur SQLite lors de l'affichage des informations de la table : {e}")
    except Exception as e:
        st.error(f"Une erreur inattendue s'est produite lors de l'affichage des informations de la table : {e}")
    finally:
        if conn:
            conn.close()
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def main():
    st.title("Analyseur de Fichier Screaming Frog")

    uploaded_file = st.file_uploader("Téléchargez votre fichier .dbseospider", type="dbseospider")

    if uploaded_file is not None:
        tables = list_tables(uploaded_file)

        if tables:
            st.header("Tables Disponibles")
            for table in tables:
                st.write(f"- {table}")

            selected_table = st.selectbox("Sélectionnez une table pour voir plus d'informations", tables)
            if selected_table:
                display_table_info(uploaded_file, selected_table)
        else:
            st.warning("Aucune table trouvée dans le fichier ou une erreur s'est produite.")

def run():
    main()

if __name__ == "__main__":
    main()
