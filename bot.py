# bot.py
import os
from http import HTTPStatus
from contextlib import asynccontextmanager

import gspread
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Telegram Bot Setup ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Set your bot token in environment
WEBHOOK_URL = os.getenv("WEBHOOK_URL")       # Set your Render app's URL here
# Initialize the PTB application (no Updater, use builder)
app_builder = ApplicationBuilder().token(BOT_TOKEN)
application = app_builder.build()

# --- Google Sheets Setup ---
# Provide path to your service account JSON and sheet name
gc = gspread.service_account(filename='service_account.json')
sheet = gc.open("YourSpreadsheetName").sheet1  # open your Google Sheet

# --- FastAPI Application and Webhook Endpoint ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set the Telegram webhook to our Render URL on startup
    await application.bot.setWebhook(WEBHOOK_URL)
    async with application:
        await application.start()
        yield
        await application.stop()

app = FastAPI(lifespan=lifespan)

@app.post("/")  # Telegram will send updates to this endpoint
async def receive_update(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=HTTPStatus.OK)

# --- Handler Functions ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Example /start command handler."""
    await update.message.reply_text("Hello! I am your bot 👋")
    
    # Schedule auto-delete of this message after 12 hours (43200 seconds)
    sent_msg = await update.message.reply_text("This message will self-destruct in 12 hours 🔥")
    context.job_queue.run_once(lambda ctx: ctx.job.context(), 43200, context=sent_msg.delete)

async def log_to_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Example handler to log data to Google Sheets."""
    user = update.effective_user.username or update.effective_user.id
    text = update.message.text
    sheet.append_row([user, text])  # Add a new row with user and message

# Register handlers
application.add_handler(CommandHandler("start", start_cmd))
application.add_handler(CommandHandler("log", log_to_sheet))

# Note: On Render, start this app with a command like:
# uvicorn bot:app --host 0.0.0.0 --port $PORT