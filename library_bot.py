import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
filters,
ContextTypes,
ConversationHandler,
)

# =============================================

# НАСТРОЙКИ

# =============================================

BOT_TOKEN = os.environ.get(“BOT_TOKEN”, “”)
ADMIN_ID = int(os.environ.get(“ADMIN_ID”, “0”))

BOOKS_DIR = “books”
COURSES_FILE = “courses.json”  # Файл где хранятся курсы

# =============================================

# ЛОГИРОВАНИЕ

# =============================================

logging.basicConfig(
format=”%(asctime)s - %(name)s - %(levelname)s - %(message)s”,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# =============================================

# СОСТОЯНИЯ

# =============================================

CHOOSE_COURSE, SEARCH_BOOK = range(2)
ADDING_COURSE = 10

# =============================================

# РАБОТА С КУРСАМИ (сохраняются в файл)

# =============================================

def load_courses() -> dict:
“”“Загружает список курсов из файла.”””
if os.path.exists(COURSES_FILE):
with open(COURSES_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
# Курсы по умолчанию если файла нет
default = {
“📚 1 курс”: “1_kurs”,
“📚 2 курс”: “2_kurs”,
}
save_courses(default)
return default

def save_courses(courses: dict):
“”“Сохраняет список курсов в файл.”””
with open(COURSES_FILE, “w”, encoding=“utf-8”) as f:
json.dump(courses, f, ensure_ascii=False, indent=2)

def add_course(name: str) -> str:
“”“Добавляет новый курс. Возвращает имя папки.”””
courses = load_courses()
folder = name.lower().replace(” “, “*”).replace(”/”, “*”)
label = f”📚 {name}”
courses[label] = folder
save_courses(courses)
os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)
return folder

# =============================================

# РАБОТА С КНИГАМИ

# =============================================

def get_all_books(course_folder=None):
courses = load_courses()
folders = [course_folder] if course_folder else list(courses.values())
books = []
for folder in folders:
path = os.path.join(BOOKS_DIR, folder)
if not os.path.exists(path):
continue
for filename in os.listdir(path):
if filename.endswith(”.pdf”):
name = filename.replace(”.pdf”, “”)
parts = name.split(”_”, 1)
title = parts[0] if len(parts) > 0 else name
author = parts[1] if len(parts) > 1 else “Неизвестен”
books.append({
“title”: title,
“author”: author,
“filename”: filename,
“folder”: folder,
“path”: os.path.join(path, filename),
})
return books

def search_books(query, course_folder=None):
query = query.lower().strip()
return [
b for b in get_all_books(course_folder)
if query in b[“title”].lower() or query in b[“author”].lower()
]

# =============================================

# КЛАВИАТУРЫ

# =============================================

def course_keyboard():
courses = load_courses()
buttons = [[KeyboardButton(label)] for label in courses.keys()]
buttons.append([KeyboardButton(“🔍 Искать по всем курсам”)])
return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_keyboard():
return ReplyKeyboardMarkup([
[KeyboardButton(“➕ Добавить курс”)],
[KeyboardButton(“📋 Список курсов”)],
[KeyboardButton(“🔙 Назад”)],
], resize_keyboard=True)

# =============================================

# ОБРАБОТЧИКИ — ПОЛЬЗОВАТЕЛЬ

# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
if user_id == ADMIN_ID:
await update.message.reply_text(
“👋 Привет, администратор!\n\nВыбери действие:”,
reply_markup=ReplyKeyboardMarkup([
[KeyboardButton(“📖 Поиск книг”)],
[KeyboardButton(“⚙️ Управление курсами”)],
], resize_keyboard=True)
)
else:
await update.message.reply_text(
“👋 Привет! Я бот библиотеки.\n\n”
“📖 Найду и отправлю нужную книгу в PDF.\n\n”
“Выбери курс:”,
reply_markup=course_keyboard()
)
return CHOOSE_COURSE

async def choose_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
courses = load_courses()

```
# Админ меню
if text == "⚙️ Управление курсами":
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "⚙️ Управление курсами:",
            reply_markup=admin_keyboard()
        )
        return CHOOSE_COURSE

if text == "📖 Поиск книг":
    await update.message.reply_text("Выбери курс:", reply_markup=course_keyboard())
    return CHOOSE_COURSE

if text == "➕ Добавить курс":
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "Напиши название нового курса.\nНапример: *3 курс* или *Магистратура*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Назад")]], resize_keyboard=True)
        )
        return ADDING_COURSE

if text == "📋 Список курсов":
    courses = load_courses()
    if not courses:
        await update.message.reply_text("Курсов пока нет.")
    else:
        text_list = "\n".join([f"• {label}" for label in courses.keys()])
        await update.message.reply_text(f"📋 Текущие курсы:\n\n{text_list}", reply_markup=admin_keyboard())
    return CHOOSE_COURSE

if text == "🔙 Назад":
    await start(update, context)
    return CHOOSE_COURSE

if text == "🔍 Искать по всем курсам":
    context.user_data["course_folder"] = None
    course_name = "всех курсов"
elif text in courses:
    context.user_data["course_folder"] = courses[text]
    course_name = text
else:
    await update.message.reply_text(
        "Выбери курс с помощью кнопок.",
        reply_markup=course_keyboard()
    )
    return CHOOSE_COURSE

await update.message.reply_text(
    f"✅ Выбрано: {course_name}\n\n🔍 Напиши название книги или имя автора:",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("🔙 Назад к выбору курса")]],
        resize_keyboard=True
    )
)
return SEARCH_BOOK
```

async def adding_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

```
if text == "🔙 Назад":
    await update.message.reply_text("⚙️ Управление курсами:", reply_markup=admin_keyboard())
    return CHOOSE_COURSE

folder = add_course(text)
await update.message.reply_text(
    f"✅ Курс *{text}* добавлен!\n"
    f"Папка для книг: `books/{folder}/`\n\n"
    f"Загрузи PDF файлы в эту папку на сервере.",
    parse_mode="Markdown",
    reply_markup=admin_keyboard()
)
return CHOOSE_COURSE
```

async def search_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
courses = load_courses()

```
if text == "🔙 Назад к выбору курса":
    await update.message.reply_text("Выбери курс:", reply_markup=course_keyboard())
    return CHOOSE_COURSE

course_folder = context.user_data.get("course_folder")
results = search_books(text, course_folder)

if not results:
    await update.message.reply_text(
        f"❌ По запросу «{text}» ничего не найдено.\n\nПопробуй другое название или автора:"
    )
    return SEARCH_BOOK

if len(results) == 1:
    book = results[0]
    await update.message.reply_text(
        f"📖 Найдено: *{book['title']}*\nАвтор: {book['author']}\n\nОтправляю...",
        parse_mode="Markdown"
    )
    try:
        with open(book["path"], "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=book["filename"],
                caption=f"📖 {book['title']} — {book['author']}"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await update.message.reply_text("⚠️ Не удалось отправить файл. Обратись к администратору.")
else:
    response = f"📚 Найдено книг: {len(results)}\n\n"
    for i, book in enumerate(results[:10], 1):
        label = [k for k, v in courses.items() if v == book["folder"]]
        label = label[0] if label else book["folder"]
        response += f"{i}. *{book['title']}* — {book['author']} ({label})\n"
    response += "\nУточни запрос для точного поиска:"
    await update.message.reply_text(response, parse_mode="Markdown")

return SEARCH_BOOK
```

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“ℹ️ *Как пользоваться ботом:*\n\n”
“1️⃣ /start — начать\n”
“2️⃣ Выбери курс\n”
“3️⃣ Напиши название книги или автора\n”
“4️⃣ Получи PDF файл\n\n”
“*Формат файлов:* `Название_Автор.pdf`\n”
“Пример: `Математика_Иванов.pdf`”,
parse_mode=“Markdown”
)

# =============================================

# ЗАПУСК

# =============================================

def main():
os.makedirs(BOOKS_DIR, exist_ok=True)
# Создаём папки для существующих курсов
for folder in load_courses().values():
os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)

```
app = Application.builder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSE_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_course)],
        SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_and_send)],
        ADDING_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adding_course)],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(conv)
app.add_handler(CommandHandler("help", help_command))

logger.info("Бот запущен!")
app.run_polling()
```

if **name** == “**main**”:
main()