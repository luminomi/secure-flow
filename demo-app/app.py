"""
Secure Flow demo app -- INTENTIONALLY VULNERABLE. DO NOT DEPLOY.

This app exists only to give the Secure Flow pipeline something to catch.
Every planted flaw is tagged with a "VULN-n" comment:

  VULN-1  SQL injection            -> caught by Semgrep (SAST)
  VULN-2  Hardcoded secret         -> caught by Gitleaks (secret scanning, later phase)
  VULN-3  Outdated dependency/CVE  -> see requirements.txt, caught by Trivy (later phase)
"""
import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "users.db"

# VULN-2: Hardcoded secret. This key is FAKE and grants access to nothing;
# it is planted so the secret-scanning stage has something to find.
# Fix: load it at runtime instead, e.g. os.environ["PAYMENT_API_KEY"].
PAYMENT_API_KEY = "Xk7pQ2mZ9vR4tL8wN3bY6cH1jF5sD0gA"


def init_db():
    """Create a small SQLite database with sample users."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    )
    conn.execute("DELETE FROM users")
    conn.executemany(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [("alice", "alice@example.com"), ("bob", "bob@example.com")],
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return "Secure Flow demo app. Try /user?name=alice"


@app.route("/user")
def get_user():
    name = request.args.get("name", "")
    conn = sqlite3.connect(DB_PATH)

    # VULN-1: SQL injection. User input is pasted straight into the SQL text,
    # so /user?name=' OR '1'='1 returns every row in the table.
    # Fix: use a parameterized query so the input is treated as data, not SQL:
    #   conn.execute("SELECT id, name, email FROM users WHERE name = ?", (name,))
    rows = conn.execute(f"SELECT id, name, email FROM users WHERE name = '{name}'").fetchall()

    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])


init_db()

if __name__ == "__main__":
    app.run(port=5000)
