import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS cabins (
    id INTEGER PRIMARY KEY,
    status TEXT,
    in_time TEXT
)
""")

for i in range(1, 6):
    cur.execute("INSERT OR IGNORE INTO cabins VALUES (?, 'Free', NULL)", (i,))

db.commit()
db.close()

print("Database created successfully!")
