import os
import json

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"


# ================== DB ==================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"courses": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================== STATES ==================
class AddCourse(StatesGroup):
    name = State()

class AddSubject(StatesGroup):
    course = State()
    name = State()

class AddPDF(StatesGroup):
    course = State()
    subject = State()
    file = State()


# ================== KEYBOARDS ==================
def courses_kb(db):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for c in db["courses"]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=c, callback_data=f"course:{c}")
        ])
    return kb


def subjects_kb(course, subjects):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for s in subjects:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=s, callback_data=f"subject:{course}:{s}")
        ])
    return kb


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Курс", callback_data="a_add_course")],
        [InlineKeyboardButton(text="📚 Предмет", callback_data="a_add_subject")],
        [InlineKeyboardButton(text="📎 PDF", callback_data="a_add_pdf")]
    ])


# ================== START ==================
@dp.message(Command("start"))
async def start(m: Message):
    db = load_db()
    await m.answer("📚 Выберите курс:", reply_markup=courses_kb(db))


# ================== ADMIN PANEL ==================
@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ Нет доступа")
    await m.answer("⚙️ Админ панель", reply_markup=admin_kb())


# ================== ADD COURSE ==================
@dp.callback_query(F.data == "a_add_course")
async def add_course(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddCourse.name)
    await call.message.answer("Введите название курса:")


@dp.message(AddCourse.name)
async def save_course(m: Message, state: FSMContext):
    db = load_db()
    db["courses"][m.text] = {}
    save_db(db)
    await state.clear()
    await m.answer("✅ Курс добавлен")


# ================== ADD SUBJECT ==================
@dp.callback_query(F.data == "a_add_subject")
async def add_subject(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubject.course)
    await call.message.answer("Введите курс:")


@dp.message(AddSubject.course)
async def subject_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddSubject.name)
    await m.answer("Введите предмет:")


@dp.message(AddSubject.name)
async def save_subject(m: Message, state: FSMContext):
    data = await state.get_data()
    course = data["course"]

    db = load_db()
    if course not in db["courses"]:
        db["courses"][course] = {}

    db["courses"][course][m.text] = []
    save_db(db)

    await state.clear()
    await m.answer("✅ Предмет добавлен")


# ================== ADD PDF ==================
@dp.callback_query(F.data == "a_add_pdf")
async def add_pdf(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddPDF.course)
    await call.message.answer("Введите курс:")


@dp.message(AddPDF.course)
async def pdf_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddPDF.subject)
    await m.answer("Введите предмет:")


@dp.message(AddPDF.subject)
async def pdf_subject(m: Message, state: FSMContext):
    await state.update_data(subject=m.text)
    await state.set_state(AddPDF.file)
    await m.answer("Отправь PDF файл")


@dp.message(AddPDF.file, F.document)
async def save_pdf(m: Message, state: FSMContext):
    data = await state.get_data()
    course = data["course"]
    subject = data["subject"]

    file_id = m.document.file_id

    db = load_db()
    db["courses"].setdefault(course, {})
    db["courses"][course].setdefault(subject, [])
    db["courses"][course][subject].append(file_id)

    save_db(db)

    await state.clear()
    await m.answer("📎 PDF сохранён")


# ================== USER NAVIGATION ==================
@dp.callback_query(F.data.startswith("course:"))
async def open_course(call: CallbackQuery):
    course = call.data.split(":")[1]
    db = load_db()

    subjects = db["courses"].get(course, {})
    await call.message.edit_text(
        f"📘 {course}",
        reply_markup=subjects_kb(course, subjects)
    )


@dp.callback_query(F.data.startswith("subject:"))
async def open_subject(call: CallbackQuery):
    _, course, subject = call.data.split(":")
    db = load_db()

    files = db["courses"][course][subject]

    await call.message.answer(f"📂 {subject}")

    for file_id in files:
        await bot.send_document(call.message.chat.id, file_id)


# ================== RUN ==================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())