import os
import re
import asyncio
import aiohttp
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from motor.motor_asyncio import AsyncIOMotorClient

# ================= ENV =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

DB_CHANNEL_ID = int(os.getenv("DB_CHANNEL_ID"))   # private storage channel id
CHANNEL_LINK = os.getenv("CHANNEL_LINK")          # https://t.me/yourchannel
GPLINKS_API = os.getenv("GPLINKS_API")
PORT = int(os.getenv("PORT", 8000))

GPLINKS_DOMAIN = "gplinks.in"

# ================= BOT =================
app = Client(
    "movie_search_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= DATABASE =================
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["filebot"]["files"]

# ================= SHORTLINK =================
async def get_shortlink(url):
    api = f"https://{GPLINKS_DOMAIN}/api?api={GPLINKS_API}&url={url}"
    async with aiohttp.ClientSession() as session:
        async with session.get(api) as resp:
            try:
                data = await resp.json()
                return data.get("shortenedUrl", url)
            except:
                return url

# ================= FORCE JOIN =================
async def is_joined(user_id):
    try:
        await app.get_chat_member(DB_CHANNEL_ID, user_id)
        return True
    except UserNotParticipant:
        return False
    except:
        return False

# ================= START =================
@app.on_message(filters.command("start"))
async def start(_, message):
    if not await is_joined(message.from_user.id):
        return await message.reply_text(
            "❌ **Bot use karne ke liye channel join karo**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]
            ])
        )

    await message.reply_text(
        "🎬 **Movie Search Bot Ready!**\n\n"
        "🔍 Movie name likho\n"
        "📂 Example: *KGF 2*"
    )

# ================= SEARCH =================
@app.on_message(filters.text & ~filters.command(["start"]))
async def search(_, message):
    if not await is_joined(message.from_user.id):
        return await message.reply_text(
            "❌ Pehle channel join karo",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]
            ])
        )

    query = message.text.strip()
    if len(query) < 2:
        return

    regex = re.compile(query, re.IGNORECASE)
    results = await db.find({"file_name": regex}).to_list(10)

    if not results:
        return await message.reply_text(
            "❌ **Movie nahi mili**\n\n"
            "👉 Spelling check karo\n"
            "👉 Short name try karo"
        )

    buttons = []
    bot_username = (await app.get_me()).username

    for file in results:
        deep_link = f"https://t.me/{bot_username}?start={file['file_id']}"
        short = await get_shortlink(deep_link)
        buttons.append([
            InlineKeyboardButton(text=file["file_name"], url=short)
        ])

    await message.reply_text(
        "📂 **Search Results:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= FILE SEND =================
@app.on_message(filters.command("start") & filters.regex(r"^/start\s+"))
async def send_file(_, message):
    if not await is_joined(message.from_user.id):
        return await message.reply_text(
            "❌ Channel join karo file lene ke liye",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]
            ])
        )

    file_id = message.command[1]
    file = await db.find_one({"file_id": file_id})

    if not file:
        return await message.reply_text("❌ File not found / expired")

    await app.send_document(
        chat_id=message.chat.id,
        document=file["file_id"],
        caption=f"🎬 **{file['file_name']}**"
    )

# ================= AUTO INDEX =================
@app.on_message(filters.channel & filters.chat(DB_CHANNEL_ID))
async def index_files(_, message):
    if not message.document:
        return

    data = {
        "file_id": message.document.file_id,
        "file_name": message.document.file_name
    }
    await db.insert_one(data)

# ================= DUMMY WEB SERVER (Koyeb FREE TRICK) =================
async def web_server():
    async def handle(request):
        return web.Response(text="OK")

    web_app = web.Application()
    web_app.router.add_get("/", handle)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# ================= MAIN =================
async def main():
    await app.start()
    await web_server()
    print("🤖 Bot is running 24×7...")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
