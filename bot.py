import nest_asyncio
nest_asyncio.apply()

import logging
import os
import json
import gspread
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from googleapiclient.discovery import build
from google.oauth2 import service_account
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import FastAPI, Request
from telegram.ext import Application

# 🔒 Credentials
creds_json = os.environ.get('GOOGLE_CREDS')
creds_dict = json.loads(creds_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_gspread = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials_gspread)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
credentials_api = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build('sheets', 'v4', credentials=credentials_api).spreadsheets()
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

# 📋 Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🌐 FastAPI for webhook
app = FastAPI()
BOT_TOKEN = "7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA"
WEBHOOK_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"

# 🤖 Bot logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me a keyword to search 🎥")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            reply = f"🔎 *{row[0]}*:\n{row[1]}\n\n📺 Visit: monktv.glide.page"
            sent = await update.message.reply_text(reply, parse_mode="Markdown")
            await asyncio.sleep(43200)  # 12 hours
            await sent.delete()
            return

    sent = await update.message.reply_text("🚫 No match found.\n\n📺 Visit: monktv.glide.page")
    await asyncio.sleep(43200)  # 12 hours
    await sent.delete()

# ⛓️ Connect bot with FastAPI
@app.on_event("startup")
async def on_startup():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    app.bot_app = application
    asyncio.create_task(application.initialize())
    asyncio.create_task(application.start())

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, app.bot_app.bot)
    await app.bot_app.process_update(update)
    return {"ok": True}