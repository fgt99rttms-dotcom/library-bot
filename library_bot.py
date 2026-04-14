import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ========== БЕРЁМ ТОКЕН ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден в переменных Railway!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
# ========================================================

class AdminStates(StatesGroup):
    waiting_course_id = State()
    waiting_course_name = State()
    waiting_subject_course = State()
    waiting_subject_name = State()
    waiting_subject_file = State()

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"courses": {}, "books": []}
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к курсам", callback_data="back_to_courses")]
    ])

def is_admin(user_id):
    return user_id == ADMIN_ID

@dp.message(Command("start"))
async def start(message: types.Message):
    data = load_data()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for course_id, course_info in data["courses"].items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=course_info["name"], callback_data=f"course_{course_id}")
        ])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔍 Поиск книги", callback_data="search_mode")])
    
    if is_admin(message.from_user.id):
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    
    await message.answer("📚 Добро пожаловать!\nВыбери курс или найди книгу:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("course_"))
async def show_subjects(callback: types.CallbackQuery):
    course_id = callback.data.split("_")[1]
    data = load_data()
    
    if course_id not in data["courses"]:
        await callback.answer("Курс не найден")
        return
    
    subjects = data["courses"][course_id]["subjects"]
    
    if not subjects:
        keyboard = back_button()
        await callback.message.edit_text("📭 На этом курсе пока нет предметов", reply_markup=keyboard)
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for subject_name, file_path in subjects.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=subject_name, callback_data=f"file_{course_id}_{subject_name}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад к курсам", callback_data="back_to_courses")])
    
    await callback.message.edit_text(f"📚 {data['courses'][course_id]['name']} - выбери предмет:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("file_"))
async def send_pdf(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    course_id = parts[1]
    subject_name = "_".join(parts[2:])
    
    data = load_data()
    file_path = data["courses"][course_id]["subjects"].get(subject_name)
    
    if not file_path or not os.path.exists(file_path):
        await callback.answer("❌ Файл не найден", show_alert=True)
        return
    
    with open(file_path, "rb") as pdf:
        await callback.message.answer_document(pdf, caption=f"📖 {subject_name}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "search_mode")
async def search_mode(callback: types.CallbackQuery):
    keyboard = back_button()
    await callback.message.edit_text("🔍 Введите название или автора книги:", reply_markup=keyboard)
    await callback.answer()

@dp.message()
async def search_book(message: types.Message):
    if message.text.startswith("/"):
        return
    
    query = message.text.lower()
    data = load_data()
    
    results = [book for book in data["books"] 
               if query in book["title"].lower() or query in book["author"].lower()]
    
    if not results:
        await message.answer("❌ Ничего не найдено. Попробуйте другое название или автора.")
        return
    
    await message.answer(f"🔍 Найдено {len(results)} книг:")
    for book in results:
        if os.path.exists(book["file"]):
            with open(book["file"], "rb") as pdf:
                await message.answer_document(pdf, caption=f"📖 {book['title']}\n✍️ {book['author']}")
        else:
            await message.answer(f"⚠️ {book['title']} - файл не найден")

@dp.callback_query(lambda c: c.data == "back_to_courses")
async def back_to_courses(callback: types.CallbackQuery):
    await start(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить курс", callback_data="admin_add_course")],
        [InlineKeyboardButton(text="📚 Добавить предмет", callback_data="admin_add_subject")],
        [InlineKeyboardButton(text="📋 Список курсов", callback_data="admin_list_courses")],
        [InlineKeyboardButton(text="🗑 Удалить курс", callback_data="admin_delete_course")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_courses")]
    ])
    await callback.message.edit_text("⚙️ **Админ-панель**\nВыберите действие:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_add_course")
async def add_course_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите **ID курса** (например: 1, 2, 3):")
    await state.set_state(AdminStates.waiting_course_id)
    await callback.answer()

@dp.message(AdminStates.waiting_course_id)
async def add_course_id(message: types.Message, state: FSMContext):
    course_id = message.text.strip()
    await state.update_data(course_id=course_id)
    await message.answer("Введите **название курса** (например: 1 курс, Первый курс):")
    await state.set_state(AdminStates.waiting_course_name)

@dp.message(AdminStates.waiting_course_name)
async def add_course_name(message: types.Message, state: FSMContext):
    course_name = message.text.strip()
    data = await state.get_data()
    course_id = data["course_id"]
    
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав")
        await state.clear()
        return
    
    bot_data = load_data()
    
    if course_id in bot_data["courses"]:
        await message.answer(f"❌ Курс с ID {course_id} уже существует!")
        await state.clear()
        return
    
    bot_data["courses"][course_id] = {"name": course_name, "subjects": {}}
    save_data(bot_data)
    
    await message.answer(f"✅ Курс **{course_name}** (ID: {course_id}) добавлен!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_add_subject")
async def add_subject_course(callback: types.CallbackQuery, state: FSMContext):
    data = load_data()
    if not data["courses"]:
        await callback.message.edit_text("❌ Сначала добавьте курс!")
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=course["name"], callback_data=f"select_course_{course_id}")]
        for course_id, course in data["courses"].items()
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    
    await callback.message.edit_text("Выберите курс для добавления предмета:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("select_course_"))
async def add_subject_name(callback: types.CallbackQuery, state: FSMContext):
    course_id = callback.data.replace("select_course_", "")
    await state.update_data(subject_course=course_id)
    await callback.message.edit_text("Введите **название предмета**:")
    await state.set_state(AdminStates.waiting_subject_name)
    await callback.answer()

@dp.message(AdminStates.waiting_subject_name)
async def add_subject_file_request(message: types.Message, state: FSMContext):
    subject_name = message.text.strip()
    await state.update_data(subject_name=subject_name)
    await message.answer("📎 **Отправьте PDF-файл** для этого предмета:")
    await state.set_state(AdminStates.waiting_subject_file)

@dp.message(AdminStates.waiting_subject_file)
async def add_subject_file(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте PDF-файл!")
        return
    
    if not message.document.file_name.endswith('.pdf'):
        await message.answer("❌ Пожалуйста, отправьте файл в формате PDF!")
        return
    
    data = await state.get_data()
    course_id = data["subject_course"]
    subject_name = data["subject_name"]
    
    if not os.path.exists("pdf"):
        os.makedirs("pdf")
    
    file_name = f"{course_id}_{subject_name}.pdf".replace(" ", "_")
    file_path = os.path.join("pdf", file_name)
    
    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, file_path)
    
    bot_data = load_data()
    if course_id not in bot_data["courses"]:
        await message.answer("❌ Курс не найден!")
        await state.clear()
        return
    
    bot_data["courses"][course_id]["subjects"][subject_name] = file_path
    bot_data["books"].append({"title": subject_name, "author": f"{bot_data['courses'][course_id]['name']}", "file": file_path})
    save_data(bot_data)
    
    await message.answer(f"✅ Предмет **{subject_name}** добавлен на {bot_data['courses'][course_id]['name']}!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_list_courses")
async def list_courses(callback: types.CallbackQuery):
    data = load_data()
    if not data["courses"]:
        await callback.message.edit_text("📭 Нет добавленных курсов")
        await callback.answer()
        return
    
    text = "**📋 Список курсов:**\n\n"
    for course_id, course in data["courses"].items():
        text += f"• **{course['name']}** (ID: {course_id}) — {len(course['subjects'])} предметов\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_delete_course")
async def delete_course_select(callback: types.CallbackQuery):
    data = load_data()
    if not data["courses"]:
        await callback.message.edit_text("📭 Нет курсов для удаления")
        await callback.answer()
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course in data["courses"].items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"❌ {course['name']}", callback_data=f"delete_course_{course_id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    
    await callback.message.edit_text("Выберите курс для удаления:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("delete_course_"))
async def delete_course_confirm(callback: types.CallbackQuery):
    course_id = callback.data.replace("delete_course_", "")
    data = load_data()
    
    if course_id not in data["courses"]:
        await callback.answer("Курс не найден")
        return
    
    course_name = data["courses"][course_id]["name"]
    
    for subject_name, file_path in data["courses"][course_id]["subjects"].items():
        if os.path.exists(file_path):
            os.remove(file_path)
    
    data["books"] = [book for book in data["books"] if not book["file"].startswith(f"pdf/{course_id}_")]
    del data["courses"][course_id]
    save_data(data)
    
    await callback.message.edit_text(f"✅ Курс **{course_name}** и все его предметы удалены!", parse_mode="Markdown")
    await callback.answer()

async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())