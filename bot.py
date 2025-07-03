import nest_asyncio
nest_asyncio.apply()

import logging
import json
import os
import asyncio
from fastapi import FastAPI, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update, Message
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram token from Render environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Google Sheets setup
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
RANGE_NAME = "Sheet1!A:B"

creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build("sheets", "v4", credentials=creds).spreadsheets()

# FastAPI app
app = FastAPI()

# Telegram bot app
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# 🧹 Auto-delete message after 12 hours
async def auto_delete(message: Message):
    await asyncio.sleep(43200)  # 12 hours
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"❌ Failed to delete message: {e}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Hello! Send me a keyword and I’ll search it for you! 🔍\n\n📺 Visit: https://monktv.glide.page"
    )
    asyncio.create_task(auto_delete(sent))

# Search function
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    for row in values:
        if query in row[0].lower():
            sent = await update.message.reply_text(
                f"🎥 {row[0]}:\n{row[1]}\n\n📺 https://monktv.glide.page"
            )
            asyncio.create_task(auto_delete(sent))
            return

    sent = await update.message.reply_text(
        "🚫 No match found. Try another keyword!\n📺 https://monktv.glide.page"
    )
    asyncio.create_task(auto_delete(sent))

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# FastAPI startup event
@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

@app.post("/")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}