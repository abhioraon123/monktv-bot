# Just triggering redeploy import os
import json
import logging
import gspread
from io import StringIO
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
)
from telegram.constants import ParseMode

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# FastAPI app
app = FastAPI()
telegram_app = None  # Will be initialized on startup
sheet = None  # Will be loaded during startup

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📺 Visit Website", url="https://monktv.glide.page")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        "Hey there! 👋\nSend me the name of the movie or topic you're looking for 🎥",
        reply_markup=reply_markup
    )
    context.job_queue.run_once(delete_message, 43200, data={"chat_id": msg.chat_id, "message_id": msg.message_id})

# Search query handler
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    data = sheet.get_all_values()

    header = data[0]
    rows = data[1:]

    found = []
    for row in rows:
        if any(query in cell.lower() for cell in row):
            found.append(row)

    if found:
        for row in found:
            title = row[0]
            link = row[1]
            msg = await update.message.reply_text(
                f"🎥 <b>{title}</b>\n👉 <a href='{link}'>Watch Now</a>",
                parse_mode=ParseMode.HTML
            )
            context.job_queue.run_once(delete_message, 43200, data={"chat_id": msg.chat_id, "message_id": msg.message_id})
    else:
        msg = await update.message.reply_text("🚫 No match found. Try something else?")
        context.job_queue.run_once(delete_message, 43200, data={"chat_id": msg.chat_id, "message_id": msg.message_id})

# Auto-delete job
async def delete_message(context: CallbackContext):
    job_data = context.job.data
    try:
        await context.bot.delete_message(chat_id=job_data["chat_id"], message_id=job_data["message_id"])
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

# PTB startup and shutdown
@app.on_event("startup")
async def startup():
    global telegram_app, sheet

    # Connect to Google Sheet
    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        creds_dict = json.loads(creds_json)
        gc = gspread.service_account_from_dict(creds_dict)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        logger.info("✅ Successfully connected to Google Sheet")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Sheet: {e}")
        raise

    # Start Telegram App
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/telegram")

@app.on_event("shutdown")
async def shutdown():
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()

# Telegram webhook endpoint
@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}