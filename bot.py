<<<<<<< HEAD
import nest_asyncio
nest_asyncio.apply()

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'monktv!A2:C'  # Skip the header row

# Authorize Sheets
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Send a title to get its 720p/1080p links.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        title = row[0].lower() if len(row) > 0 else ""
        if query in title:
            title_text = f"🎬 *{row[0]}*"
            link_720 = f"🔹 720p: {row[1]}" if len(row) > 1 and row[1] else ""
            link_1080 = f"🔹 1080p: {row[2]}" if len(row) > 2 and row[2] else ""
            message = "\n".join(filter(None, [title_text, link_720, link_1080]))
            await update.message.reply_text(message, parse_mode="Markdown")
            return
    await update.message.reply_text("❌ Title not found.")

# Main runner
async def main():
    app = ApplicationBuilder().token("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
=======
import os
import json
import logging
import gspread
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# 🧠 Logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 Load environment variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GOOGLE_CREDS_JSON = os.environ["GOOGLE_CREDS_JSON"]
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# ⚙️ Create FastAPI app
app = FastAPI()

# 📊 Connect to Google Sheets
creds_dict = json.loads(GOOGLE_CREDS_JSON)
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# 🧾 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\U0001F44B Welcome to MonkTV Bot!\n\n"
        "\U0001F50E Just type any movie or category name to search.\n"
        "\U0001F4FA Also visit: https://monktv.glide.page"
    )

# 🔎 Search handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()
    data = sheet.get_all_records()

    results = [
        row for row in data
        if query in row.get("Name", "").lower() or query in row.get("Category", "").lower()
    ]

    if results:
        for row in results[:5]:  # Show only top 5 matches
            name = row.get("Name", "No Title")
            link = row.get("Link", "No Link")
            text = f"\U0001F3A5 <b>{name}</b>\n\U0001F517 <a href='{link}'>Watch Now</a>"
            await update.message.reply_html(text, disable_web_page_preview=True)
    else:
        await update.message.reply_text("\u274C No match found.")

# 
>>>>>>> 56db08aa54cf4211e1bc41bb89de92c65ebcaf0b
