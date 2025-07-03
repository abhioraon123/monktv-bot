import nest_asyncio
nest_asyncio.apply()

import logging
import os
import json
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.error import TelegramError
from googleapiclient.discovery import build
from google.oauth2 import service_account
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets Setup
creds_json = os.environ.get('GOOGLE_CREDS')
creds_dict = json.loads(creds_json)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Website link
website_link = "\n\n📺 Visit: https://monktv.glide.page"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "Hey there! 👋 Send me a movie keyword and I’ll find it for you! 🔎" + website_link
    await update.message.reply_text(msg, reply_to_message_id=update.message.message_id)

# Search Function
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            reply = f"🎥 *{row[0]}*:\n{row[1]}{website_link}"
            sent = await update.message.reply_text(reply, parse_mode="Markdown")
            await context.bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id, delay=43200)
            return

    # No match found
    sent = await update.message.reply_text("🚫 No match found." + website_link)
    await context.bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id, delay=43200)

# Error Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="⚠️ Exception while handling an update:", exc_info=context.error)

# Main Function
async def main():
    app = ApplicationBuilder().token("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    app.add_error_handler(error_handler)

    print("Bot is running...")
    await app.run_polling()

# Run it
if __name__ == "__main__":
    asyncio.run(main())