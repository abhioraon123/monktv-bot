import os
import logging
import json
import gspread
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# Connect to Google Sheet
try:
    gc = gspread.service_account_from_dict(json.loads(GOOGLE_CREDS_JSON))
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    logger.info("✅ Connected to Google Sheet")
except Exception as e:
    logger.error(f"❌ Error connecting to Google Sheet: {e}")
    sheet = None

# FastAPI app
app = FastAPI()
telegram_app = None  # PTB Application

# Emojis
EMOJI_MOVIE = "🎥"
EMOJI_SEARCH = "🔎"
EMOJI_SITE = "📺"
EMOJI_NO_MATCH = "🚫"

# Search function
def search_movies(query):
    if sheet is None:
        return []
    rows = sheet.get_all_records()
    query = query.lower()
    return [row for row in rows if query in str(row.get("Title", "")).lower()]

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Welcome to MonkTV Bot!*\n\n"
        f"{EMOJI_MOVIE} Send a movie name to search.\n"
        f"{EMOJI_SITE} Visit: https://monktv.glide.page"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# Handle search
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    results = search_movies(query)
    if results:
        for movie in results[:5]:
            msg = f"{EMOJI_MOVIE} *{movie['Title']}*\n{EMOJI_SEARCH} [Watch Now]({movie['Link']})"
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"{EMOJI_NO_MATCH} No match found for *{query}*", parse_mode=ParseMode.MARKDOWN)

# Telegram webhook endpoint
@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, Bot(BOT_TOKEN))
    await telegram_app.process_update(update)
    return {"ok": True}

# On startup
@app.on_event("startup")
async def on_startup():
    global telegram_app
    logger.info("🚀 Starting Telegram application...")
    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/telegram")
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}/telegram")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")