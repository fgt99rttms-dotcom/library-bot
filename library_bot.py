import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
ApplicationBuilder, CommandHandler, CallbackQueryHandler,
MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv(“BOT_TOKEN”)
ADMIN_ID = int(os.getenv(“ADMIN_ID”))
DATA_FILE = “courses.json”
PAGE_SIZE = 8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

def load_courses():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
return {}

def save_courses(data):
with open(DATA_FILE, “w”, encoding=“utf-8”) as f:
json.dump(data, f, ensure_ascii=False, indent=2)

courses = load_courses()
user_state = {}

def is_admin(user_id):
return user_id == ADMIN_ID

def courses_keyboard(page=0):
keys = list(courses.keys())
start = page * PAGE_SIZE
chunk = keys[start: start + PAGE_SIZE]
keyboard = [[InlineKeyboardButton(c, callback_data=“course|” + c + “|0”)] for c in chunk]
nav = []
if page > 0:
nav.append(InlineKeyboardButton(”<<”, callback_data=“coursepage|” + str(page - 1)))
if start + PAGE_SIZE < len(keys):
nav.append(InlineKeyboardButton(”>>”, callback_data=“coursepage|” + str(page + 1)))
if nav:
keyboard.append(nav)
return InlineKeyboardMarkup(keyboard)

def books_keyboard(course, page=0):
books = list(courses.get(course, {}).keys())
start = page * PAGE_SIZE
chunk = books[start: start + PAGE_SIZE]
keyboard = [[InlineKeyboardButton(b, callback_data=“book|” + course + “|” + b)] for b in chunk]
nav = []
if page > 0:
nav.append(InlineKeyboardButton(”<<”, callback_data=“bookpage|” + course + “|” + str(page - 1)))
if start + PAGE_SIZE < len(books):
nav.append(InlineKeyboardButton(”>>”, callback_data=“bookpage|” + course + “|” + str(page + 1)))
if nav:
keyboard.append(nav)
keyboard.append([InlineKeyboardButton(“Назад”, callback_data=“back_courses”)])
return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not courses:
await update.message.reply_text(“Курсов пока нет. Заходите позже!”)
return
await update.message.reply_text(“Выберите курс:”, reply_markup=courses_keyboard())

async def cmd_add_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.message.from_user.id):
return
user_state[update.message.from_user.id] = {“step”: “adding_course”}
await update.message.reply_text(“Введите название нового курса:”)

async def cmd_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.message.from_user.id):
return
if not courses:
await update.message.reply_text(“Сначала создайте хотя бы один курс (/addcourse).”)
return
user_state[update.message.from_user.id] = {“step”: “adding_book_course”}
await update.message.reply_text(“Введите название курса, в который добавить книгу:”)

async def cmd_delete_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.message.from_user.id):
return
args = context.args
if not args:
course_list = “\n”.join(”- “ + c for c in courses) or “Нет курсов”
await update.message.reply_text(“Использование: /deletecourse <название>\n\n” + course_list)
return
course = “ “.join(args)
if course not in courses:
await update.message.reply_text(“Такого курса нет.”)
return
del courses[course]
save_courses(courses)
await update.message.reply_text(“Курс удалён.”)

async def cmd_delete_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.message.from_user.id):
return
args = context.args
raw = “ “.join(args)
if “|” not in raw:
await update.message.reply_text(“Использование: /deletebook <курс> | <книга>”)
return
course, book = [p.strip() for p in raw.split(”|”, 1)]
if course not in courses:
await update.message.reply_text(“Курс не найден.”)
return
if book not in courses[course]:
await update.message.reply_text(“Книга не найдена.”)
return
del courses[course][book]
save_courses(courses)
await update.message.reply_text(“Книга удалена.”)

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.message.from_user.id
if user_id in user_state:
del user_state[user_id]
await update.message.reply_text(“Действие отменено.”)
else:
await update.message.reply_text(“Нечего отменять.”)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
data = query.data

```
if data.startswith("coursepage|"):
    page = int(data.split("|")[1])
    await query.edit_message_text("Выберите курс:", reply_markup=courses_keyboard(page))

elif data.startswith("course|"):
    parts = data.split("|", 2)
    course = parts[1]
    page = int(parts[2])
    if course not in courses:
        await query.edit_message_text("Курс не найден.")
        return
    if not courses[course]:
        await query.edit_message_text(
            "В этом курсе пока нет книг.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back_courses")]])
        )
        return
    await query.edit_message_text("Книги курса " + course + ":", reply_markup=books_keyboard(course, page))

elif data.startswith("bookpage|"):
    parts = data.split("|", 2)
    course = parts[1]
    page = int(parts[2])
    await query.edit_message_text("Книги курса " + course + ":", reply_markup=books_keyboard(course, page))

elif data.startswith("book|"):
    parts = data.split("|", 2)
    course = parts[1]
    book = parts[2]
    if course not in courses or book not in courses[course]:
        await query.edit_message_text("Файл не найден.")
        return
    file_id = courses[course][book]
    try:
        await context.bot.send_document(chat_id=query.message.chat_id, document=file_id, caption=book)
    except Exception as e:
        logger.error("Ошибка отправки файла: %s", e)
        await query.message.reply_text("Не удалось отправить файл.")

elif data == "back_courses":
    if not courses:
        await query.edit_message_text("Курсов пока нет.")
        return
    await query.edit_message_text("Выберите курс:", reply_markup=courses_keyboard())
```

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.message.from_user.id
state = user_state.get(user_id)
if not state:
return

```
step = state["step"]

if step == "adding_course":
    course = update.message.text.strip()
    if not course:
        await update.message.reply_text("Название не может быть пустым.")
        return
    if course in courses:
        await update.message.reply_text("Такой курс уже существует.")
        return
    courses[course] = {}
    save_courses(courses)
    del user_state[user_id]
    await update.message.reply_text("Курс добавлен!")

elif step == "adding_book_course":
    course = update.message.text.strip()
    if course not in courses:
        await update.message.reply_text("Такого курса нет. Попробуйте ещё раз или /cancel.")
        return
    state["course"] = course
    state["step"] = "adding_book_name"
    await update.message.reply_text("Введите название книги:")

elif step == "adding_book_name":
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Название не может быть пустым.")
        return
    state["book_name"] = name
    state["step"] = "adding_book_file"
    await update.message.reply_text("Теперь отправьте файл книги:")
```

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.message.from_user.id
state = user_state.get(user_id)
if not state or state.get(“step”) != “adding_book_file”:
return
course = state[“course”]
book_name = state.get(“book_name”, update.message.document.file_name)
courses[course][book_name] = update.message.document.file_id
save_courses(courses)
del user_state[user_id]
await update.message.reply_text(“Книга добавлена!”)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler(“start”, start))
app.add_handler(CommandHandler(“addcourse”, cmd_add_course))
app.add_handler(CommandHandler(“addbook”, cmd_add_book))
app.add_handler(CommandHandler(“deletecourse”, cmd_delete_course))
app.add_handler(CommandHandler(“deletebook”, cmd_delete_book))
app.add_handler(CommandHandler(“cancel”, cmd_cancel))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.Document.ALL, file_handler))

app.run_polling()