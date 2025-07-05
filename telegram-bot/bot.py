import os
import json
import logging
import gspread
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
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

# 📊 Connect to Google Sheets
creds_dict = json.loads(GOOGLE_CREDS_JSON)
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# ⚙️ Lifespan startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global application
    try:
        print("🚀 [lifespan] Starting bot initialization...")
        application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .build()
        )
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await application.initialize()
        print("✅ [lifespan] Application initialized.")

        await application.start()
        print("✅ [lifespan] Application started.")

        await application.bot.set_webhook(f"{WEBHOOK_URL}/telegram/webhook")
        print(f"✅ [lifespan] Webhook set to {WEBHOOK_URL}/telegram/webhook")

    except Exception as e:
        print(f"❌ [lifespan] Bot setup failed: {e}")

    yield

    print("🔻 [lifespan] Shutting down bot...")
    await application.stop()
    await application.shutdown()

# ⚙️ Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

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

# 📬 Webhook endpoint for Telegram
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("🔔 Incoming update:", data)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}