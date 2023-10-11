import sqlite3

conn = sqlite3.connect('gpt_chat_history.db')
c = conn.cursor()
c.execute('SELECT * FROM history')
print(c.fetchall())
