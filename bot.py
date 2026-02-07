import os
import re
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient

# ================== CONFIG (ENV ONLY) ==================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

DB_NAME = "filebot"
COLLECTION = "files"

DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))  # indexing channel
GPLINKS_API = os.getenv("GPLINKS_API")            # shortlink key
GPLINKS_DOMAIN = "gplinks.in"

# ================== BOT & DB ==================
app = Client(
    "file_search_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo[DB_NAME][COLLECTION]

# ================== SHORTLINK ==================
async def get_shortlink(url: str):
    if not GPLINKS_API:
        return url

    api = (
        f"https://{GPLINKS_DOMAIN}/api"
        f"?api={GPLINKS_API}&url={url}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(api) as resp:
            data = await resp.json()
            return data.get("shortenedUrl", url)

# ================== START ==================
@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "👋 Welcome!\n\n"
        "🔍 Send any **movie / file name** to search.\n"
        "📂 I’ll find it for you instantly ⚡"
    )

# ================== SEARCH ==================
@app.on_message(filters.text & ~filters.command)
async def search(_, message):
    query = message.text.strip()
    if len(query) < 2:
        return

    regex = re.compile(query, re.IGNORECASE)
    results = await db.find({"file_name": regex}).to_list(10)

    if not results:
        await message.reply_text("❌ No files found.")
        return

    buttons = []
    for file in results:
        link = f"https://t.me/{(await app.get_me()).username}?start={file['file_id']}"
        short = await get_shortlink(link)

        buttons.append([
            InlineKeyboardButton(
                text=file["file_name"],
                url=short
            )
        ])

    await message.reply_text(
        "📁 **Search Results:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================== FILE SEND ==================
@app.on_message(filters.command("start") & filters.regex(r"^/start\s+"))
async def send_file(_, message):
    file_id = message.command[1]
    file = await db.find_one({"file_id": file_id})

    if not file:
        await message.reply_text("❌ File expired or not found.")
        return

    await app.send_document(
        chat_id=message.chat.id,
        document=file["file_id"],
        caption=f"📂 {file['file_name']}"
    )

# ================== INDEXING ==================
@app.on_message(filters.channel & filters.chat(DB_CHANNEL_ID))
async def index_files(_, message):
    if not message.document:
        return

    file_data = {
        "file_id": message.document.file_id,
        "file_name": message.document.file_name
    }

    await db.insert_one(file_data)

# ================== RUN ==================
app.run()
