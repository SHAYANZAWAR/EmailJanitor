# db_utils.py
import sqlite3
import os

DB_NAME = 'processed_emails.db'

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def init_db():
    """Initializes the database by creating the processed_emails table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_emails (
            email_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized.")

def add_processed_email_id(email_id: str) -> None:
    """Adds an email ID to the processed_emails table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO processed_emails (email_id) VALUES (?)", (email_id,))
        conn.commit()
        # print(f"Email ID '{email_id}' marked as processed.")
    except sqlite3.IntegrityError:
        # This means the email_id already exists (PRIMARY KEY constraint)
        # print(f"Email ID '{email_id}' already in processed list.")
        pass # Silently ignore if already exists
    finally:
        conn.close()

def check_if_email_processed(email_id: str) -> bool:
    """Checks if an email ID exists in the processed_emails table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Initialize the database when this module is imported or run directly
init_db()