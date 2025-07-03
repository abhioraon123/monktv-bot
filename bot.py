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
RANGE_NAME = 'Sheet1!A:B'

# Authorize Google Sheets
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a keyword to search.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            await update.message.reply_text(f'{row[0]}: {row[1]}')
            return
    await update.message.reply_text("No match found.")

# Main Function
async def main():
    app = ApplicationBuilder().token("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("Bot is running...")
    await app.run_polling()

# Run the bot
if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
