import os
import json
import base64
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
)

# 🌐 Load Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

if not BOT_TOKEN or not WEBHOOK_URL or not GOOGLE_CREDS_JSON:
    raise ValueError("❌ Missing required environment variables: BOT_TOKEN, WEBHOOK_URL, or GOOGLE_CREDS_JSON")

# 📄 Decode Google Service Account JSON from base64
creds_dict = json.loads(base64.b64decode(GOOGLE_CREDS_JSON))
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open_by_index(0).sheet1

# 🤖 Create Telegram Bot Application
application = Application.builder().token(BOT_TOKEN).build()

# 🌐 FastAPI with lifespan to start/stop the bot
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.bot.set_webhook(WEBHOOK_URL)
    async with application:
        await application.start()
        yield
        await application.stop()

app = FastAPI(lifespan=lifespan)

# 📬 Webhook route to receive Telegram updates
@app.post("/")
async def receive_update(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=HTTPStatus.OK)

# 🚀 /start command
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Welcome to MonkTV bot.")
    msg = await update.message.reply_text("This message will self-destruct in 12 hours 🔥")
    context.job_queue.run_once(lambda ctx: ctx.job.context(), 43200, context=msg.delete)

# 📝 /log command to log message in Google Sheet
async def log_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or str(update.effective_user.id)
    text = update.message.text
    sheet.append_row([user, text])
    await update.message.reply_text("✅ Logged to sheet!")

# 🎯 Register handlers
application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("log", log_to_sheet))