import json
import os
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))


if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден")
    exit(1)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DATA_FILE = "data.json"


# ===================== FSM =====================

class AdminStates(StatesGroup):
    waiting_course_id = State()
    waiting_course_name = State()
    waiting_subject_course = State()
    waiting_subject_name = State()
    waiting_subject_file = State()


class SearchStates(StatesGroup):
    waiting_query = State()


# ===================== DATA =====================

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"courses": {}, "books": []}
        save_data(data)
        return data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_admin(user_id):
    return user_id == ADMIN_ID


# ===================== KEYBOARD =====================

def build_main_keyboard(user_id):
    data = load_data()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for course_id, course in data["courses"].items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=course["name"],
                callback_data=f"course_{course_id}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text="🔍 Поиск книги",
            callback_data="search_mode"
        )
    ])

    if is_admin(user_id):
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="⚙️ Админ-панель",
                callback_data="admin_panel"
            )
        ])

    return keyboard


# ===================== START =====================

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()

    keyboard = build_main_keyboard(message.from_user.id)

    await message.answer(
        "📚 Добро пожаловать!\nВыбери курс:",
        reply_markup=keyboard
    )


# ===================== BACK =====================

@dp.callback_query(F.data == "back_to_courses")
async def back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    keyboard = build_main_keyboard(callback.from_user.id)

    await callback.message.edit_text(
        "📚 Выбери курс:",
        reply_markup=keyboard
    )

    await callback.answer()


# ===================== SHOW SUBJECTS =====================

@dp.callback_query(F.data.startswith("course_"))
async def show_subjects(callback: types.CallbackQuery):
    course_id = callback.data.split("_")[1]

    data = load_data()

    if course_id not in data["courses"]:
        await callback.answer("Курс не найден")
        return

    subjects = data["courses"][course_id]["subjects"]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    if not subjects:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_courses"
            )
        ])

        await callback.message.edit_text(
            "📭 Пока нет предметов",
            reply_markup=keyboard
        )

        return

    for subject in subjects:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=subject,
                callback_data=f"file_{course_id}_{subject}"
            )
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_courses"
        )
    ])

    await callback.message.edit_text(
        f"📚 {data['courses'][course_id]['name']}",
        reply_markup=keyboard
    )


# ===================== SEND FILE =====================

@dp.callback_query(F.data.startswith("file_"))
async def send_file(callback: types.CallbackQuery):
    _, course_id, subject = callback.data.split("_", 2)

    data = load_data()

    file_path = data["courses"][course_id]["subjects"].get(subject)

    if not file_path or not os.path.exists(file_path):
        await callback.answer("Файл не найден", show_alert=True)
        return

    await callback.message.answer_document(
        types.FSInputFile(file_path),
        caption=f"📖 {subject}"
    )


# ===================== ADMIN PANEL =====================

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="add_subject")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_courses")]
    ])

    await callback.message.edit_text(
        "⚙️ Админ-панель",
        reply_markup=keyboard
    )


# ===================== ADD COURSE =====================

@dp.callback_query(F.data == "add_course")
async def add_course_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_course_id)

    await callback.message.edit_text(
        "Введите ID курса:"
    )


@dp.message(AdminStates.waiting_course_id)
async def add_course_id(message: types.Message, state: FSMContext):
    await state.update_data(course_id=message.text.strip())

    await state.set_state(AdminStates.waiting_course_name)

    await message.answer("Введите название курса:")


@dp.message(AdminStates.waiting_course_name)
async def add_course_name(message: types.Message, state: FSMContext):
    data_fsm = await state.get_data()

    course_id = data_fsm["course_id"]

    data = load_data()

    if course_id in data["courses"]:
        await message.answer("Такой курс уже существует")
        return

    data["courses"][course_id] = {
        "name": message.text.strip(),
        "subjects": {}
    }

    save_data(data)

    await message.answer("Курс добавлен")

    await state.clear()


# ===================== ADD SUBJECT =====================

@dp.callback_query(F.data == "add_subject")
async def choose_course(callback: types.CallbackQuery):
    data = load_data()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for course_id, course in data["courses"].items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=course["name"],
                callback_data=f"select_{course_id}"
            )
        ])

    await callback.message.edit_text(
        "Выбери курс:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("select_"))
async def subject_name(callback: types.CallbackQuery, state: FSMContext):
    course_id = callback.data.split("_")[1]

    await state.update_data(course_id=course_id)

    await state.set_state(AdminStates.waiting_subject_name)

    await callback.message.edit_text("Введите название предмета:")


@dp.message(AdminStates.waiting_subject_name)
async def subject_file(message: types.Message, state: FSMContext):
    await state.update_data(subject_name=message.text)

    await state.set_state(AdminStates.waiting_subject_file)

    await message.answer("Отправьте PDF файл")


@dp.message(AdminStates.waiting_subject_file)
async def save_pdf(message: types.Message, state: FSMContext):

    if not message.document:
        await message.answer("Отправьте PDF")
        return

    data_fsm = await state.get_data()

    course_id = data_fsm["course_id"]

    subject_name = data_fsm["subject_name"]

    os.makedirs("pdf", exist_ok=True)

    file_path = f"pdf/{course_id}_{subject_name}.pdf"

    file = await bot.get_file(message.document.file_id)

    await bot.download_file(file.file_path, file_path)

    data = load_data()

    data["courses"][course_id]["subjects"][subject_name] = file_path

    save_data(data)

    await message.answer("Предмет добавлен")

    await state.clear()


# ===================== RUN =====================

async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())