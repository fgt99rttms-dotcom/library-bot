from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "8657476988:AAH1HZZDIw2ZmTOrAZS_RpgTiYwVPl0iPoI"
ADMIN_ID = 1009646927

courses = {}
user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for course in courses:
        keyboard.append(
            [InlineKeyboardButton(course, callback_data=f"course_{course}")]
        )

    await update.message.reply_text(
        "Выберите курс:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def course_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    course = query.data.replace("course_", "")

    books = courses.get(course, {})

    keyboard = []

    for book in books:
        keyboard.append(
            [InlineKeyboardButton(book, callback_data=f"book_{course}_{book}")]
        )

    await query.edit_message_text(
        f"Книги курса {course}:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, course, book = query.data.split("_", 2)

    file_id = courses[course][book]

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=file_id,
    )


async def add_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    user_state[update.message.from_user.id] = "adding_course"

    await update.message.reply_text("Введите название курса")


async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    user_state[update.message.from_user.id] = "adding_book_course"

    await update.message.reply_text("Введите курс")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_state:
        return

    state = user_state[user_id]

    if state == "adding_course":
        course = update.message.text

        courses[course] = {}

        del user_state[user_id]

        await update.message.reply_text("Курс добавлен")

    elif state == "adding_book_course":
        course = update.message.text

        if course not in courses:
            await update.message.reply_text("Такого курса нет")
            return

        context.user_data["course"] = course
        user_state[user_id] = "adding_book_file"

        await update.message.reply_text("Отправьте файл книги")


async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_state:
        return

    if user_state[user_id] != "adding_book_file":
        return

    course = context.user_data["course"]

    file = update.message.document

    courses[course][file.file_name] = file.file_id

    del user_state[user_id]

    await update.message.reply_text("Книга добавлена")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addcourse", add_course))
app.add_handler(CommandHandler("addbook", add_book))

app.add_handler(CallbackQueryHandler(course_handler, pattern="^course_"))
app.add_handler(CallbackQueryHandler(book_handler, pattern="^book_"))

app.add_handler(MessageHandler(filters.TEXT, text_handler))
app.add_handler(MessageHandler(filters.Document.ALL, file_handler))

app.run_polling()