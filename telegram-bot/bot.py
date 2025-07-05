import os
import json
import gspread
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# Google Sheets setup
creds_dict = json.loads(GOOGLE_CREDS_JSON)
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# FastAPI app
app = FastAPI()

# Telegram bot app
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()


# 🟡 Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to MonkTV Bot!\n\n"
        "Send me a keyword and I’ll fetch study materials for you! 🔍"
    )


# 🟢 Main search handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    records = sheet.get_all_records()

    matches = []
    for row in records:
        if query in row["name"].lower():
            matches.append(f'🎥 {row["name"]} - {row["link"]}')

    if matches:
        reply = "\n\n".join(matches)
    else:
        reply = "🚫 No match found. Try different keywords."

    await update.message.reply_text(reply)


# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ✅ Set webhook when app starts
@app.on_event("startup")
async def on_startup():
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook set")


# ❌ Remove webhook on shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.bot.delete_webhook()
    print("🛑 Webhook deleted")


# 📬 Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}