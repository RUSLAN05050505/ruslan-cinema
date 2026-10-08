from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "movies.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return "Ruslan Cinema API работает!"


@app.route("/api/movies")
def movies():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM movies ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()

    conn = get_db()
    rows = conn.execute(
        """
        SELECT * FROM movies
        WHERE title LIKE ? OR description LIKE ?
        ORDER BY id DESC
        """,
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
