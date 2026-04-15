# ================= FIXED SUBJECTS KB =================
def subjects_kb(course, subjects):
    kb = []
    for s in subjects:
        # Используем безопасный разделитель
        callback_data = f"subject|{course}|{s}"
        kb.append([InlineKeyboardButton(text=s, callback_data=callback_data)])

    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_courses")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ================= FIXED OPEN SUBJECT =================
@dp.callback_query(F.data.startswith("subject|"))
async def open_subject(call: CallbackQuery):
    try:
        _, course, subject = call.data.split("|", 2)
    except ValueError:
        await call.answer("❌ Ошибка формата данных", show_alert=True)
        return
    
    db = load_db()
    
    # Проверка существования
    if course not in db["courses"]:
        await call.answer("❌ Курс не найден", show_alert=True)
        return
    
    if subject not in db["courses"][course]:
        await call.answer("❌ Предмет не найден", show_alert=True)
        return
    
    files = db["courses"][course][subject]
    
    if not files:
        await call.message.answer(f"📂 {subject}\n\n⚠️ Нет загруженных PDF")
        return
    
    await call.message.answer(f"📂 {subject}")
    for file_id in files:
        await bot.send_document(call.message.chat.id, file_id)
    
    await call.answer()  # Закрываем "часики" на кнопке


# ================= FIXED OPEN COURSE =================
@dp.callback_query(F.data.startswith("course|"))
async def open_course(call: CallbackQuery):
    course = call.data.split("|", 1)[1]
    db = load_db()
    
    if course not in db["courses"]:
        await call.answer("❌ Курс не найден", show_alert=True)
        return
    
    subjects = db["courses"].get(course, {})
    
    if not subjects:
        await call.message.edit_text(
            f"📘 {course}\n\n⚠️ В этом курсе пока нет предметов",
            reply_markup=subjects_kb(course, {})
        )
        return
    
    await call.message.edit_text(
        f"📘 {course}",
        reply_markup=subjects_kb(course, subjects)
    )


# ================= FIXED COURSES KB =================
def courses_kb(db):
    kb = []
    for c in db["courses"]:
        kb.append([InlineKeyboardButton(text=c, callback_data=f"course|{c}")])

    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ================= FIXED ADMIN PANEL =================
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="admin|add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="admin|add_subject")],
        [InlineKeyboardButton(text="📎 Загрузить PDF", callback_data="admin|add_pdf")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
    ])


@dp.callback_query(F.data == "menu_admin")
async def menu_admin(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await call.message.edit_text("⚙️ Админ панель", reply_markup=admin_kb())


@dp.callback_query(F.data.startswith("admin|"))
async def admin_actions(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    action = call.data.split("|", 1)[1]
    
    if action == "add_course":
        await state.set_state(AddCourse.name)
        await call.message.answer("Введите название курса:")
    elif action == "add_subject":
        await state.set_state(AddSubject.course)
        await call.message.answer("Введите название курса (куда добавить предмет):")
    elif action == "add_pdf":
        await state.set_state(AddPDF.course)
        await call.message.answer("Введите курс:")
    
    await call.answer()