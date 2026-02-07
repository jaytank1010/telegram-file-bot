import asyncio
import re
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
API_ID = 39676458
API_HASH = "5cbbab7cce3e7abcb6232bbb4772d9f6"
BOT_TOKEN = "8363286559:AAEfCUy7cFzfegxWPSlJXuU4pw9PKpwihNg" # Aapka naya fresh token
MONGO_URL = "mongodb+srv://Jay:Jay10@cluster0.q2umpq1.mongodb.net/?appName=Cluster0"
DB_CHANNEL_ID = -1003884650366
GPLINKS_API = "Db2b094793689ffb0c0c5e71468d5b89e10c9c3e"

# MongoDB Setup
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client.get_database("JayMovies").get_collection("Files")

app = Client("JayMovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- UTILS ---

async def delete_after_delay(message, delay):
    """Background task to delete message after X seconds"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"Delete Error: {e}")

def get_shortlink(url):
    """Convert long URL to GPLinks earning link"""
    try:
        api_url = f"https://gplinks.in/api?api={GPLINKS_API}&url={url}"
        res = requests.get(api_url).json()
        return res["shortenedUrl"] if res["status"] == "success" else url
    except:
        return url

# --- HANDLERS ---

@app.on_message(filters.command("start"))
async def start(client, message):
    msg = await message.reply_text(f"Hello {message.from_user.first_name}!\nI am Jay's Movie Bot. Send me a movie name to search.")
    # Start message deletes in 60 seconds to keep chat clean
    asyncio.create_task(delete_after_delay(msg, 60))

@app.on_message(filters.text & filters.private)
async def search(client, message):
    query = message.text
    if query.startswith("/"): return

    search_log = await message.reply_text(f"🔎 Searching for '{query}'...")
    
    # Database Search Logic
    regex = re.compile(query, re.IGNORECASE)
    files = await db.find({"file_name": regex}).to_list(10)

    if not files:
        err = await message.reply_text("❌ Sorry Jay! Movie nahi mili. Spelling check karein.")
        asyncio.create_task(delete_after_delay(err, 30)) # Error msg delete in 30s
        await search_log.delete()
        return

    # Results found
    for file in files:
        file_name = file["file_name"]
        file_id = file["file_id"]
        # Creating deep link for the file
        long_url = f"https://t.me/share/url?url=https://t.me/c/{str(DB_CHANNEL_ID)[4:]}/{file_id}"
        short_url = get_shortlink(long_url)

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Download Now", url=short_url)]
        ])

        # Sending file result with auto-delete
        sent_msg = await message.reply_text(
            f"🎬 **File:** `{file_name}`\n\n⚠️ *This message will be deleted in 3 minutes!*",
            reply_markup=buttons
        )
        
        # 180 seconds = 3 minutes timer
        asyncio.create_task(delete_after_delay(sent_msg, 180))

    await search_log.delete()

# Indexing from Channel
@app.on_message(filters.chat(DB_CHANNEL_ID) & (filters.document | filters.video))
async def index_files(client, message):
    file_name = message.document.file_name if message.document else message.video.file_name
    file_id = message.id
    
    # Save to MongoDB
    await db.update_one(
        {"file_id": file_id},
        {"$set": {"file_name": file_name, "file_id": file_id}},
        upsert=True
    )
    print(f"✅ Indexed: {file_name}")

print("Bot is LIVE with 3-Min Auto-Delete! 🚀")
app.run()
