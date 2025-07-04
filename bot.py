import os
import logging
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
)
import gspread

# 📌 Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📌 Load from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")

# 📌 Google Sheets setup
gc = gspread.service_account_from_dict(eval(GOOGLE_CREDS))
sheet = gc.open_by_key("1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U").sheet1

# 📌 FastAPI app
app = FastAPI()

# 🧠 Your bot logic
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    rows = sheet.get_all_values()
    matched = None
    for row in rows:
        if user_message in row[0].lower():
            matched = row[1]
            break

    if matched:
        msg = f"🎥 Here you go: {matched}"
    else:
        msg = "🚫 No match found. Try again!"

    sent = await update.message.reply_text(msg)
    context.job_queue.run_once(
        lambda ctx: asyncio.create_task(sent.delete()),
        when=43200,  # 12 hours
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to MonkTV Bot!")

# 🛠️ Build application
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# 🚀 Webhook FastAPI endpoint
@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return {"ok": True}

# 🌱 Lifespan event to start bot with job queue
@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    logger.info("Bot started via webhook on Render ✅")

@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()
    logger.info("Bot shut down gracefully ✨")