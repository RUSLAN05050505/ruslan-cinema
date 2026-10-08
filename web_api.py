from flask import Flask, 
jsonify, request
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "movies.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return "Ruslan Cinema API работает!"


@app.route("/api/movies")
def movies():
    conn = get_db()

    rows = conn.execute("""
        SELECT id, title, description, photo_id,
               channel_username, post_link, created_at
        FROM movies
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = get_db()

    rows = conn.execute("""
        SELECT id, title, description, photo_id,
               channel_username, post_link, created_at
        FROM movies
        WHERE title LIKE ?
           OR description LIKE ?
        ORDER BY id DESC
    """, (f"%{query}%", f"%{query}%")).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
