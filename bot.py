import os
import json
import asyncio
import logging
import gspread
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# FastAPI app
app = FastAPI()
telegram_app: Application = None
sheet = None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📺 Visit Website", url="https://monktv.glide.page")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        "Hey there! 👋\nSend me the name of the movie or topic you're looking for 🎥",
        reply_markup=reply_markup
    )
    context.job_queue.run_once(delete_message_after_delay, 43200, data=msg.message_id, chat_id=msg.chat_id)

# Query search
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    data = sheet.get_all_values()
    rows = data[1:]

    found = []
    for row in rows:
        if any(query in cell.lower() for cell in row):
            found.append(row)

    if found:
        for row in found:
            title, link = row[0], row[1]
            msg = await update.message.reply_text(
                f"🎥 <b>{title}</b>\n👉 <a href='{link}'>Watch Now</a>",
                parse_mode=ParseMode.HTML
            )
            context.job_queue.run_once(delete_message_after_delay, 43200, data=msg.message_id, chat_id=msg.chat_id)
    else:
        msg = await update.message.reply_text("🚫 No match found. Try something else?")
        context.job_queue.run_once(delete_message_after_delay, 43200, data=msg.message_id, chat_id=msg.chat_id)

# Delete message after delay
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(43200)
    try:
        await context.bot.delete_message(
            chat_id=context.job.chat_id,
            message_id=context.job.data
        )
    except BadRequest as e:
        if "message can't be deleted" in str(e):
            pass
        else:
            logger.warning(f"Telegram BadRequest: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while deleting message: {e}")

# Startup & shutdown using FastAPI lifespan
@app.on_event("startup")
async def on_startup():
    global telegram_app, sheet

    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        creds_dict = json.loads(creds_json)
        gc = gspread.service_account_from_dict(creds_dict)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        logger.info("✅ Connected to Google Sheet")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Google Sheet: {e}")
        raise

    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/telegram")
    logger.info(f"✅ Webhook set to {WEBHOOK_URL}/telegram")

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("🛑 Bot shut down cleanly")

# Webhook route
@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}