import nest_asyncio
nest_asyncio.apply()

import logging
import os
import json
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

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

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

# Authorize Google Sheets
SERVICE_ACCOUNT_FILE = "credentials.json"
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Telegram Bot Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text(
        "Welcome! Send a keyword to search.\n\n📺 Visit us: https://monktv.glide.page"
    )
    await asyncio.sleep(43200)  # 12 hours = 43,200 seconds
    try:
        await message.delete()
    except:
        pass

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            message = await update.message.reply_text(
                f'{row[0]}: {row[1]}\n\n📺 Visit us: https://monktv.glide.page'
            )
            await asyncio.sleep(43200)
            try:
                await message.delete()
            except:
                pass
            return

    message = await update.message.reply_text(
        "No match found.\n\n📺 Visit us: https://monktv.glide.page"
    )
    await asyncio.sleep(43200)
    try:
        await message.delete()
    except:
        pass

# Main Function
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