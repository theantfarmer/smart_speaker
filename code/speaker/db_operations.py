import sqlite3

def connect_db():
    return sqlite3.connect("gpt_chat_history.db")

def initialize_db():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()

def save_to_db(role, content):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        conn.commit()

def save_conversation(user_text, agent_text):
    save_to_db('User', user_text)
    save_to_db('Agent', agent_text)
