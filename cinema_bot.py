import sqlite3
from datetime import datetime
import os
import difflib

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("TOKEN")

CHANNEL_USERNAME = "KINOFLEKS05"
DB_NAME = "movies.db"

# Telegram ID администратора
ADMIN_ID = 5232991686

# Картинка приветствия
WELCOME_IMAGE = "welcome.png"

# Фильмов на одной странице
MOVIES_PER_PAGE = 10


# =========================
# БАЗА ДАННЫХ
# =========================

def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            channel_id INTEGER,
            message_id INTEGER,
            photo_id TEXT,
            channel_username TEXT,
            post_link TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(movies)")
    columns = [row[1] for row in cursor.fetchall()]

    if "channel_username" not in columns:
        cursor.execute(
            "ALTER TABLE movies ADD COLUMN channel_username TEXT"
        )

    if "post_link" not in columns:
        cursor.execute(
            "ALTER TABLE movies ADD COLUMN post_link TEXT"
        )

    conn.commit()
    conn.close()


# =========================
# ПОЛЬЗОВАТЕЛИ
# =========================

def save_user(user):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, username, first_name, created_at)
        VALUES (?, ?, ?, COALESCE(
            (SELECT created_at FROM users WHERE user_id = ?),
            ?
        ))
    """, (
        user.id,
        user.username,
        user.first_name,
        user.id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def count_users():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()[0]

    conn.close()
    return result


# =========================
# ФИЛЬМЫ
# =========================

def add_movie(
    title,
    description,
    channel_id,
    message_id,
    photo_id,
    channel_username,
    post_link
):
    conn = get_db()
    cursor = conn.cursor()

    # Проверяем, есть ли уже этот Telegram-пост
    cursor.execute("""
        SELECT id
        FROM movies
        WHERE channel_id = ? AND message_id = ?
    """, (channel_id, message_id))

    existing = cursor.fetchone()

    if existing:
        conn.close()

        print(
            f"⚠️ Этот пост уже есть в базе. "
            f"ID фильма: {existing[0]}"
        )

        return existing[0]

    cursor.execute("""
        INSERT INTO movies
        (
            title,
            description,
            channel_id,
            message_id,
            photo_id,
            channel_username,
            post_link,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        description,
        channel_id,
        message_id,
        photo_id,
        channel_username,
        post_link,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    movie_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return movie_id


def get_movie(movie_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            description,
            photo_id,
            post_link,
            created_at
        FROM movies
        WHERE id = ?
    """, (movie_id,))

    result = cursor.fetchone()

    conn.close()

    return result


def search_movies(query):
    conn = get_db()
    cursor = conn.cursor()

    query = query.strip()

    cursor.execute("""
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
    """, (
        f"%{query}%",
        f"%{query}%"
    ))

    results = cursor.fetchall()

    conn.close()

    # Если точного совпадения нет,
    # пробуем найти похожие названия
    if not results:

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                title,
                description,
                photo_id,
                post_link,
                created_at
            FROM movies
        """)

        all_movies = cursor.fetchall()

        conn.close()

        query_lower = query.lower()

        titles = [
            movie[1]
            for movie in all_movies
            if movie[1]
        ]

        close_titles = difflib.get_close_matches(
            query_lower,
            [title.lower() for title in titles],
            n=10,
            cutoff=0.45
        )

        for movie in all_movies:

            if movie[1].lower() in close_titles:
                results.append(movie)

    return results


def get_latest_movies(limit=10):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            description,
            photo_id,
            post_link,
            created_at
        FROM movies
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()

    conn.close()

    return results


def get_all_movies():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
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

    results = cursor.fetchall()

    conn.close()

    return results


def count_movies():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM movies")
    result = cursor.fetchone()[0]

    conn.close()

    return result


def count_today_movies():
    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT COUNT(*) FROM movies WHERE created_at LIKE ?",
        (today + "%",)
    )

    result = cursor.fetchone()[0]

    conn.close()

    return result


def delete_movie(movie_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM movies WHERE id = ?",
        (movie_id,)
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted > 0


# =========================
# КЛАВИАТУРЫ
# =========================

def main_keyboard(user_id=None):

    buttons = [
        ["🔎 Поиск", "🆕 Новинки"],
        ["🎬 Все фильмы"],
    ]

    if user_id == ADMIN_ID:
        buttons.append(["👑 Админ-панель"])

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )


def admin_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Статистика",
                callback_data="admin_stats"
            )
        ],
        [
            InlineKeyboardButton(
                "🎬 Список фильмов",
                callback_data="admin_movies"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Удалить фильм",
                callback_data="admin_delete_info"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# /START
# =========================

async def start(update, context):

    user = update.effective_user

    save_user(user)

    text = (
        "🎬 <b>Добро пожаловать в KINOFLEKS!</b>\n\n"
        "Здесь вы можете найти фильмы и сериалы.\n\n"
        "🔎 Используйте поиск по названию."
    )

    if os.path.exists(WELCOME_IMAGE):

        with open(WELCOME_IMAGE, "rb") as photo:

            await update.message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=main_keyboard(user.id)
            )

    else:

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(user.id)
        )


# =========================
# TELEGRAM ID
# =========================

async def user_id_command(update, context):

    await update.message.reply_text(
        f"🆔 Ваш Telegram ID:\n\n"
        f"<code>{update.effective_user.id}</code>",
        parse_mode="HTML"
    )


# =========================
# АДМИН-ПАНЕЛЬ
# =========================

async def admin_panel(update, context):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ У вас нет доступа к админ-панели."
        )

        return

    text = (
        "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выберите нужный раздел:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# ОТПРАВКА ФИЛЬМА
# =========================

async def send_movie(update, movie):

    (
        movie_id,
        title,
        description,
        photo_id,
        post_link,
        created_at
    ) = movie

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎬 Смотреть фильм",
                url=post_link
            )
        ]
    ])

    text = (
        f"🎬 <b>{title}</b>\n\n"
        f"{description}"
    )

    if photo_id:

        await update.message.reply_photo(
            photo=photo_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    else:

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


# =========================
# ПОИСК
# =========================

async def search_movies_command(update, context):

    await update.message.reply_text(
        "🔎 Напишите название фильма или сериала:"
    )

    context.user_data["waiting_search"] = True


# =========================
# НОВИНКИ
# =========================

async def show_latest(update):

    movies = get_latest_movies(10)

    if not movies:

        await update.message.reply_text(
            "📭 Пока фильмов нет."
        )

        return

    await update.message.reply_text(
        "🆕 <b>Последние фильмы:</b>",
        parse_mode="HTML"
    )

    for movie in movies:

        await send_movie(update, movie)


# =========================
# ВСЕ ФИЛЬМЫ
# =========================

async def show_all_movies(update, page=0):

    all_movies = get_all_movies()

    if not all_movies:

        await update.message.reply_text(
            "📭 Пока фильмов нет."
        )

        return

    total = len(all_movies)

    start_index = page * MOVIES_PER_PAGE
    end_index = start_index + MOVIES_PER_PAGE

    movies = all_movies[start_index:end_index]

    await update.message.reply_text(
        f"🎬 <b>Все фильмы</b>\n\n"
        f"Всего: <b>{total}</b>\n"
        f"Страница: <b>{page + 1}</b>",
        parse_mode="HTML"
    )

    for movie in movies:

        await send_movie(update, movie)

    keyboard = []

    if page > 0:

        keyboard.append(
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f"movies_page_{page - 1}"
            )
        )

    if end_index < total:

        keyboard.append(
            InlineKeyboardButton(
                "➡️ Далее",
                callback_data=f"movies_page_{page + 1}"
            )
        )

    if keyboard:

        await update.message.reply_text(
            "📚 Навигация:",
            reply_markup=InlineKeyboardMarkup(
                [keyboard]
            )
        )


# =========================
# ОБРАБОТКА ТЕКСТА
# =========================

async def text_handler(update, context):

    user = update.effective_user

    text = update.message.text.strip()

    save_user(user)

    if text == "👑 Админ-панель":

        if user.id == ADMIN_ID:

            await update.message.reply_text(
                "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
                "Выберите раздел:",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )

        else:

            await update.message.reply_text(
                "⛔ Доступ запрещён."
            )

        return

    if text == "🔎 Поиск":

        await search_movies_command(
            update,
            context
        )

        return

    if text == "🆕 Новинки":

        await show_latest(update)

        return

    if text == "🎬 Все фильмы":

        await show_all_movies(update)

        return

    if context.user_data.get("waiting_search"):

        context.user_data["waiting_search"] = False

        movies = search_movies(text)

        if not movies:

            await update.message.reply_text(
                f"❌ По запросу <b>{text}</b> "
                f"ничего не найдено.",
                parse_mode="HTML"
            )

            return

        await update.message.reply_text(
            f"🔎 Найдено: <b>{len(movies)}</b>",
            parse_mode="HTML"
        )

        for movie in movies:

            await send_movie(update, movie)

        return

    movies = search_movies(text)

    if movies:

        await update.message.reply_text(
            f"🔎 Найдено: <b>{len(movies)}</b>",
            parse_mode="HTML"
        )

        for movie in movies:

            await send_movie(update, movie)

    else:

        await update.message.reply_text(
            "❌ Ничего не найдено.\n\n"
            "Попробуйте другое название."
        )


# =========================
# CALLBACK АДМИН-ПАНЕЛИ
# =========================

async def callback_handler(update, context):

    query = update.callback_query

    user = query.from_user

    # Навигация по фильмам доступна всем
    if query.data.startswith("movies_page_"):

        try:
            page = int(
                query.data.replace(
                    "movies_page_",
                    ""
                )
            )
        except ValueError:
            await query.answer("Ошибка страницы.")
            return

        await query.answer()

        all_movies = get_all_movies()

        if not all_movies:
            await query.edit_message_text(
                "📭 Фильмов пока нет."
            )
            return

        total = len(all_movies)

        start_index = page * MOVIES_PER_PAGE
        end_index = start_index + MOVIES_PER_PAGE

        movies = all_movies[start_index:end_index]

        text = (
            f"🎬 <b>Все фильмы</b>\n\n"
            f"Всего: <b>{total}</b>\n"
            f"Страница: <b>{page + 1}</b>\n\n"
            "Выберите фильм ниже:"
        )

        keyboard = []

        for movie in movies:

            movie_id = movie[0]
            title = movie[1] or "Без названия"

            if len(title) > 35:
                title = title[:35] + "..."

            keyboard.append([
                InlineKeyboardButton(
                    f"🎬 {title}",
                    url=movie[4]
                )
            ])

        navigation = []

        if page > 0:

            navigation.append(
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data=f"movies_page_{page - 1}"
                )
            )

        if end_index < total:

            navigation.append(
                InlineKeyboardButton(
                    "➡️ Далее",
                    callback_data=f"movies_page_{page + 1}"
                )
            )

        if navigation:
            keyboard.append(navigation)

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    await query.answer()

    if user.id != ADMIN_ID:

        await query.answer(
            "⛔ Доступ запрещён.",
            show_alert=True
        )

        return

    data = query.data

    if data == "admin_panel":

        await query.edit_message_text(
            "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
            "Выберите раздел:",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        return

    if data == "admin_stats":

        users = count_users()
        movies = count_movies()
        today = count_today_movies()

        text = (
            "📊 <b>СТАТИСТИКА</b>\n\n"
            f"👥 Пользователей: <b>{users}</b>\n"
            f"🎬 Всего фильмов: <b>{movies}</b>\n"
            f"🆕 Добавлено сегодня: <b>{today}</b>"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="admin_panel"
                )
            ]
        ])

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        return

    if data == "admin_movies":

        movies = get_all_movies()

        if not movies:

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅️ Назад",
                        callback_data="admin_panel"
                    )
                ]
            ])

            await query.edit_message_text(
                "📭 Фильмов пока нет.",
                reply_markup=keyboard
            )

            return

        movies = movies[:30]

        keyboard = []

        for movie in movies:

            movie_id = movie[0]
            title = movie[1] or "Без названия"

            if len(title) > 35:
                title = title[:35] + "..."

            keyboard.append([
                InlineKeyboardButton(
                    f"🎬 {movie_id} — {title}",
                    callback_data=f"admin_movie_{movie_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="admin_panel"
            )
        ])

        await query.edit_message_text(
            f"🎬 <b>Фильмы</b>\n\n"
            f"Показаны последние {len(movies)} фильмов:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    if data.startswith("admin_movie_"):

        movie_id = int(
            data.replace(
                "admin_movie_",
                ""
            )
        )

        movie = get_movie(movie_id)

        if not movie:

            await query.answer(
                "Фильм не найден.",
                show_alert=True
            )

            return

        (
            _,
            title,
            description,
            photo_id,
            post_link,
            created_at
        ) = movie

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🗑 Удалить",
                    callback_data=f"admin_confirm_delete_{movie_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ К фильмам",
                    callback_data="admin_movies"
                )
            ]
        ])

        text = (
            f"🎬 <b>{title}</b>\n\n"
            f"🆔 ID: <code>{movie_id}</code>\n"
            f"📅 Добавлен: {created_at}\n\n"
            f"{description}"
        )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        return

    if data == "admin_delete_info":

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎬 Выбрать фильм",
                    callback_data="admin_movies"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data="admin_panel"
                )
            ]
        ])

        await query.edit_message_text(
            "🗑 <b>Удаление фильма</b>\n\n"
            "Выберите фильм из списка, "
            "затем нажмите кнопку «Удалить».",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        return

    if data.startswith("admin_confirm_delete_"):

        movie_id = int(
            data.replace(
                "admin_confirm_delete_",
                ""
            )
        )

        movie = get_movie(movie_id)

        if not movie:

            await query.answer(
                "Фильм уже удалён.",
                show_alert=True
            )

            return

        title = movie[1]

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Да, удалить",
                    callback_data=f"admin_delete_{movie_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"admin_movie_{movie_id}"
                )
            ]
        ])

        await query.edit_message_text(
            "⚠️ <b>Подтверждение удаления</b>\n\n"
            "Вы действительно хотите удалить:\n\n"
            f"🎬 <b>{title}</b>?",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        return

    if data.startswith("admin_delete_"):

        movie_id = int(
            data.replace(
                "admin_delete_",
                ""
            )
        )

        deleted = delete_movie(movie_id)

        if deleted:

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🎬 Список фильмов",
                        callback_data="admin_movies"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Админ-панель",
                        callback_data="admin_panel"
                    )
                ]
            ])

            await query.edit_message_text(
                "✅ <b>Фильм удалён!</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )

        else:

            await query.answer(
                "❌ Фильм не найден.",
                show_alert=True
            )

        return


# =========================
# АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ
# ИЗ TELEGRAM-КАНАЛА
# =========================

async def handle_channel_post(update, context):

    message = update.channel_post

    if not message:
        return

    # Проверяем канал
    if message.chat.username:

        username = message.chat.username

        if username.lower() != CHANNEL_USERNAME.lower():
            return

    else:
        return

    # Получаем текст или подпись к фото
    text = message.text or message.caption or ""

    if not text.strip():
        print("⚠️ Пост без текста пропущен.")
        return

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return

    # Первая строка = название
    title = lines[0]

    # Всё сообщение = описание
    description = text

    # Фото
    photo_id = None

    if message.photo:
        photo_id = message.photo[-1].file_id

    # Ссылка на пост
    post_link = (
        f"https://t.me/"
        f"{message.chat.username}/"
        f"{message.message_id}"
    )

    print("\n" + "=" * 45)
    print("📢 НОВЫЙ ПОСТ В КАНАЛЕ")
    print("=" * 45)

    print(f"ID канала: {message.chat.id}")
    print(f"ID сообщения: {message.message_id}")
    print(f"Название: {title}")

    if photo_id:
        print("🖼 Фото найдено")
    else:
        print("🖼 Фото нет")

    print(f"🔗 Ссылка: {post_link}")

    movie_id = add_movie(
        title=title,
        description=description,
        channel_id=message.chat.id,
        message_id=message.message_id,
        photo_id=photo_id,
        channel_username=message.chat.username,
        post_link=post_link
    )

    print(
        f"✅ Фильм сохранён! ID: {movie_id}"
    )

    print("=" * 45)


# =========================
# /DELETE
# =========================

async def delete_command(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Доступ запрещён."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Использование:\n\n"
            "/delete ID\n\n"
            "Например:\n"
            "/delete 5"
        )

        return

    try:

        movie_id = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ ID должен быть числом."
        )

        return

    if delete_movie(movie_id):

        await update.message.reply_text(
            f"✅ Фильм с ID {movie_id} удалён."
        )

    else:

        await update.message.reply_text(
            "❌ Фильм с таким ID не найден."
        )


# =========================
# ЗАПУСК БОТА
# =========================

def main():

    if not TOKEN:
        print("❌ Переменная TOKEN не установлена!")
        print("Установите TOKEN перед запуском бота.")
        return

    init_db()

    print("=" * 50)
    print("🎬 KINOFLEKS BOT")
    print("=" * 50)

    print("✅ База данных готова")
    print("👑 Администратор:", ADMIN_ID)
    print("📢 Канал:", CHANNEL_USERNAME)
    print("🖼 Приветственная картинка:", WELCOME_IMAGE)
    print("🚀 Бот запускается...")

    print("=" * 50)

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Команды
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("id", user_id_command)
    )

    app.add_handler(
        CommandHandler("admin", admin_panel)
    )

    app.add_handler(
        CommandHandler("delete", delete_command)
    )

    # Посты канала
    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL,
            handle_channel_post
        )
    )

    # Кнопки
    app.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # Текст
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print("🟢 Бот запущен!")
    print("Остановить: Ctrl+C")

    app.run_polling()


# =========================
# START
# =========================

if __name__ == "__main__":
    main()
