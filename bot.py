import nest_asyncio
nest_asyncio.apply()

import os
import json
import logging
import gspread
from fastapi import FastAPI, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials from environment variable
creds_json = os.environ.get('GOOGLE_CREDS')
creds_dict = json.loads(creds_json)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(credentials)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U'
RANGE_NAME = 'Sheet1!A:B'

creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

# Telegram bot token
BOT_TOKEN = "7346055162:AAEpJC6HWmnG3sywQtBw_b3-TRqM6Ka0AkA"
bot = Bot(token=BOT_TOKEN)

# FastAPI app
app = FastAPI()

@app.post("/")
async def handle_update(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot)
    await application.process_update(update)
    return "ok"

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://your-service-name.onrender.com"
    await bot.set_webhook(url=webhook_url)

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👋 Welcome to MonkTV Bot!\n\nSend me a movie or topic to search 🔎"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    for row in values:
        if query in row[0].lower():
            reply = f"🎥 *{row[0]}*\n🔗 {row[1]}\n\n📺 Visit: https://monktv.glide.page"
            sent = await context.bot.send_message(chat_id=update.effective_chat.id, text=reply, parse_mode="Markdown")
            
            # Auto-delete after 12 hours (43200 seconds)
            await context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id),
                when=43200,
                data=None
            )
            return

    await context.bot.send_message(chat_id=update.effective_chat.id, text="🚫 No match found.")

# Build Application
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

# Port binding for Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)