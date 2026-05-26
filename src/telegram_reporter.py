import os
import requests
from datetime import datetime, timedelta
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

def get_next_run_message():
    """Calculates when the next scheduled 4-hour cron job runs relative to now."""
    now = datetime.now()
    now_utc = datetime.utcnow()
    current_hour = now_utc.hour
    
    # Next multiple of 4 hours
    next_hour = ((current_hour // 4) + 1) * 4
    if next_hour >= 24:
        next_run_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        next_run_utc = now_utc.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
    diff = next_run_utc - now_utc
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    local_next_run = now + diff
    time_str = local_next_run.strftime("%I:%M %p").strip()
    
    relative_str = ""
    if hours > 0:
        relative_str += f"{hours}h "
    relative_str += f"{minutes}m"
    
    return f"{time_str} (in {relative_str})"

def report_success(filename, seo_title, facebook_url, remaining_queue):
    current_time = datetime.now().strftime("%I:%M %p %Z")
    message = (
        "✅ <b>Facebook Reel Uploaded Successfully</b>\n\n"
        f"📁 <b>File:</b> {filename}\n"
        f"📝 <b>Title:</b> {seo_title}\n"
        f"🕒 <b>Uploaded At:</b> {current_time}\n"
        f"🔗 <b>Link:</b> {facebook_url}\n"
        f"📊 <b>Remaining Queue:</b> {remaining_queue}\n"
        f"⏭️ <b>Next Scheduled Run:</b> {get_next_run_message()}"
    )
    return send_telegram_message(message)

def report_failure(filename, error_message, remaining_queue):
    current_time = datetime.now().strftime("%I:%M %p %Z")
    message = (
        "❌ <b>Facebook Reel Upload Failed</b>\n\n"
        f"📁 <b>File:</b> {filename}\n"
        f"⚠️ <b>Error:</b> {error_message}\n"
        f"🕒 <b>Attempt At:</b> {current_time}\n"
        f"📊 <b>Remaining Queue:</b> {remaining_queue}\n"
        f"⏭️ <b>Next Scheduled Run:</b> {get_next_run_message()}"
    )
    return send_telegram_message(message)
