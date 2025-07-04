import nest_asyncio
nest_asyncio.apply()

import logging
import json
import os
import asyncio
from fastapi import FastAPI, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
RANGE_NAME = "Sheet1!A:B"
AUTO_DELETE_DELAY = 43200  # 12 hours in seconds

# Google Sheets Setup
creds_dict = json.loads(GOOGLE_CREDS)
scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
sheet = build("sheets", "v4", credentials=creds).spreadsheets()

# FastAPI App
app = FastAPI()

# Telegram Application
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# Auto-delete
async def auto_delete(context: ContextTypes.DEFAULT_TYPE, chat_id, message_id):
    await asyncio.sleep(AUTO_DELETE_DELAY)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = await update.message.reply_text(
        "👋 Hello! Send me a keyword and I’ll search it for you! 🔍\n\n📺 Visit: https://monktv.glide.page"
    )
    await context.application.create_task(auto_delete(context, update.effective_chat.id, update.message.message_id))
    await context.application.create_task(auto_delete(context, reply.chat_id, reply.message_id))

# Keyword search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    for row in values:
        if query in row[0].lower():
            reply = await update.message.reply_text(
                f"🎥 {row[0]}:\n{row[1]}\n\n📺 https://monktv.glide.page"
            )
            await context.application.create_task(auto_delete(context, update.effective_chat.id, update.message.message_id))
            await context.application.create_task(auto_delete(context, reply.chat_id, reply.message_id))
            return

    reply = await update.message.reply_text("🚫 No match found. Try another keyword!\n📺 https://monktv.glide.page")
    await context.application.create_task(auto_delete(context, update.effective_chat.id, update.message.message_id))
    await context.application.create_task(auto_delete(context, reply.chat_id, reply.message_id))

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# FastAPI startup
@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    logger.info("✅ Bot started via webhook!")

# Webhook route
@app.post("/")
async def handle_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}