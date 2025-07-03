import nest_asyncio
nest_asyncio.apply()

import os
import json
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)
from googleapiclient.discovery import build
from google.oauth2 import service_account
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials from environment
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

google_creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build('sheets', 'v4', credentials=google_creds).spreadsheets()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Add this in Render env too

app = FastAPI()
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send a keyword to search.")

# Message Handler
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            reply = f"🔎 *{row[0]}*\n\n🎥 {row[1]}\n\n📺 Visit: monktv.glide.page"
            sent = await update.message.reply_text(reply, parse_mode="Markdown")
            await asyncio.sleep(43200)  # wait 12 hours
            await sent.delete()
            return

    await update.message.reply_text("🚫 No match found.")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# FastAPI Startup
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Bot started via webhook!")

# Telegram Webhook
@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}