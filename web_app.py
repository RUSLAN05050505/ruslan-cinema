from flask import Flask, jsonify, send_from_directory, send_file, request
import sqlite3
import os
import io
import urllib.request
import json

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "movies.db")
WEB_DIR = os.path.join(BASE_DIR, "cinema_web")

TOKEN = os.getenv("TOKEN")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/api/movies")
def movies():
    conn = get_db()

    cursor = conn.execute("""
        SELECT
            id,
            title,
            description,
            photo_id,
            post_link,
            created_at
        FROM movies
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    result = []

    for movie in rows:
        result.append({
            "id": movie["id"],
            "title": movie["title"],
            "description": movie["description"] or "",
            "photo_id": movie["photo_id"] or "",
            "post_link": movie["post_link"] or "",
            "created_at": movie["created_at"] or ""
        })

    return jsonify(result)


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = get_db()

    cursor = conn.execute("""
        SELECT
            id,
            title,
            description,
            photo_id,
            post_link,
            created_at
        FROM movies
        WHERE title LIKE ?
           OR description LIKE ?
        ORDER BY id DESC
    """, (f"%{query}%", f"%{query}%"))

    rows = cursor.fetchall()
    conn.close()

    result = []

    for movie in rows:
        result.append({
            "id": movie["id"],
            "title": movie["title"],
            "description": movie["description"] or "",
            "photo_id": movie["photo_id"] or "",
            "post_link": movie["post_link"] or "",
            "created_at": movie["created_at"] or ""
        })

    return jsonify(result)


@app.route("/api/photo/<path:photo_id>")
def photo(photo_id):
    if not TOKEN:
        return "TOKEN не установлен", 500

    try:
        # Получаем путь файла у Telegram
        api_url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={photo_id}"

        with urllib.request.urlopen(api_url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        if not data.get("ok"):
            return "Telegram не вернул файл", 404

        file_path = data["result"]["file_path"]

        # Скачиваем изображение
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

        with urllib.request.urlopen(file_url, timeout=30) as response:
            image_data = response.read()

        return send_file(
            io.BytesIO(image_data),
            mimetype="image/jpeg"
        )

    except Exception as e:
        print("Ошибка загрузки фото:", e)
        return "Ошибка загрузки изображения", 500


if __name__ == "__main__":
    print("🎬 Ruslan Cinema Web запущен!")
    print("🌐 http://127.0.0.1:8080")

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
