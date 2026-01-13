from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_NAME = "cafe.db"

# ===========================
# DATABASE SETUP
# ===========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Cabins
    c.execute("""
        CREATE TABLE IF NOT EXISTS cabins (
            cabin_id INTEGER PRIMARY KEY,
            status TEXT,
            in_time TEXT,
            out_time TEXT
        )
    """)

    # Orders (temporary)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cabin_id INTEGER,
            item TEXT,
            price INTEGER
        )
    """)

    # Daily / Monthly Report (permanent)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            cabin_id INTEGER,
            duration REAL,
            total_bill INTEGER
        )
    """)

    # Create 5 cabins
    c.execute("SELECT COUNT(*) FROM cabins")
    if c.fetchone()[0] < 5:
        for i in range(1, 6):
            c.execute(
                "INSERT OR IGNORE INTO cabins (cabin_id, status) VALUES (?, ?)",
                (i, "Free")
            )

    conn.commit()
    conn.close()

init_db()

# ===========================
# HOME
# ===========================
@app.route("/")
def home():
    return render_template("home.html")

# ===========================
# DASHBOARD
# ===========================
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT cabin_id, status FROM cabins")
    cabins = c.fetchall()
    conn.close()
    return render_template("dashboard.html", cabins=cabins)

# ===========================
# RESERVE CABIN
# ===========================
@app.route("/reserve/<int:cabin_id>")
def reserve(cabin_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        UPDATE cabins
        SET status=?, in_time=?, out_time=?
        WHERE cabin_id=?
    """, ("Reserved", now, None, cabin_id))

    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# ===========================
# TAKE ORDER (MULTI ITEM)
# ===========================
@app.route("/order/<int:cabin_id>", methods=["GET", "POST"])
def order(cabin_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if request.method == "POST":
        items = request.form.getlist("items")
        prices = request.form.getlist("prices")

        for item, price in zip(items, prices):
            c.execute(
                "INSERT INTO orders (cabin_id, item, price) VALUES (?, ?, ?)",
                (cabin_id, item, int(price))
            )
        conn.commit()

    c.execute("SELECT item, price FROM orders WHERE cabin_id=?", (cabin_id,))
    orders = c.fetchall()
    conn.close()

    return render_template("order.html", cabin_id=cabin_id, orders=orders)

# ===========================
# CHECKOUT / BILL
# ===========================
@app.route("/checkout/<int:cabin_id>")
def checkout(cabin_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Orders
    c.execute("SELECT item, price FROM orders WHERE cabin_id=?", (cabin_id,))
    orders = c.fetchall()
    food_total = sum(o[1] for o in orders)

    # Time calculation
    c.execute("SELECT in_time FROM cabins WHERE cabin_id=?", (cabin_id,))
    in_time_str = c.fetchone()[0]

    duration_hours = 0
    cabin_bill = 0

    if in_time_str:
        in_time = datetime.strptime(in_time_str, "%Y-%m-%d %H:%M:%S")
        out_time = datetime.now()
        duration = out_time - in_time
        duration_hours = duration.total_seconds() / 3600

        cabin_bill = 200
        if duration_hours > 1:
            extra_blocks = int((duration_hours - 1) / 0.5 + 0.999)
            cabin_bill += extra_blocks * 100

    total_bill = food_total + cabin_bill

    # ===========================
    # SAVE REPORT DATA (KEY)
    # ===========================
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        INSERT INTO daily_report (date, cabin_id, duration, total_bill)
        VALUES (?, ?, ?, ?)
    """, (today, cabin_id, round(duration_hours, 2), total_bill))

    # Reset cabin
    c.execute("""
        UPDATE cabins
        SET status=?, in_time=?, out_time=?
        WHERE cabin_id=?
    """, ("Free", None, None, cabin_id))

    # Clear orders
    c.execute("DELETE FROM orders WHERE cabin_id=?", (cabin_id,))

    conn.commit()
    conn.close()

    return render_template(
        "bill.html",
        cabin_id=cabin_id,
        orders=orders,
        cabin_bill=cabin_bill,
        total_order=food_total,
        total_bill=total_bill,
        duration=round(duration_hours, 2)
    )

# ===========================
# DAILY REPORT
# ===========================
@app.route("/daily-report")
def daily_report():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("""
        SELECT COUNT(*), IFNULL(SUM(total_bill), 0)
        FROM daily_report
        WHERE date=?
    """, (today,))
    couples, total_money = c.fetchone()

    c.execute("""
        SELECT cabin_id, duration, total_bill
        FROM daily_report
        WHERE date=?
    """, (today,))
    details = c.fetchall()

    conn.close()

    return render_template(
        "daily_report.html",
        date=today,
        couples=couples,
        total_money=total_money,
        details=details
    )

# ===========================
# MONTHLY REPORT
# ===========================
@app.route("/monthly-report")
def monthly_report():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    c.execute("""
        SELECT COUNT(*), IFNULL(SUM(total_bill), 0)
        FROM daily_report
        WHERE strftime('%Y-%m', date)=?
    """, (month,))
    couples, total_money = c.fetchone()

    c.execute("""
        SELECT cabin_id,
               COUNT(*) AS visits,
               SUM(total_bill) AS revenue
        FROM daily_report
        WHERE strftime('%Y-%m', date)=?
        GROUP BY cabin_id
    """, (month,))
    details = c.fetchall()

    conn.close()

    return render_template(
        "monthly_report.html",
        month=month,
        couples=couples,
        total_money=total_money,
        details=details
    )

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
