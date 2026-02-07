import os
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient

# --- JAY TANK'S FINAL CONFIGURATION ---
API_ID = 39676458
API_HASH = "5cbbab7cce3e7abcb6232bbb4772d9f6"
BOT_TOKEN = "8363286559:AAHe5YWJkjd-qE-FRnfFf07ZnH4V0KKTFUM"
MONGO_URL = "mongodb+srv://Jay:Jay10@cluster0.q2umpq1.mongodb.net/?retryWrites=true&w=majority"
DB_CHANNEL_ID = -1003884650366
CHANNEL_LINK = "https://t.me/+IlD4EhrhIBY3MmE1"
GPLINKS_API = "Db2b094793689ffb0c0c5e71468d5b89e10c9c3e"

# --- DATABASE SETUP ---
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["MovieBotDB"]
files_col = db["files"]

app = Client("JayMovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# GPLinks Shortener Function
def get_shortlink(url):
    try:
        api_url = f"https://gplinks.in/api?api={GPLINKS_API}&url={url}"
        res = requests.get(api_url).json()
        if res.get("status") == "success":
            return res["shortenedUrl"]
        return url
    except Exception as e:
        print(f"GPLinks Error: {e}")
        return url

# 1. Indexing Logic: Direct Upload aur Forwarded Files dono ko index karega
@app.on_message(filters.chat(DB_CHANNEL_ID) & (filters.document | filters.video))
async def index_files(client, message):
    file = message.document or message.video
    # File name ko lowercase mein save kar rahe hain taaki search aasaan ho
    file_name = file.file_name.lower() if file.file_name else "unknown_file"
    
    file_data = {
        "file_name": file_name,
        "file_id": file.file_id
    }
    
    # MongoDB mein update ya insert karein
    await files_col.update_one({"file_id": file.file_id}, {"$set": file_data}, upsert=True)
    await message.reply_text(f"✅ Indexed Successfully:\n`{file_name}`")

# 2. Search Logic (Private Chat mein)
@app.on_message(filters.text & filters.private)
async def search(client, message):
    if message.text.startswith("/"): return
    
    query = message.text.lower()
    # Database mein partial search ke liye regex use kar rahe hain
    cursor = files_col.find({"file_name": {"$regex": query}})
    results = await cursor.to_list(length=15)

    if not results:
        await message.reply_text("❌ Sorry Jay! Movie nahi mili. Spelling check karein.")
        return

    buttons = []
    bot_username = (await client.get_me()).username
    
    for file in results:
        # Har file ke liye download link aur use GPLinks se shorten karna
        long_url = f"https://t.me/{bot_username}?start={file['file_id']}"
        short_url = get_shortlink(long_url)
        buttons.append([InlineKeyboardButton(f"🎬 {file['file_name'][:40]}", url=short_url)])

    await message.reply_text("🍿 Results Mil Gaye (Click to Download):", reply_markup=InlineKeyboardMarkup(buttons))

# 3. Start Command & File Delivery
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if len(message.command) > 1:
        file_id = message.command[1]
        try:
            await client.send_document(message.chat.id, file_id, caption="Aapki Movie Taiyar Hai! 🎥\n\nJoin: " + CHANNEL_LINK)
        except Exception as e:
            await message.reply_text(f"❌ Error: File send nahi ho saki. {e}")
    else:
        await message.reply_text(f"👋 Namaste Jay!\n\nMain movies dhoondh kar aapko earning link de sakta hoon. Bas movie ka naam likh kar bhejein.")

print("🤖 Bot is running 24x7 on Koyeb...")
app.run()
