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
    """Calculates when the next scheduled upload slot is in US Eastern Time."""
    from zoneinfo import ZoneInfo
    
    # Get current time in US Eastern Time
    est_now = datetime.now(ZoneInfo('America/New_York'))
    current_hour = est_now.hour
    
    scheduled_hours = sorted([0, 8, 12, 16, 20])
    
    next_hour = None
    next_day = False
    
    for h in scheduled_hours:
        if h > current_hour:
            next_hour = h
            break
            
    if next_hour is None:
        # Next run is midnight tomorrow EST
        next_hour = 0
        next_day = True
        
    if next_day:
        next_run_est = est_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        next_run_est = est_now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
    diff = next_run_est - est_now
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    # We display time_str in EST/EDT format since uploads are scheduled in EST
    time_str = next_run_est.strftime("%I:%M %p %Z").strip()
    
    relative_str = ""
    if hours > 0:
        relative_str += f"{hours}h "
    relative_str += f"{minutes}m"
    
    return f"{time_str} (in {relative_str})"

def report_success(filename, seo_title, facebook_url, remaining_queue):
    from zoneinfo import ZoneInfo
    current_time = datetime.now(ZoneInfo('America/New_York')).strftime("%I:%M %p %Z")
    message = (
        "✅ <b>Video Successfully Uploaded</b>\n\n"
        f"📁 <b>Video Name:</b> {filename}\n\n"
        f"🕒 <b>Upload Time:</b> {current_time}\n\n"
        f"🔗 <b>Facebook Video Link:</b> {facebook_url}\n\n"
        f"⏰ <b>Next Scheduled Upload:</b> {get_next_run_message()}"
    )
    return send_telegram_message(message)

def report_failure(filename, error_message, remaining_queue):
    from zoneinfo import ZoneInfo
    current_time = datetime.now(ZoneInfo('America/New_York')).strftime("%I:%M %p %Z")
    message = (
        "❌ <b>Video Upload Failed</b>\n\n"
        f"📁 <b>Video Name:</b> {filename}\n\n"
        f"⚠️ <b>Error:</b> {error_message}\n\n"
        f"🕒 <b>Attempt Time:</b> {current_time}\n\n"
        f"⏰ <b>Next Scheduled Upload:</b> {get_next_run_message()}"
    )
    return send_telegram_message(message)
