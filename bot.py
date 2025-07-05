import os
import logging
import json
import gspread
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# Google Sheets setup
try:
    creds_dict = json.loads(GOOGLE_CREDS_JSON)
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sh.sheet1
    logger.info("✅ Connected to Google Sheet")
except Exception as e:
    logger.error(f"❌ Google Sheets Error: {e}")
    raise e

# FastAPI app
app = FastAPI()

# Telegram App setup
telegram_app = Application.builder().token(BOT_TOKEN).build()

# 📌 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎥 Movies", url="https://t.me/monktvclub")],
        [InlineKeyboardButton("📺 Website", url="https://monktv.glide.page")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to MonkTV! 🍿", reply_markup=reply_markup)

# 📌 Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()
    rows = worksheet.get_all_records()
    for row in rows:
        if query in row["Name"].lower():
            reply = f"🎬 *{row['Name']}*\n\n🔗 {row['Link']}"
            await update.message.reply_text(reply, parse_mode="Markdown")
            return
    await update.message.reply_text("🚫 No match found.")

# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🚀 Webhook endpoint
@app.post("/")
async def telegram_webhook(request: Request):
    update_dict = await request.json()
    update = Update.de_json(update_dict, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# 🌀 Startup hook for webhook
@app.on_event("startup")
async def on_startup():
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    logger.info(f"🚀 Webhook set to: {WEBHOOK_URL}")