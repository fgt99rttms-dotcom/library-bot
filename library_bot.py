import json
import os
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "data.json"


# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"courses": {}}
        save_data(data)
        return data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_admin(user_id):
    return user_id == ADMIN_ID


# ================= FSM =================

class AdminFSM(StatesGroup):
    course_name = State()
    subject_name = State()
    subject_file = State()
    confirm_delete_course = State()
    confirm_delete_subject = State()


# ================= MAIN MENU =================

def main_kb(user_id):
    data = load_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, course in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=course["name"],
                callback_data=f"course:{cid}"
            )
        ])

    if is_admin(user_id):
        kb.inline_keyboard.append([
            InlineKeyboardButton("⚙️ Админ", callback_data="admin")
        ])

    return kb


# ================= START =================

@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("📚 LMS v3.0", reply_markup=main_kb(m.from_user.id))


# ================= ADMIN PANEL =================

@dp.callback_query(F.data == "admin")
async def admin(c: types.CallbackQuery):

    if not is_admin(c.from_user.id):
        return await c.answer("Нет доступа", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Добавить курс", callback_data="add_course")],
        [InlineKeyboardButton("🗑 Удалить курс", callback_data="del_course_menu")],
        [InlineKeyboardButton("📖 Добавить предмет", callback_data="add_subject")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ])

    await c.message.edit_text("⚙️ Админ-панель", reply_markup=kb)


# ================= ADD COURSE =================

@dp.callback_query(F.data == "add_course")
async def add_course(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.course_name)
    await c.message.edit_text("Введите название курса:")


@dp.message(AdminFSM.course_name)
async def save_course(m: types.Message, state: FSMContext):

    data = load_data()

    course_id = str(int(max(data["courses"].keys(), default="0")) + 1)

    data["courses"][course_id] = {
        "name": m.text,
        "subjects": {}
    }

    save_data(data)

    await m.answer("Курс добавлен")
    await state.clear()


# ================= DELETE COURSE (SAFE) =================

@dp.callback_query(F.data == "del_course_menu")
async def del_course_menu(c: types.CallbackQuery):

    data = load_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, course in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {course['name']}",
                callback_data=f"del_course:{cid}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="admin")
    ])

    await c.message.edit_text("Выберите курс:", reply_markup=kb)


@dp.callback_query(F.data.startswith("del_course:"))
async def delete_course(c: types.CallbackQuery):

    cid = c.data.split(":")[1]

    data = load_data()

    if cid in data["courses"]:

        # delete files
        for f in data["courses"][cid]["subjects"].values():
            if os.path.exists(f):
                os.remove(f)

        del data["courses"][cid]
        save_data(data)

    await c.message.edit_text("Курс удалён")


# ================= COURSE VIEW =================

@dp.callback_query(F.data.startswith("course:"))
async def open_course(c: types.CallbackQuery):

    cid = c.data.split(":")[1]
    data = load_data()

    course = data["courses"].get(cid)

    if not course:
        return await c.answer("Нет курса", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for subject in course["subjects"]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=subject,
                callback_data=f"subject:{cid}:{subject}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="back")
    ])

    await c.message.edit_text(course["name"], reply_markup=kb)


# ================= FILE =================

@dp.callback_query(F.data.startswith("subject:"))
async def send_file(c: types.CallbackQuery):

    _, cid, subject = c.data.split(":", 2)

    data = load_data()

    path = data["courses"][cid]["subjects"].get(subject)

    if not path or not os.path.exists(path):
        return await c.answer("Файл не найден", show_alert=True)

    await c.message.answer_document(types.FSInputFile(path))


# ================= ADD SUBJECT =================

@dp.callback_query(F.data == "add_subject")
async def add_subject(c: types.CallbackQuery):

    data = load_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, course in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(course["name"], callback_data=f"pick:{cid}")
        ])

    await c.message.edit_text("Выберите курс:", reply_markup=kb)


@dp.callback_query(F.data.startswith("pick:"))
async def pick_course(c: types.CallbackQuery, state: FSMContext):

    cid = c.data.split(":")[1]

    await state.update_data(course_id=cid)
    await state.set_state(AdminFSM.subject_name)

    await c.message.edit_text("Название предмета?")


@dp.message(AdminFSM.subject_name)
async def subject_name(m: types.Message, state: FSMContext):

    await state.update_data(subject_name=m.text)
    await state.set_state(AdminFSM.subject_file)

    await m.answer("Отправьте PDF")


@dp.message(AdminFSM.subject_file)
async def save_pdf(m: types.Message, state: FSMContext):

    if not m.document:
        return await m.answer("PDF нужен")

    data_fsm = await state.get_data()

    cid = data_fsm["course_id"]
    name = data_fsm["subject_name"]

    os.makedirs("pdf", exist_ok=True)

    path = f"pdf/{cid}_{name}.pdf"

    file = await bot.get_file(m.document.file_id)
    await bot.download_file(file.file_path, path)

    data = load_data()
    data["courses"][cid]["subjects"][name] = path
    save_data(data)

    await m.answer("Сохранено")
    await state.clear()


# ================= BACK =================

@dp.callback_query(F.data == "back")
async def back(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("📚 Меню", reply_markup=main_kb(c.from_user.id))


# ================= RUN =================

async def main():
    print("BOT v3.0 RUNNING")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())