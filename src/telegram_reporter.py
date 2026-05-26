import os
import requests
from datetime import datetime
try:
    from .logger import logger
except ImportError:
    from logger import logger

def send_telegram_message(message):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.warning("Telegram bot configuration is missing. Skipping Telegram notification.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def report_success(filename, seo_title, facebook_url, remaining_queue):
    current_time = datetime.now().strftime("%I:%M %p %Z")
    message = (
        "✅ <b>Facebook Reel Uploaded Successfully</b>\n\n"
        f"📁 {filename}\n"
        f"📝 {seo_title}\n"
        f"🕒 {current_time}\n"
        f"🔗 {facebook_url}\n"
        f"📊 Remaining Queue: {remaining_queue}"
    )
    return send_telegram_message(message)

def report_failure(filename, error_message, remaining_queue):
    current_time = datetime.now().strftime("%I:%M %p %Z")
    message = (
        "❌ <b>Facebook Reel Upload Failed</b>\n\n"
        f"📁 {filename}\n"
        f"⚠️ {error_message}\n"
        f"🕒 {current_time}\n"
        f"📊 Remaining Queue: {remaining_queue}"
    )
    return send_telegram_message(message)
