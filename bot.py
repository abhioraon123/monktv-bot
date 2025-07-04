import os
import json
import base64
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
)

# --- ENV VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# --- Decode Google Credentials ---
creds_dict = json.loads(base64.b64decode(GOOGLE_CREDS_JSON))
gc = gspread.service_account_from_dict(creds_dict)
sheet = gc.open("YourSpreadsheetName").sheet1  # 📌 Replace with your actual sheet name

# --- Setup PTB Application ---
application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Command: /start ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Hello! I am your bot 👋")
    context.job_queue.run_once(lambda ctx: msg.delete(), 43200)  # 12 hours

# --- Command: /log ---
async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username or str(update.effective_user.id)
    text = update.message.text
    sheet.append_row([user, text])
    await update.message.reply_text("✅ Logged to Google Sheet!")

# --- Register handlers ---
application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("log", log_cmd))

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.bot.setWebhook(WEBHOOK_URL)
    async with application:
        await application.start()
        yield
        await application.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=HTTPStatus.OK)