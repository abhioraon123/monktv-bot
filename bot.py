import nest_asyncio
nest_asyncio.apply()

import os
import json
import logging
from fastapi import FastAPI, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot and Google Sheets config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
RANGE_NAME = "Sheet1!A:B"

# Setup Google Sheets credentials
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build("sheets", "v4", credentials=creds).spreadsheets()

# FastAPI app
app = FastAPI()

# Telegram Application (NO UPDATER)
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# Command handler: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "👋 Hello! Send me a keyword and I’ll search it for you! 🔍\n\n📺 Visit: https://monktv.glide.page"
    )
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id, delay=30)

# Message handler: search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    for row in values:
        if query in row[0].lower():
            msg = await update.message.reply_text(
                f"🎥 {row[0]}:\n{row[1]}\n\n📺 https://monktv.glide.page"
            )
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id, delay=30)
            return

    msg = await update.message.reply_text("🚫 No match found. Try another keyword!\n📺 https://monktv.glide.page")
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg.message_id, delay=30)

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# FastAPI startup
@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    logger.info("✅ Bot started via webhook on Render!")

# Telegram webhook receiver
@app.post("/")
async def receive_update(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}