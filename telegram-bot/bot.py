import os
import json
import logging
import gspread
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
application = None
worksheet = None

def load_environment_variables():
    """Load and validate environment variables"""
    try:
        required_vars = ['BOT_TOKEN', 'WEBHOOK_URL', 'GOOGLE_CREDS_JSON']
        for var in required_vars:
            if not os.getenv(var):
                raise ValueError(f"❌ Missing required environment variable: {var}")
        
        logger.info("✅ Environment variables loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Environment setup failed: {e}")
        return False

def setup_google_sheets():
    """Setup Google Sheets connection"""
    global worksheet
    try:
        google_creds = json.loads(os.getenv('GOOGLE_CREDS_JSON'))
        gc = gspread.service_account_from_dict(google_creds)
        worksheet = gc.open("MonkTV Search Results").sheet1
        logger.info("✅ Google Sheets connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Google Sheets setup failed: {e}")
        return False

def search_google_sheets(query: str) -> str:
    """Search Google Sheets for the query"""
    try:
        if not worksheet:
            return "❌ Google Sheets not connected"
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Filter records that match the query
        matching_records = []
        for record in records:
            # Check if query matches in any field
            for key, value in record.items():
                if query.lower() in str(value).lower():
                    matching_records.append(record)
                    break
        
        if not matching_records:
            return f"❌ No results found for '{query}'"
        
        # Format results
        result_text = f"🔍 Search Results for '{query}':\n\n"
        for i, record in enumerate(matching_records[:5], 1):  # Limit to 5 results
            result_text += f"{i}. "
            for key, value in record.items():
                if value:  # Only show non-empty values
                    result_text += f"{key}: {value} | "
            result_text = result_text.rstrip(" | ") + "\n\n"
        
        return result_text
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return f"❌ Search error: {str(e)}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        await update.message.reply_text(
            "🤖 Welcome to MonkTV Search Bot!\n\n"
            "Use /search <query> to search our database.\n"
            "Example: /search your query here"
        )
    except Exception as e:
        logger.error(f"❌ Start command failed: {e}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Please provide a search query.\nExample: /search your query")
            return
        
        query = ' '.join(context.args)
        logger.info(f"🔍 Searching for: {query}")
        
        # Search Google Sheets
        result = search_google_sheets(query)
        
        # Send result
        await update.message.reply_text(result)
        
    except Exception as e:
        logger.error(f"❌ Search command failed: {e}")
        await update.message.reply_text(f"❌ Search failed: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    try:
        message = update.message.text
        logger.info(f"📨 Received message: {message}")
        
        # If message doesn't start with /, treat as search
        if not message.startswith('/'):
            result = search_google_sheets(message)
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("❌ Unknown command. Use /search <query> to search.")
            
    except Exception as e:
        logger.error(f"❌ Message handling failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global application
    
    try:
        # Load environment variables
        if not load_environment_variables():
            raise Exception("Environment setup failed")
        
        # Setup Google Sheets
        if not setup_google_sheets():
            raise Exception("Google Sheets setup failed")
        
        # Initialize bot
        logger.info("🚀 Starting bot initialization...")
        
        application = (
            Application.builder()
            .token(os.getenv('BOT_TOKEN'))
            .build()
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Initialize application
        await application.initialize()
        
        # Set webhook
        webhook_url = f"{os.getenv('WEBHOOK_URL')}/telegram/webhook"
        await application.bot.set_webhook(webhook_url)
        
        logger.info("✅ Bot initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Bot setup failed: {e}")
        raise
    finally:
        # Cleanup
        if application:
            await application.shutdown()

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "MonkTV Bot is running"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhooks"""
    try:
        if not application:
            logger.error("❌ Application not initialized")
            raise HTTPException(status_code=500, detail="Bot not initialized")
        
        # Get update data
        data = await request.json()
        
        # Create update object
        update = Update.de_json(data, application.bot)
        
        # Process update
        await application.process_update(update)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))