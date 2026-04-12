return SEARCH_BOOK


async def search_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Как пользоваться ботом:*\n\n"
        "1️⃣ /start — начать\n"
        "2️⃣ Выбери курс\n"
        "3️⃣ Напиши название книги или автора\n"
        "4️⃣ Получи PDF файл\n\n"
        "*Формат файлов:* `Название_Автор.pdf`\n"
        "Пример: `Математика_Иванов.pdf`",
        parse_mode="Markdown"
    )


# =============================================
# ЗАПУСК
# =============================================

def main():
    for folder in COURSES.values():
        os.makedirs(os.path.join(BOOKS_DIR, folder), exist_ok=True)

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


if name == "__main__":
    main()