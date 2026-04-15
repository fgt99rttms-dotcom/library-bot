import json
import os
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ================= CONFIG =================

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


# ================= MEMORY (FSM REPLACEMENT) =================

USER_STATE = {}   # временные шаги админа


# ================= KEYBOARD =================

def main_kb(uid):
    data = load_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for cid, course in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=course["name"],
                callback_data=f"course:{cid}"
            )
        ])

    if is_admin(uid):
        kb.inline_keyboard.append([
            InlineKeyboardButton("⚙️ Admin", callback_data="admin")
        ])

    return kb


# ================= START =================

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("📚 LMS BOT v1", reply_markup=main_kb(m.from_user.id))


# ================= ADMIN PANEL =================

@dp.callback_query(F.data == "admin")
async def admin(c: types.CallbackQuery):

    if not is_admin(c.from_user.id):
        return await c.answer("No access", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add course", callback_data="add_course")],
        [InlineKeyboardButton("🗑 Delete course", callback_data="del_course")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ])

    await c.message.edit_text("⚙️ Admin panel", reply_markup=kb)


# ================= ADD COURSE =================

@dp.callback_query(F.data == "add_course")
async def add_course(c: types.CallbackQuery):
    USER_STATE[c.from_user.id] = {"step": "course_name"}
    await c.message.edit_text("Enter course name:")


@dp.message()
async def text_router(m: types.Message):

    uid = m.from_user.id

    if uid not in USER_STATE:
        return

    state = USER_STATE[uid]

    # ========== COURSE NAME ==========
    if state["step"] == "course_name":

        data = load_data()

        course_id = str(int(max(data["courses"].keys(), default="0")) + 1)

        data["courses"][course_id] = {
            "name": m.text,
            "subjects": {}
        }

        save_data(data)

        USER_STATE.pop(uid)

        await m.answer("✅ Course added")

    # ========== SUBJECT NAME ==========
    elif state["step"] == "subject_name":

        state["subject_name"] = m.text
        state["step"] = "subject_file"

        await m.answer("Send PDF file")


# ================= FILE UPLOAD =================

@dp.message(F.document)
async def file_handler(m: types.Message):

    uid = m.from_user.id

    if uid not in USER_STATE:
        return

    state = USER_STATE[uid]

    if state.get("step") != "subject_file":
        return

    data_fsm = state["data"]

    cid = data_fsm["course_id"]
    subject = state["subject_name"]

    os.makedirs("pdf", exist_ok=True)

    path = f"pdf/{cid}_{subject}.pdf"

    file = await bot.get_file(m.document.file_id)
    await bot.download_file(file.file_path, path)

    data = load_data()
    data["courses"][cid]["subjects"][subject] = path
    save_data(data)

    USER_STATE.pop(uid)

    await m.answer("✅ Saved")


# ================= COURSE VIEW =================

@dp.callback_query(F.data.startswith("course:"))
async def course(c: types.CallbackQuery):

    cid = c.data.split(":")[1]
    data = load_data()

    course = data["courses"].get(cid)

    if not course:
        return await c.answer("Not found", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for s in course["subjects"]:
        kb.inline_keyboard.append([
            InlineKeyboardButton(s, callback_data=f"file:{cid}:{s}")
        ])

    await c.message.edit_text(course["name"], reply_markup=kb)


# ================= FILE =================

@dp.callback_query(F.data.startswith("file:"))
async def file(c: types.CallbackQuery):

    _, cid, subject = c.data.split(":")

    data = load_data()

    path = data["courses"][cid]["subjects"].get(subject)

    if not path or not os.path.exists(path):
        return await c.answer("File not found", show_alert=True)

    await c.message.answer_document(types.FSInputFile(path))


# ================= DELETE COURSE =================

@dp.callback_query(F.data == "del_course")
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

    await c.message.edit_text("Select course:", reply_markup=kb)


@dp.callback_query(F.data.startswith("del:"))
async def delete(c: types.CallbackQuery):

    cid = c.data.split(":")[1]

    data = load_data()

    if cid in data["courses"]:

        for f in data["courses"][cid]["subjects"].values():
            if os.path.exists(f):
                os.remove(f)

        del data["courses"][cid]
        save_data(data)

    await c.message.edit_text("Deleted")


# ================= BACK =================

@dp.callback_query(F.data == "back")
async def back(c: types.CallbackQuery):
    await c.message.edit_text("📚 Menu", reply_markup=main_kb(c.from_user.id))


# ================= RUN =================

async def main():
    print("BOT v1 RUNNING")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())