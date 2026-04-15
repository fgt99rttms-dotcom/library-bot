import asyncio
import json
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_admin(uid):
    return uid == ADMIN_ID


# ================= KEYBOARD =================

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
            InlineKeyboardButton("➕ Add course", callback_data="add_course")
        ])

        kb.inline_keyboard.append([
            InlineKeyboardButton("🗑 Delete course", callback_data="del_menu")
        ])

    return kb


# ================= START =================

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("📚 BOT WORKING", reply_markup=main_kb(m.from_user.id))


# ================= ADD COURSE =================

@dp.callback_query(F.data == "add_course")
async def add_course(c: types.CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("No access", show_alert=True)

    await c.message.answer("Send course name now")

    dp.add_handler(temp_course_name)


async def temp_course_name(m: types.Message):
    if not is_admin(m.from_user.id):
        return

    data = load_data()

    cid = str(int(max(data["courses"].keys(), default="0")) + 1)

    data["courses"][cid] = {
        "name": m.text,
        "subjects": {}
    }

    save_data(data)

    await m.answer("Course added")

    dp.message.unregister(temp_course_name)


# ================= DELETE COURSE =================

@dp.callback_query(F.data == "del_menu")
async def del_menu(c: types.CallbackQuery):

    data = load_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, course in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                f"❌ {course['name']}",
                callback_data=f"del:{cid}"
            )
        ])

    await c.message.edit_text("Select:", reply_markup=kb)


@dp.callback_query(F.data.startswith("del:"))
async def delete(c: types.CallbackQuery):

    cid = c.data.split(":")[1]

    data = load_data()

    if cid in data["courses"]:
        del data["courses"][cid]
        save_data(data)

    await c.message.edit_text("Deleted")


# ================= COURSE VIEW =================

@dp.callback_query(F.data.startswith("course:"))
async def course(c: types.CallbackQuery):

    cid = c.data.split(":")[1]

    data = load_data()

    course = data["courses"].get(cid)

    if not course:
        return await c.answer("Not found", show_alert=True)

    await c.message.edit_text(
        f"📚 {course['name']}"
    )


# ================= RUN =================

async def main():
    print("BOT RUNNING FIXED VERSION")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())