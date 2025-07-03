import nest_asyncio
nest_asyncio.apply()

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import json
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

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'
SERVICE_ACCOUNT_FILE = 'credentials.json'

# Authorize Sheets API
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🎬 *Welcome to MonkTV Bot!*\n\nJust type a keyword to search 🔎 your movie or series.\n\n📺 *Visit us:* monktv.glide.page"
    sent_msg = await update.message.reply_text(msg, parse_mode="Markdown")
    await context.bot.delete_message(chat_id=sent_msg.chat_id, message_id=sent_msg.message_id, delay=43200)  # 12 hrs

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            msg = f"🎥 *{row[0]}*\n\n🔗 {row[1]}\n\n📺 *More:* monktv.glide.page"
            sent_msg = await update.message.reply_text(msg, parse_mode="Markdown")
            await context.bot.delete_message(chat_id=sent_msg.chat_id, message_id=sent_msg.message_id, delay=43200)
            return

    no_match = "🚫 *No match found!*\nTry a different keyword.\n\n📺 *Visit:* monktv.glide.page"
    sent_msg = await update.message.reply_text(no_match, parse_mode="Markdown")
    await context.bot.delete_message(chat_id=sent_msg.chat_id, message_id=sent_msg.message_id, delay=43200)

# Main function
async def main():
    app = ApplicationBuilder().token("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("Bot is running...")
    await app.run_polling()

# Run the bot
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())