import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BOOKS_DIR = "books"
COURSES_FILE = "courses.json"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSE_COURSE, SEARCH_BOOK, ADDING_COURSE = 0, 1, 2

def load_courses():
    if os.path.exists(COURSES_FILE):
        with open(COURSES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    default = {"1 kurs": "1_kurs", "2 kurs": "2_kurs"}
    save_courses(default)
    return default

def save_courses(courses):
    with open(COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)

def add_course(name):
    courses = load_courses()
    folder = name.lower().replace(" ", "_").replace("/", "_")
    courses[name] = folder
    save_courses(courses)
    os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)
    return folder

def get_all_books(course_folder=None):
    courses = load_courses()
    folders = [course_folder] if course_folder else list(courses.values())
    books = []
    for folder in folders:
        path = os.path.join(BOOKS_DIR, folder)
        if not os.path.exists(path):
            continue
        for filename in os.listdir(path):
            if filename.endswith(".pdf"):
                name = filename.replace(".pdf", "")
                parts = name.split("_", 1)
                title = parts[0] if len(parts) > 0 else name
                author = parts[1] if len(parts) > 1 else "Neizvestsen"
                books.append({"title": title, "author": author, "filename": filename, "folder": folder, "path": os.path.join(path, filename)})
    return books

def search_books(query, course_folder=None):
    query = query.lower().strip()
    return [b for b in get_all_books(course_folder) if query in b["title"].lower() or query in b["author"].lower()]

def course_keyboard():
    courses = load_courses()
    buttons = [[KeyboardButton(label)] for label in courses.keys()]
    buttons.append([KeyboardButton("Vse kursy")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("Dobavit kurs")], [KeyboardButton("Spisok kursov")], [KeyboardButton("Nazad")]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Admin panel:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Poisk knig")], [KeyboardButton("Upravlenie kursami")]], resize_keyboard=True))
    else:
        await update.message.reply_text("Privet! Ya bot biblioteki. Vyberi kurs:", reply_markup=course_keyboard())
    return CHOOSE_COURSE

async def choose_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    courses = load_courses()
    if text == "Upravlenie kursami" and update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Upravlenie:", reply_markup=admin_keyboard())
        return CHOOSE_COURSE
    if text == "Poisk knig":
        await update.message.reply_text("Vyberi kurs:", reply_markup=course_keyboard())
        return CHOOSE_COURSE
    if text == "Dobavit kurs" and update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Napishi nazvanie novogo kursa:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Nazad")]], resize_keyboard=True))
        return ADDING_COURSE
    if text == "Spisok kursov":
        course_list = "\n".join([f"- {label}" for label in courses.keys()])
        await update.message.reply_text(f"Kursy:\n{course_list}", reply_markup=admin_keyboard())
        return CHOOSE_COURSE
    if text == "Nazad":
        await start(update, context)
        return CHOOSE_COURSE
    if text == "Vse kursy":
        context.user_data["course_folder"] = None
        course_name = "vse kursy"
    elif text in courses:
        context.user_data["course_folder"] = courses[text]
        course_name = text
    else:
        await update.message.reply_text("Vyberi kurs:", reply_markup=course_keyboard())
        return CHOOSE_COURSE
    await update.message.reply_text(f"Vybrano: {course_name}\nNapishi nazvanie knigi ili avtora:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Nazad k kursam")]], resize_keyboard=True))
    return SEARCH_BOOK

async def adding_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Nazad":
        await update.message.reply_text("Upravlenie:", reply_markup=admin_keyboard())
        return CHOOSE_COURSE
    folder = add_course(text)
    await update.message.reply_text(f"Kurs {text} dobavlen! Papka: books/{folder}/", reply_markup=admin_keyboard())
    return CHOOSE_COURSE

async def search_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    courses = load_courses()
    if text == "Nazad k kursam":
        await update.message.reply_text("Vyberi kurs:", reply_markup=course_keyboard())
        return CHOOSE_COURSE
    course_folder = context.user_data.get("course_folder")
    results = search_books(text, course_folder)
    if not results:
        await update.message.reply_text(f"Po zaprosu {text} nichego ne naydeno. Poprobuy drugoe:")
        return SEARCH_BOOK
    if len(results) == 1:
        book = results[0]
        await update.message.reply_text(f"Naydeno: {book['title']}\nAvtor: {book['author']}\nOtpravlyayu...")
        try:
            with open(book["path"], "rb") as f:
                await update.message.reply_document(document=f, filename=book["filename"], caption=f"{book['title']} - {book['author']}")
        except Exception as e:
            logger.error(f"Oshibka: {e}")
            await update.message.reply_text("Ne udalos otpravit fayl. Obratites k adminu.")
    else:
        response = f"Naydeno knig: {len(results)}\n\n"
        for i, book in enumerate(results[:10], 1):
            label = [k for k, v in courses.items() if v == book["folder"]]
            label = label[0] if label else book["folder"]
            response += f"{i}. {book['title']} - {book['author']} ({label})\n"
        response += "\nUtochni zapros:"
        await update.message.reply_text(response)
    return SEARCH_BOOK

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("1. /start\n2. Vyberi kurs\n3. Napishi nazvanie knigi ili avtora\n4. Poluchi PDF")

def main():
    os.makedirs(BOOKS_DIR, exist_ok=True)
    for folder in load_courses().values():
        os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)
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
    logger.info("Bot zapuschen!")
    app.run_polling()

if __name__ == "__main__":
    main()
