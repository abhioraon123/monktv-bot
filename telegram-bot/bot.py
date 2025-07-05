import os
import json
import logging
import gspread
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# Global bot app variable
telegram_app = None
sheet = None

# Emojis
EMOJI_MOVIE = "🎥"
EMOJI_SEARCH = "🔎"
EMOJI_SITE = "📺"
EMOJI_NO_MATCH = "🚫"

# Search function
def search_movies(query):
    if sheet is None:
        return []
    try:
        rows = sheet.get_all_records()
        query = query.lower()
        return [row for row in rows if query in str(row.get("Title", "")).lower()]
    except Exception as e:
        logger.error(f"❌ Error reading Google Sheet: {e}")
        return []

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Welcome to MonkTV Bot!*\n\n"
        f"{EMOJI_MOVIE} Send a movie name to search.\n"
        f"{EMOJI_SITE} Visit: https://monktv.glide.page"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# Handle search query
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    results = search_movies(query)

    if results:
        for movie in results[:5]:
            msg = f"{EMOJI_MOVIE} *{movie['Title']}*\n{EMOJI_SEARCH} [Watch Now]({movie['Link']})"
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            f"{EMOJI_NO_MATCH} No match found for *{query}*", parse_mode=ParseMode.MARKDOWN
        )

# FastAPI + PTB integration
@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app, sheet

    # Google Sheets auth
    try:
        gc = gspread.service_account_from_dict(json.loads(GOOGLE_CREDS_JSON))
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        logger.info("✅ Connected to Google Sheet")
    except Exception as e:
        logger.error(f"❌ Google Sheet connection error: {e}")
        sheet = None

    # Telegram App init
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set webhook
    try:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/telegram")
        logger.info(f"✅ Webhook set to {WEBHOOK_URL}/telegram")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

    await telegram_app.initialize()
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()

# FastAPI app instance
app = FastAPI(lifespan=lifespan)

# Webhook endpoint
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}