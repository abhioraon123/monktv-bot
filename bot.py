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