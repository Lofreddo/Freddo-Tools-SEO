import streamlit as st
import sqlite3
import pandas as pd
import tempfile

def run():
    st.title("Liste des Tables dans un Fichier Screaming Frog")

    # File uploader for .dbseospider file
    uploaded_file = st.file_uploader("Téléchargez votre fichier .dbseospider", type="dbseospider")

    if uploaded_file is not None:
        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name

        # Connect to the SQLite database
        conn = sqlite3.connect(temp_file_path)

        # List all tables in the database
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables_df = pd.read_sql_query(tables_query, conn)
        tables = tables_df['name'].tolist()

        # Display the list of tables
        st.header("Tables Disponibles")
        st.write(tables)

        # Close the connection and remove the temporary file
        conn.close()

if __name__ == "__main__":
    run()
