import psycopg2
import streamlit as st

def connect_to_database():
    """Establishes a secure connection to the Cloud PostgreSQL database."""
    try:
        # Pulls the URL securely from secrets.toml (locally) or Streamlit Cloud Settings (in production)
        DATABASE_URL = st.secrets["DATABASE_URL"]
        connection = psycopg2.connect(DATABASE_URL)
        return connection
    except Exception as e:
        print(f"Cloud database connection error: {e}")
        return None