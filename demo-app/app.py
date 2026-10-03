"""
Secure Flow demo app -- FIXED version.

The vulnerable "before" version lives only in PR #1 (branch add-vulnerable-demo-app).
Each flaw from that version is fixed here and tagged with a matching "FIXED-n" comment:

  FIXED-1  SQL injection            -> parameterized query          (proved by Semgrep)
  FIXED-2  Hardcoded secret         -> read from environment        (proved by Gitleaks)
  FIXED-3  Outdated dependencies    -> see requirements.txt         (proved by Trivy)
"""
import os
import sqlite3
import sys

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "users.db"

# FIXED-2: The secret is read from the environment at startup instead of being
# written in the code. If it is missing, stop immediately with a clear message
# rather than running half-configured.
PAYMENT_API_KEY = os.environ.get("PAYMENT_API_KEY")
if not PAYMENT_API_KEY:
    sys.exit(
        "ERROR: the PAYMENT_API_KEY environment variable is not set. "
        "Set it before starting the app."
    )


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

    # FIXED-1: Parameterized query. The "?" placeholder makes the database
    # driver pass the input separately as data, so it can never change the SQL.
    # /user?name=' OR '1'='1 now just looks for a user with that literal name.
    rows = conn.execute(
        "SELECT id, name, email FROM users WHERE name = ?", (name,)
    ).fetchall()

    conn.close()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2]} for r in rows])


init_db()

if __name__ == "__main__":
    app.run(port=5000)
