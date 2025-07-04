import os
import json
from http import HTTPStatus
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from google.oauth2.service_account import Credentials

# 🔐 Load credentials
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
creds_dict = json.loads(GOOGLE_CREDS)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
SPREADSHEET_ID = "1K-Nuv4dB8_MPBvk-Jc4Qr_Haa4nW6Z8z2kbfUemYe1U"
RANGE_NAME = "Sheet1!A:B"

# 🔧 Telegram Bot setup
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # set in Render environment tab
scheduler = AsyncIOScheduler()
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 🚀 FastAPI app with lifespan hook
@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_telegram.bot.set_webhook(WEBHOOK_URL)
    async with app_telegram:
        await app_telegram.start()
        yield
        await app_telegram.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, app_telegram.bot)
    await app_telegram.process_update(update)
    return Response(status_code=HTTPStatus.OK)

# 🧼 Auto-delete handler (12 hours = 43200 sec)
async def delete_after_12hrs(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await app_telegram.bot.delete_message(chat_id=job.chat_id, message_id=job.message_id)
    except Exception as e:
        print(f"Delete failed: {e}")

# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = await update.message.reply_text("👋 Hello! Send me a keyword and I’ll search it for you!")
    context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=reply.chat_id, message_id=reply.message_id)
    context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=update.message.chat_id, message_id=update.message.message_id)

# 🔍 Search handler
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    rows = result.get("values", [])

    for row in rows:
        if query in row[0].lower():
            reply = await update.message.reply_text(f"🎥 {row[0]}:\n{row[1]}\n\n📺 https://monktv.glide.page")
            context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=reply.chat_id, message_id=reply.message_id)
            context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=update.message.chat_id, message_id=update.message.message_id)
            return

    reply = await update.message.reply_text("🚫 No match found. Try another keyword!\n📺 https://monktv.glide.page")
    context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=reply.chat_id, message_id=reply.message_id)
    context.job_queue.run_once(delete_after_12hrs, 43200, chat_id=update.message.chat_id, message_id=update.message.message_id)

# 🔌 Register handlers
app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))