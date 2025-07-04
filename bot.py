import os
import json
import logging
import nest_asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from google.oauth2 import service_account
from googleapiclient.discovery import build

nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env vars
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDS")

# Google Sheets setup
creds_dict = json.loads(GOOGLE_CREDS)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
RANGE_NAME = "Sheet1!A:B"
creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build("sheets", "v4", credentials=creds).spreadsheets()

# FastAPI app
app = FastAPI()

# Telegram bot
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 👋 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Hello! Send me a keyword and I’ll search it for you! 🔍\n\n📺 Visit: https://monktv.glide.page"
    )
    # Auto-delete after 12 hours (43200 sec)
    await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id, delay=43200)

# 🔎 Search handler
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get("values", [])

    for row in values:
        if query in row[0].lower():
            msg = await update.message.reply_text(
                f"🎥 {row[0]}:\n{row[1]}\n\n📺 https://monktv.glide.page"
            )
            await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id, delay=43200)
            return

    msg = await update.message.reply_text(
        "🚫 No match found. Try another keyword!\n📺 https://monktv.glide.page"
    )
    await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id, delay=43200)

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# 🚀 Startup
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.start()

# 🌐 Webhook route
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}