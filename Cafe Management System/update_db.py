import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabin_id INTEGER,
    item TEXT,
    price INTEGER
)
""")

db.commit()
db.close()

print("Orders table created")
