import os
import json
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Владелец бота (создатель)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"
ADMINS_FILE = "admins.json"  # Файл для хранения списка админов


# ================= DB =================
def load_db():
    if not os.path.exists(DB_FILE):
        data = {"courses": {}}
        save_db(data)
        return data

    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================= ADMINS MANAGEMENT =================
def load_admins():
    if not os.path.exists(ADMINS_FILE):
        data = {"admins": [OWNER_ID]}  # Владелец автоматически админ
        save_admins(data)
        return data
    
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_admins(data):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    admins = load_admins()
    return user_id in admins["admins"]


def is_owner(user_id):
    """Проверяет, является ли пользователь владельцем"""
    return user_id == OWNER_ID


def add_admin(user_id):
    """Добавляет админа"""
    admins = load_admins()
    if user_id not in admins["admins"]:
        admins["admins"].append(user_id)
        save_admins(admins)
        return True
    return False


def remove_admin(user_id):
    """Удаляет админа"""
    admins = load_admins()
    if user_id in admins["admins"] and user_id != OWNER_ID:  # Владельца нельзя удалить
        admins["admins"].remove(user_id)
        save_admins(admins)
        return True
    return False


def get_admins_list():
    """Возвращает список админов"""
    admins = load_admins()
    return admins["admins"]


# ================= STATES =================
class AddCourse(StatesGroup):
    name = State()

class AddSubject(StatesGroup):
    course = State()
    subject = State()

class AddPDF(StatesGroup):
    course = State()
    subject = State()
    file = State()
    continue_adding = State()

class DeleteItem(StatesGroup):
    level = State()
    course = State()
    subject = State()
    pdf_index = State()

class AdminManagement(StatesGroup):
    action = State()
    user_id = State()


# ================= UI KEYBOARDS =================
def main_menu(user_id):
    kb = [[InlineKeyboardButton(text="📚 Курсы", callback_data="menu_courses")]]
    
    # Кнопка админа видна только админам
    if is_admin(user_id):
        kb.append([InlineKeyboardButton(text="⚙️ Админ", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def courses_kb(db):
    kb = []
    for c in db["courses"]:
        kb.append([InlineKeyboardButton(text=c, callback_data=f"course|{c}")])

    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def subjects_kb(course, subjects):
    kb = []
    for s in subjects:
        callback_data = f"subject|{course}|{s}"
        kb.append([InlineKeyboardButton(text=s, callback_data=callback_data)])

    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_courses")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_kb(user_id):
    kb = [
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="admin|add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="admin|add_subject")],
        [InlineKeyboardButton(text="📎 Загрузить PDF", callback_data="admin|add_pdf")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data="admin|delete")]
    ]
    
    # Управление админами доступно только владельцу
    if is_owner(user_id):
        kb.append([InlineKeyboardButton(text="👥 Управление админами", callback_data="admin|manage_admins")])
    
    kb.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def pdf_continue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Продолжить добавлять PDF", callback_data="pdf_continue")],
        [InlineKeyboardButton(text="✅ Завершить", callback_data="pdf_finish")]
    ])


def admins_management_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin|add_admin")],
        [InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin|remove_admin")],
        [InlineKeyboardButton(text="📋 Список админов", callback_data="admin|list_admins")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_admin")]
    ])


# ================= START =================
@dp.message(Command("start"))
async def start(m: Message):
    user_id = m.from_user.id
    welcome_text = f"📱 Мини-библиотека\n\nПривет, {m.from_user.first_name}!"
    
    if is_admin(user_id):
        welcome_text += "\n\n✅ Вы имеете доступ к админ-панели"
    
    await m.answer(welcome_text, reply_markup=main_menu(user_id))


# ================= NAVIGATION =================
@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.message.edit_text("📱 Главное меню", reply_markup=main_menu(call.from_user.id))


@dp.callback_query(F.data == "menu_courses")
async def menu_courses(call: CallbackQuery):
    db = load_db()
    await call.message.edit_text("📚 Курсы:", reply_markup=courses_kb(db))


@dp.callback_query(F.data == "menu_admin")
async def menu_admin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    await call.message.edit_text("⚙️ Админ панель", reply_markup=admin_kb(call.from_user.id))


# ================= ADMIN MANAGEMENT =================
@dp.callback_query(F.data == "admin|manage_admins")
async def manage_admins(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ Только владелец бота может управлять админами", show_alert=True)
        return
    
    await call.message.edit_text("👥 Управление администраторами", reply_markup=admins_management_kb())
    await call.answer()


@dp.callback_query(F.data == "admin|add_admin")
async def add_admin_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminManagement.user_id)
    await state.update_data(action="add")
    await call.message.answer("📝 Введите Telegram ID пользователя, которого хотите сделать админом:\n\n(Можно переслать любое сообщение от этого пользователя, чтобы получить его ID)")
    await call.answer()


@dp.callback_query(F.data == "admin|remove_admin")
async def remove_admin_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    
    admins = get_admins_list()
    if len(admins) <= 1:
        await call.message.answer("⚠️ Нельзя удалить единственного админа (владельца)")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for admin_id in admins:
        if admin_id != OWNER_ID:  # Владельца нельзя удалить
            try:
                user = await bot.get_chat(admin_id)
                name = user.first_name
                kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {name} ({admin_id})", callback_data=f"remove_admin_id|{admin_id}")])
            except:
                kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ ID: {admin_id}", callback_data=f"remove_admin_id|{admin_id}")])
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|manage_admins")])
    
    await call.message.edit_text("🗑️ Выберите админа для удаления:", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("remove_admin_id|"))
async def remove_admin_by_id(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    
    admin_id = int(call.data.split("|")[1])
    
    if remove_admin(admin_id):
        await call.message.answer(f"✅ Админ с ID {admin_id} удалён")
    else:
        await call.message.answer(f"❌ Не удалось удалить админа")
    
    await manage_admins(call)


@dp.callback_query(F.data == "admin|list_admins")
async def list_admins(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    
    admins = get_admins_list()
    text = "👥 Список администраторов:\n\n"
    
    for admin_id in admins:
        try:
            user = await bot.get_chat(admin_id)
            name = f"{user.first_name}"
            if user.username:
                name += f" (@{user.username})"
            role = "👑 Владелец" if admin_id == OWNER_ID else "👤 Админ"
            text += f"{role}: {name} (ID: {admin_id})\n"
        except:
            text += f"👤 ID: {admin_id}\n"
    
    text += f"\nВсего админов: {len(admins)}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|manage_admins")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@dp.message(AdminManagement.user_id)
async def process_admin_user_id(m: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("action")
    
    # Пытаемся получить ID из текста или из пересланного сообщения
    if m.forward_from:
        user_id = m.forward_from.id
    else:
        try:
            user_id = int(m.text.strip())
        except:
            await m.answer("❌ Пожалуйста, введите корректный Telegram ID или перешлите сообщение от пользователя")
            return
    
    if action == "add":
        if add_admin(user_id):
            try:
                user = await bot.get_chat(user_id)
                name = user.first_name
                await m.answer(f"✅ Пользователь {name} (ID: {user_id}) теперь администратор!")
                
                # Отправляем уведомление новому админу
                try:
                    await bot.send_message(user_id, "🎉 Поздравляем! Вы были назначены администратором бота.")
                except:
                    pass
            except:
                await m.answer(f"✅ Пользователь с ID {user_id} теперь администратор!")
        else:
            await m.answer(f"❌ Пользователь уже является администратором")
    
    await state.clear()
    await menu_admin(m)


# ================= COURSES =================
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


# ================= SUBJECT =================
@dp.callback_query(F.data.startswith("subject|"))
async def open_subject(call: CallbackQuery):
    try:
        _, course, subject = call.data.split("|", 2)
    except ValueError:
        await call.answer("❌ Ошибка формата данных", show_alert=True)
        return
    
    db = load_db()
    
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
    
    await call.answer()


# ================= ADMIN: ADD COURSE =================
@dp.callback_query(F.data == "admin|add_course")
async def add_course(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await state.set_state(AddCourse.name)
    await call.message.answer("Введите название курса:")
    await call.answer()


@dp.message(AddCourse.name)
async def save_course(m: Message, state: FSMContext):
    db = load_db()
    db["courses"][m.text] = {}
    save_db(db)

    await state.clear()
    await m.answer("✅ Курс добавлен")


# ================= ADMIN: ADD SUBJECT =================
@dp.callback_query(F.data == "admin|add_subject")
async def add_subject(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await state.set_state(AddSubject.course)
    await call.message.answer("Введите название курса (куда добавить предмет):")
    await call.answer()


@dp.message(AddSubject.course)
async def subject_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddSubject.subject)
    await m.answer("Введите название предмета:")


@dp.message(AddSubject.subject)
async def save_subject(m: Message, state: FSMContext):
    data = await state.get_data()
    course = data["course"]

    db = load_db()
    db["courses"].setdefault(course, {})
    db["courses"][course][m.text] = []

    save_db(db)

    await state.clear()
    await m.answer("✅ Предмет добавлен")


# ================= ADMIN: ADD PDF =================
@dp.callback_query(F.data == "admin|add_pdf")
async def add_pdf(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await state.set_state(AddPDF.course)
    await call.message.answer("📝 Введите название курса:")
    await call.answer()


@dp.message(AddPDF.course)
async def pdf_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddPDF.subject)
    await m.answer("📝 Введите название предмета:")


@dp.message(AddPDF.subject)
async def pdf_subject(m: Message, state: FSMContext):
    await state.update_data(subject=m.text)
    await state.set_state(AddPDF.file)
    await m.answer("📎 Отправьте PDF файл(ы)\nМожно отправить несколько файлов подряд", 
                   reply_markup=pdf_continue_kb())


@dp.message(AddPDF.file, F.document)
async def save_pdf(m: Message, state: FSMContext):
    data = await state.get_data()
    course = data["course"]
    subject = data["subject"]

    db = load_db()
    db["courses"].setdefault(course, {})
    db["courses"][course].setdefault(subject, [])

    db["courses"][course][subject].append(m.document.file_id)
    save_db(db)

    await m.answer(f"✅ PDF «{m.document.file_name}» сохранён в {course} / {subject}\n\n📎 Отправьте следующий PDF или нажмите «Завершить»", 
                   reply_markup=pdf_continue_kb())


@dp.callback_query(F.data == "pdf_continue")
async def pdf_continue(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddPDF.file)
    await call.message.answer("📎 Отправьте следующий PDF файл:")
    await call.answer()


@dp.callback_query(F.data == "pdf_finish")
async def pdf_finish(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("✅ Добавление PDF завершено", reply_markup=admin_kb(call.from_user.id))
    await call.answer()


# ================= ADMIN: DELETE MENU =================
@dp.callback_query(F.data == "admin|delete")
async def delete_menu(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Удалить курс", callback_data="delete_type|course")],
        [InlineKeyboardButton(text="📖 Удалить предмет", callback_data="delete_type|subject")],
        [InlineKeyboardButton(text="📄 Удалить PDF", callback_data="delete_type|pdf")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_admin")]
    ])
    
    await call.message.edit_text("🗑️ Что хотите удалить?", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("delete_type|"))
async def delete_type(call: CallbackQuery, state: FSMContext):
    delete_type = call.data.split("|")[1]
    await state.update_data(delete_type=delete_type)
    
    db = load_db()
    
    if delete_type == "course":
        if not db["courses"]:
            await call.message.answer("📭 Нет курсов для удаления")
            return
        
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for course in db["courses"]:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {course}", callback_data=f"delete_course|{course}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|delete")])
        
        await call.message.edit_text("🗑️ Выберите курс для удаления:", reply_markup=kb)
    
    elif delete_type == "subject":
        if not db["courses"]:
            await call.message.answer("📭 Нет курсов с предметами")
            return
        
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for course in db["courses"]:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"📚 {course}", callback_data=f"delete_subject_course|{course}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|delete")])
        
        await call.message.edit_text("🗑️ Выберите курс, из которого удалить предмет:", reply_markup=kb)
    
    elif delete_type == "pdf":
        if not db["courses"]:
            await call.message.answer("📭 Нет курсов с PDF")
            return
        
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for course in db["courses"]:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"📚 {course}", callback_data=f"delete_pdf_course|{course}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|delete")])
        
        await call.message.edit_text("🗑️ Выберите курс, из которого удалить PDF:", reply_markup=kb)
    
    await call.answer()


# ================= DELETE COURSE =================
@dp.callback_query(F.data.startswith("delete_course|"))
async def delete_course(call: CallbackQuery, state: FSMContext):
    course = call.data.split("|", 1)[1]
    
    db = load_db()
    if course in db["courses"]:
        del db["courses"][course]
        save_db(db)
        await call.message.answer(f"✅ Курс «{course}» удалён")
    else:
        await call.message.answer(f"❌ Курс «{course}» не найден")
    
    await state.clear()
    await menu_admin(call)


# ================= DELETE SUBJECT =================
@dp.callback_query(F.data.startswith("delete_subject_course|"))
async def delete_subject_choose_course(call: CallbackQuery, state: FSMContext):
    course = call.data.split("|", 1)[1]
    await state.update_data(delete_course=course)
    
    db = load_db()
    subjects = db["courses"].get(course, {})
    
    if not subjects:
        await call.message.answer(f"📭 В курсе «{course}» нет предметов")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for subject in subjects:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {subject}", callback_data=f"delete_subject|{course}|{subject}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|delete")])
    
    await call.message.edit_text(f"🗑️ Выберите предмет для удаления из курса «{course}»:", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("delete_subject|"))
async def delete_subject(call: CallbackQuery, state: FSMContext):
    _, course, subject = call.data.split("|", 2)
    
    db = load_db()
    if course in db["courses"] and subject in db["courses"][course]:
        del db["courses"][course][subject]
        
        if not db["courses"][course]:
            del db["courses"][course]
            save_db(db)
            await call.message.answer(f"✅ Предмет «{subject}» удалён. Курс «{course}» тоже удалён (стал пустым)")
        else:
            save_db(db)
            await call.message.answer(f"✅ Предмет «{subject}» удалён из курса «{course}»")
    else:
        await call.message.answer(f"❌ Предмет или курс не найден")
    
    await state.clear()
    await menu_admin(call)


# ================= DELETE PDF =================
@dp.callback_query(F.data.startswith("delete_pdf_course|"))
async def delete_pdf_choose_course(call: CallbackQuery, state: FSMContext):
    course = call.data.split("|", 1)[1]
    await state.update_data(delete_course=course)
    
    db = load_db()
    subjects = db["courses"].get(course, {})
    
    if not subjects:
        await call.message.answer(f"📭 В курсе «{course}» нет предметов с PDF")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for subject in subjects:
        if subjects[subject]:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"📄 {subject}", callback_data=f"delete_pdf_subject|{course}|{subject}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin|delete")])
    
    if not kb.inline_keyboard:
        await call.message.answer(f"📭 В курсе «{course}» нет PDF-файлов для удаления")
        return
    
    await call.message.edit_text(f"🗑️ Выберите предмет, из которого удалить PDF (курс «{course}»):", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("delete_pdf_subject|"))
async def delete_pdf_choose_file(call: CallbackQuery, state: FSMContext):
    _, course, subject = call.data.split("|", 2)
    await state.update_data(delete_course=course, delete_subject=subject)
    
    db = load_db()
    files = db["courses"][course][subject]
    
    if not files:
        await call.message.answer(f"📭 В предмете «{subject}» нет PDF-файлов")
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for idx, file_id in enumerate(files):
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ PDF #{idx+1}", callback_data=f"delete_pdf_file|{course}|{subject}|{idx}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"delete_pdf_course|{course}")])
    
    await call.message.edit_text(f"🗑️ Выберите PDF для удаления из предмета «{subject}»:", reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data.startswith("delete_pdf_file|"))
async def delete_pdf_file(call: CallbackQuery, state: FSMContext):
    _, course, subject, idx = call.data.split("|", 3)
    idx = int(idx)
    
    db = load_db()
    files = db["courses"][course][subject]
    
    if 0 <= idx < len(files):
        files.pop(idx)
        
        if not files:
            del db["courses"][course][subject]
            if not db["courses"][course]:
                del db["courses"][course]
            save_db(db)
            await call.message.answer(f"✅ PDF удалён. Предмет «{subject}» удалён (стал пустым)")
        else:
            save_db(db)
            await call.message.answer(f"✅ PDF удалён из предмета «{subject}»")
    else:
        await call.message.answer(f"❌ PDF не найден")
    
    await state.clear()
    await menu_admin(call)


# ================= RUN =================
async def main():
    print("BOT STARTED")
    print(f"Owner ID: {OWNER_ID}")
    admins = get_admins_list()
    print(f"Admins: {admins}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())