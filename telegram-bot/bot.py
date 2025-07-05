import os
import json
import logging
import gspread
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# 🧠 Logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 Load environment variables
BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
GOOGLE_CREDS_JSON = os.environ["GOOGLE_CREDS_JSON"]
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"

# ⚙️ Create FastAPI app
app = FastAPI()

# 📊 Connect to Google Sheets
creds_dict = json.loads(GOOGLE_CREDS_JSON)
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# 🧾 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to MonkTV Bot!\n\n"
        "🔎 Just type any movie or category name to search.\n"
        "📺 Also visit: https://monktv.glide.page"
    )

# 🔎 Search handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()
    data = sheet.get_all_records()

    results = [
        row for row in data
        if query in row.get("Name", "").lower() or query in row.get("Category", "").lower()
    ]

    if results:
        for row in results[:5]:  # Show only top 5 matches
            name = row.get("Name", "No Title")
            link = row.get("Link", "No Link")
            text = f"🎥 <b>{name}</b>\n🔗 <a href='{link}'>Watch Now</a>"
            await update.message.reply_html(text, disable_web_page_preview=True)
    else:
        await update.message.reply_text("🚫 No match found.")

# 🚀 Webhook setup on bot startup
@app.on_event("startup")
async def on_startup():
    global application
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(set_webhook)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await application.initialize()
    await application.start()

# 🧠 Webhook registration
async def set_webhook(app):
    await app.bot.set_webhook(WEBHOOK_URL)

# 📴 Graceful shutdown
@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()

# 📬 Webhook endpoint for Telegram
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}