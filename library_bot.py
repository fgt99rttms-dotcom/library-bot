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
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"


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

class DeleteItem(StatesGroup):
    level = State()
    course = State()
    subject = State()
    pdf_index = State()


# ================= UI KEYBOARDS =================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Курсы", callback_data="menu_courses")],
        [InlineKeyboardButton(text="⚙️ Админ", callback_data="menu_admin")]
    ])


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


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="admin|add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="admin|add_subject")],
        [InlineKeyboardButton(text="📎 Загрузить PDF", callback_data="admin|add_pdf")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data="admin|delete")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
    ])


# ================= START =================
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("📱 Мини-библиотека", reply_markup=main_menu())


# ================= NAVIGATION =================
@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.message.edit_text("📱 Главное меню", reply_markup=main_menu())


@dp.callback_query(F.data == "menu_courses")
async def menu_courses(call: CallbackQuery):
    db = load_db()
    await call.message.edit_text("📚 Курсы:", reply_markup=courses_kb(db))


@dp.callback_query(F.data == "menu_admin")
async def menu_admin(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа", show_alert=True)

    await call.message.edit_text("⚙️ Админ панель", reply_markup=admin_kb())


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
    if call.from_user.id != ADMIN_ID:
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
    if call.from_user.id != ADMIN_ID:
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
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await state.set_state(AddPDF.course)
    await call.message.answer("Введите курс:")
    await call.answer()


@dp.message(AddPDF.course)
async def pdf_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddPDF.subject)
    await m.answer("Введите предмет:")


@dp.message(AddPDF.subject)
async def pdf_subject(m: Message, state: FSMContext):
    await state.update_data(subject=m.text)
    await state.set_state(AddPDF.file)
    await m.answer("Отправьте PDF файл:")


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

    await state.clear()
    await m.answer("📎 PDF сохранён")


# ================= ADMIN: DELETE MENU =================
@dp.callback_query(F.data == "admin|delete")
async def delete_menu(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Нет доступа", show_alert=True)
    
    await state.set_state(DeleteItem.level)
    await state.update_data(level="course")
    
    db = load_db()
    if not db["courses"]:
        await call.message.answer("📭 Нет ни одного курса для удаления")
        await state.clear()
        return
    
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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())