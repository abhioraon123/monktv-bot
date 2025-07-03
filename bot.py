import nest_asyncio
nest_asyncio.apply()

import logging
import os
import json
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from googleapiclient.discovery import build
from google.oauth2 import service_account

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

SERVICE_ACCOUNT_FILE = "credentials.json"  # dummy, not used with os.environ creds
sheet = build('sheets', 'v4', credentials=credentials).spreadsheets()

# Website link
WEBSITE_LINK = "📺 Visit: https://monktv.glide.page"

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sent = await update.message.reply_text("👋 Welcome to MonkTV Bot! Send me a keyword to search 🔎\n" + WEBSITE_LINK)
    await schedule_delete(context, sent)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            sent = await update.message.reply_text(f"🎥 *{row[0]}*: {row[1]}\n\n{WEBSITE_LINK}", parse_mode='Markdown')
            await schedule_delete(context, sent)
            return

    sent = await update.message.reply_text("🚫 No match found!\n\n" + WEBSITE_LINK)
    await schedule_delete(context, sent)

# Schedule delete after 12 hours (43200 seconds)
async def schedule_delete(context, message):
    await asyncio.sleep(43200)  # 12 hours
    try:
        await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")

# Main
async def main():
    app = ApplicationBuilder().token("7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("🚀 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())