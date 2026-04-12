import logging
import os
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

# НАСТРОЙКИ — замени на свои данные

# =============================================

BOT_TOKEN = “8657476988:AAH1HZZDIw2ZmTOrAZS_RpgTiYwVPl0iPoI”

# Папка где лежат книги (файлы PDF)

# Структура папок:

# books/

# 1_kurs/

# Математика_Иванов.pdf

# 2_kurs/

# Физика_Петров.pdf

BOOKS_DIR = “books”

# =============================================

# ЛОГИРОВАНИЕ

# =============================================

logging.basicConfig(
format=”%(asctime)s - %(name)s - %(levelname)s - %(message)s”,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# =============================================

# СОСТОЯНИЯ ДИАЛОГА

# =============================================

CHOOSE_COURSE, SEARCH_BOOK = range(2)

# =============================================

# КУРСЫ

# =============================================

COURSES = {
“📚 1 курс”: “1_kurs”,
“📚 2 курс”: “2_kurs”,
“📚 3 курс”: “3_kurs”,
“📚 4 курс”: “4_kurs”,
}

# =============================================

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

# =============================================

def get_all_books(course_folder=None):
“”“Возвращает список всех книг. Если указан курс — только из него.”””
books = []
folders = [course_folder] if course_folder else list(COURSES.values())

```
for folder in folders:
    path = os.path.join(BOOKS_DIR, folder)
    if not os.path.exists(path):
        continue
    for filename in os.listdir(path):
        if filename.endswith(".pdf"):
            name = filename.replace(".pdf", "")
            parts = name.split("_", 1)
            title = parts[0] if len(parts) > 0 else name
            author = parts[1] if len(parts) > 1 else "Неизвестен"
            books.append({
                "title": title,
                "author": author,
                "filename": filename,
                "folder": folder,
                "path": os.path.join(path, filename),
            })
return books
```

def search_books(query, course_folder=None):
“”“Ищет книги по названию или автору.”””
query = query.lower().strip()
results = []
for book in get_all_books(course_folder):
if query in book[“title”].lower() or query in book[“author”].lower():
results.append(book)
return results

def course_keyboard():
“”“Клавиатура выбора курса.”””
buttons = [[KeyboardButton(course)] for course in COURSES.keys()]
buttons.append([KeyboardButton(“🔍 Искать по всем курсам”)])
return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# =============================================

# ОБРАБОТЧИКИ

# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“👋 Привет! Я бот библиотеки.\n\n”
“📖 Напиши название книги или имя автора — я найду и отправлю PDF.\n\n”
“Сначала выбери курс:”,
reply_markup=course_keyboard()
)
return CHOOSE_COURSE

async def choose_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

```
if text == "🔍 Искать по всем курсам":
    context.user_data["course_folder"] = None
    course_name = "всех курсов"
elif text in COURSES:
    context.user_data["course_folder"] = COURSES[text]
    course_name = text
else:
    await update.message.reply_text(
        "Пожалуйста, выбери курс с помощью кнопок.",
        reply_markup=course_keyboard()
    )
    return CHOOSE_COURSE

await update.message.reply_text(
    f"✅ Выбрано: {course_name}\n\n"
    "🔍 Напиши название книги или имя автора:",
    reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("🔙 Назад к выбору курса")]],
        resize_keyboard=True
    )
)
return SEARCH_BOOK
```

async def search_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

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
        label = [k for k, v in COURSES.items() if v == book["folder"]]
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
for folder in COURSES.values():
os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)

```
app = Application.builder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSE_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_course)],
        SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_and_send)],
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