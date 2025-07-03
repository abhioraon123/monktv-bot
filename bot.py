import nest_asyncio
nest_asyncio.apply()

import os
import json
import logging
from fastapi import FastAPI, Request
import uvicorn

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from googleapiclient.discovery import build
from google.oauth2 import service_account
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
creds_json = os.environ.get('GOOGLE_CREDS')
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

service_creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
sheet = build('sheets', 'v4', credentials=service_creds).spreadsheets()

# Telegram bot token and app
BOT_TOKEN = os.environ.get("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA
")
app = FastAPI()

# Telegram application setup
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me a keyword and I’ll find your study material 📚")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            message = f"🔎 {row[0]}: {row[1]}\n\n📺 Visit: https://monktv.glide.page"
            sent = await update.message.reply_text(message)
            # Auto-delete after 12 hours (43200 seconds)
            await context.application.create_task(context.bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id, timeout=43200))
            return
    await update.message.reply_text("🚫 No match found. Try another keyword!")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# Webhook route
@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"status": "ok"}

# Startup event
@app.on_event("startup")
async def startup():
    logger.info("Bot is starting via webhook...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down bot...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

# Run with uvicorn if local
if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=10000)