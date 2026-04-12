import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.environ.get(“BOT_TOKEN”, “”)
ADMIN_ID = int(os.environ.get(“ADMIN_ID”, “0”))
BOOKS_DIR = “books”
COURSES_FILE = “courses.json”

logging.basicConfig(format=”%(asctime)s - %(name)s - %(levelname)s - %(message)s”, level=logging.INFO)
logger = logging.getLogger(**name**)

MAIN_MENU, SEARCH_BOOK, BROWSE_COURSE, ADDING_COURSE, ADDING_SUBJECT = 0, 1, 2, 3, 4

def load_courses():
if os.path.exists(COURSES_FILE):
with open(COURSES_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
default = {}
save_courses(default)
return default

def save_courses(courses):
with open(COURSES_FILE, “w”, encoding=“utf-8”) as f:
json.dump(courses, f, ensure_ascii=False, indent=2)

def get_books_in_folder(folder):
path = os.path.join(BOOKS_DIR, folder)
books = []
if not os.path.exists(path):
return books
for filename in os.listdir(path):
if filename.endswith(”.pdf”):
name = filename.replace(”.pdf”, “”)
parts = name.split(”_”, 1)
title = parts[0] if len(parts) > 0 else name
author = parts[1] if len(parts) > 1 else “”
books.append({“title”: title, “author”: author, “filename”: filename, “path”: os.path.join(path, filename)})
return books

def search_all_books(query):
courses = load_courses()
query = query.lower().strip()
results = []
for course_name, subjects in courses.items():
for subject_name, folder in subjects.items():
for book in get_books_in_folder(folder):
if query in book[“title”].lower() or query in book[“author”].lower() or query in subject_name.lower():
book[“course”] = course_name
book[“subject”] = subject_name
results.append(book)
return results

def main_keyboard(user_id):
courses = load_courses()
buttons = []
for course_name in courses.keys():
buttons.append([KeyboardButton(course_name)])
buttons.append([KeyboardButton(“Поиск книги”)])
if user_id == ADMIN_ID:
buttons.append([KeyboardButton(“Управление”)])
return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
await update.message.reply_text(
“Добро пожаловать в библиотеку!\n\nВыберите курс или воспользуйтесь поиском:”,
reply_markup=main_keyboard(user_id)
)
return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
courses = load_courses()
user_id = update.effective_user.id

```
if text == "Поиск книги":
    await update.message.reply_text(
        "Введите название книги или имя автора:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Назад")]], resize_keyboard=True)
    )
    return SEARCH_BOOK

if text == "Управление" and user_id == ADMIN_ID:
    buttons = [
        [KeyboardButton("Добавить курс")],
        [KeyboardButton("Добавить предмет")],
        [KeyboardButton("Назад")]
    ]
    await update.message.reply_text("Панель управления:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return ADDING_COURSE

if text in courses:
    context.user_data["current_course"] = text
    subjects = courses[text]
    if not subjects:
        await update.message.reply_text("В этом курсе пока нет предметов.", reply_markup=main_keyboard(user_id))
        return MAIN_MENU
    buttons = [[KeyboardButton(subject)] for subject in subjects.keys()]
    buttons.append([KeyboardButton("Назад")])
    await update.message.reply_text(f"{text} - выберите предмет:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return BROWSE_COURSE

await update.message.reply_text("Выберите курс или поиск:", reply_markup=main_keyboard(user_id))
return MAIN_MENU
```

async def browse_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
user_id = update.effective_user.id

```
if text == "Назад":
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard(user_id))
    return MAIN_MENU

courses = load_courses()
current_course = context.user_data.get("current_course")
if not current_course or current_course not in courses:
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard(user_id))
    return MAIN_MENU

subjects = courses[current_course]
if text in subjects:
    folder = subjects[text]
    books = get_books_in_folder(folder)
    if not books:
        await update.message.reply_text("В этом предмете пока нет книг.")
        return BROWSE_COURSE
    if len(books) == 1:
        book = books[0]
        await update.message.reply_text(f"Отправляю: {book['title']}")
        try:
            with open(book["path"], "rb") as f:
                await update.message.reply_document(document=f, filename=book["filename"], caption=f"{book['title']}")
        except Exception as e:
            logger.error(f"Oshibka: {e}")
            await update.message.reply_text("Не удалось отправить файл.")
    else:
        buttons = [[KeyboardButton(b["title"])] for b in books]
        buttons.append([KeyboardButton("Назад")])
        context.user_data["books"] = {b["title"]: b for b in books}
        await update.message.reply_text("Выберите книгу:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return BROWSE_COURSE

books = context.user_data.get("books", {})
if text in books:
    book = books[text]
    await update.message.reply_text(f"Отправляю: {book['title']}")
    try:
        with open(book["path"], "rb") as f:
            await update.message.reply_document(document=f, filename=book["filename"], caption=f"{book['title']}")
    except Exception as e:
        logger.error(f"Oshibka: {e}")
        await update.message.reply_text("Не удалось отправить файл.")
    return BROWSE_COURSE

await update.message.reply_text("Выберите предмет из списка.")
return BROWSE_COURSE
```

async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
user_id = update.effective_user.id

```
if text == "Назад":
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard(user_id))
    return MAIN_MENU

results = search_all_books(text)
if not results:
    await update.message.reply_text(f"По запросу '{text}' ничего не найдено. Попробуйте другой запрос:")
    return SEARCH_BOOK

if len(results) == 1:
    book = results[0]
    await update.message.reply_text(f"Найдено: {book['title']}\nОтправляю...")
    try:
        with open(book["path"], "rb") as f:
            await update.message.reply_document(document=f, filename=book["filename"], caption=f"{book['title']}")
    except Exception as e:
        logger.error(f"Oshibka: {e}")
        await update.message.reply_text("Не удалось отправить файл.")
else:
    buttons = [[KeyboardButton(b["title"])] for b in results[:10]]
    buttons.append([KeyboardButton("Назад")])
    context.user_data["search_results"] = {b["title"]: b for b in results[:10]}
    response = f"Найдено книг: {len(results)}\n\n"
    for i, book in enumerate(results[:10], 1):
        response += f"{i}. {book['title']} ({book['course']})\n"
    response += "\nВыберите книгу:"
    await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    context.user_data["in_search_results"] = True

return SEARCH_BOOK
```

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
user_id = update.effective_user.id
courses = load_courses()

```
if text == "Назад":
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard(user_id))
    return MAIN_MENU

if text == "Добавить курс":
    await update.message.reply_text(
        "Введите название курса (например: 1 курс):",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Назад")]], resize_keyboard=True)
    )
    context.user_data["admin_action"] = "add_course"
    return ADDING_SUBJECT

if text == "Добавить предмет":
    if not courses:
        await update.message.reply_text("Сначала добавьте курс!")
        return ADDING_COURSE
    buttons = [[KeyboardButton(c)] for c in courses.keys()]
    buttons.append([KeyboardButton("Назад")])
    await update.message.reply_text("Выберите курс для добавления предмета:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    context.user_data["admin_action"] = "select_course_for_subject"
    return ADDING_SUBJECT

return ADDING_COURSE
```

async def adding_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text
user_id = update.effective_user.id
courses = load_courses()
action = context.user_data.get(“admin_action”)

```
if text == "Назад":
    buttons = [[KeyboardButton("Добавить курс")], [KeyboardButton("Добавить предмет")], [KeyboardButton("Назад")]]
    await update.message.reply_text("Панель управления:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return ADDING_COURSE

if action == "add_course":
    if text not in courses:
        courses[text] = {}
        save_courses(courses)
        os.makedirs(os.path.join(BOOKS_DIR, text.replace(" ", "_")), exist_ok=True)
    await update.message.reply_text(f"Курс '{text}' добавлен!", reply_markup=main_keyboard(user_id))
    return MAIN_MENU

if action == "select_course_for_subject":
    if text in courses:
        context.user_data["selected_course"] = text
        context.user_data["admin_action"] = "add_subject"
        await update.message.reply_text(
            f"Введите название предмета для {text}:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Назад")]], resize_keyboard=True)
        )
    return ADDING_SUBJECT

if action == "add_subject":
    selected_course = context.user_data.get("selected_course")
    if selected_course and selected_course in courses:
        folder = f"{selected_course}_{text}".replace(" ", "_")
        courses[selected_course][text] = folder
        save_courses(courses)
        os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)
        await update.message.reply_text(
            f"Предмет '{text}' добавлен в {selected_course}!\nПапка для книг: books/{folder}/",
            reply_markup=main_keyboard(user_id)
        )
    return MAIN_MENU

return ADDING_SUBJECT
```

def main():
os.makedirs(BOOKS_DIR, exist_ok=True)
app = Application.builder().token(BOT_TOKEN).build()
conv = ConversationHandler(
entry_points=[CommandHandler(“start”, start)],
states={
MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_book)],
BROWSE_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, browse_course)],
ADDING_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel)],
ADDING_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adding_subject)],
},
fallbacks=[CommandHandler(“start”, start)],
)
app.add_handler(conv)
logger.info(“Bot zapuschen!”)
app.run_polling()

if **name** == “**main**”:
main()