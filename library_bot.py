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


# ================= DB INIT =================
def create_default_db():
    data = {
        "courses": {
            "1 курс": {
                "Анатомия": [],
                "Физиология": []
            },
            "2 курс": {
                "Биохимия": []
            }
        }
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return data


def load_db():
    if not os.path.exists(DB_FILE):
        return create_default_db()

    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "courses" not in data:
        return create_default_db()

    return data


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


# ================= KEYBOARDS =================
def courses_kb(db):
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for course in db["courses"].keys():
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=course, callback_data=f"course:{course}")
        ])

    return kb


def subjects_kb(course, subjects):
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for s in subjects.keys():
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=s, callback_data=f"subject:{course}:{s}")
        ])

    return kb


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="add_subject")],
        [InlineKeyboardButton(text="📎 Загрузить PDF", callback_data="add_pdf")]
    ])


# ================= START =================
@dp.message(Command("start"))
async def start(m: Message):
    db = load_db()
    await m.answer("📚 Выберите курс:", reply_markup=courses_kb(db))


# ================= ADMIN =================
@dp.message(Command("admin"))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔ Нет доступа")

    await m.answer("⚙️ Админ панель", reply_markup=admin_kb())


# ================= ADD COURSE =================
@dp.callback_query(F.data == "add_course")
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


# ================= ADD SUBJECT =================
@dp.callback_query(F.data == "add_subject")
async def add_subject(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubject.course)
    await call.message.answer("Введите курс:")


@dp.message(AddSubject.course)
async def subject_course(m: Message, state: FSMContext):
    await state.update_data(course=m.text)
    await state.set_state(AddSubject.subject)
    await m.answer("Введите предмет:")


@dp.message(AddSubject.subject)
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


# ================= ADD PDF =================
@dp.callback_query(F.data == "add_pdf")
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


# ================= NAVIGATION =================
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


# ================= RUN =================
async def main():
    print("BOT STARTED")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())