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
    from datetime import datetime, timedelta
    
    # Get current time in US Eastern Time
    est_now = datetime.now(ZoneInfo('America/New_York'))
    
    SLOTS = [
        {'hour': 8, 'minute': 0, 'type': 'reel'},
        {'hour': 10, 'minute': 30, 'type': 'photo'},
        {'hour': 12, 'minute': 30, 'type': 'reel'},
        {'hour': 15, 'minute': 0, 'type': 'photo'},
        {'hour': 17, 'minute': 0, 'type': 'reel'},
        {'hour': 19, 'minute': 0, 'type': 'photo'},
        {'hour': 20, 'minute': 30, 'type': 'reel'},
        {'hour': 22, 'minute': 30, 'type': 'photo'},
        {'hour': 23, 'minute': 45, 'type': 'reel'}
    ]
    
    next_slot = None
    next_day = False
    
    for s in SLOTS:
        slot_dt = est_now.replace(hour=s['hour'], minute=s['minute'], second=0, microsecond=0)
        if slot_dt > est_now:
            next_slot = s
            break
            
    if next_slot is None:
        next_slot = SLOTS[0]
        next_day = True
        
    if next_day:
        next_run_est = est_now.replace(hour=next_slot['hour'], minute=next_slot['minute'], second=0, microsecond=0) + timedelta(days=1)
    else:
        next_run_est = est_now.replace(hour=next_slot['hour'], minute=next_slot['minute'], second=0, microsecond=0)
        
    diff = next_run_est - est_now
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    time_str = next_run_est.strftime("%I:%M %p %Z").strip()
    media_str = next_slot['type'].capitalize()
    
    relative_str = ""
    if hours > 0:
        relative_str += f"{hours}h "
    relative_str += f"{minutes}m"
    
    return f"{time_str} ({media_str}) (in {relative_str})"

def report_success(filename, seo_title, description, hashtags, facebook_url, youtube_url, remaining_queue, media_type='reel'):
    from zoneinfo import ZoneInfo
    current_time = datetime.now(ZoneInfo('America/New_York')).strftime("%I:%M %p %Z")
    
    github_repo = os.environ.get('GITHUB_REPOSITORY')
    github_run_id = os.environ.get('GITHUB_RUN_ID')
    github_server_url = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
    
    github_repo_url = f"{github_server_url}/{github_repo}" if github_repo else "Local Run"
    github_run_url = f"{github_repo_url}/actions/runs/{github_run_id}" if github_run_id else "Local Run"
    
    media_label = "Photo" if media_type == 'photo' else "Video"
    fb_label = "Facebook Photo Post" if media_type == 'photo' else "Facebook Reel"
    
    hashtag_str = " ".join(hashtags) if isinstance(hashtags, list) else str(hashtags)
    
    yt_status_line = ""
    yt_url_line = ""
    if media_type == 'reel':
        yt_status = "Success" if youtube_url and not youtube_url.startswith("Error") else "Failed / Skipped"
        yt_status_line = f"📤 YouTube Upload Status: {yt_status}\n"
        yt_url_line = f"▶️ YouTube Video URL:\n{youtube_url if youtube_url else 'N/A'}\n\n"
    
    message = (
        "✅ Pipeline Run Completed\n\n"
        f"🎬 {media_label} Name:\n"
        f"{seo_title}\n\n"
        f"📤 Facebook Upload Status: Success\n"
        f"{yt_status_line}\n"
        f"🏷️ SEO Title:\n"
        f"{seo_title}\n\n"
        f"📝 Description:\n"
        f"{description}\n\n"
        f"{hashtag_str}\n\n"
        f"Original File: {filename}\n\n"
        f"🔗 {fb_label} URL:\n"
        f"{facebook_url}\n\n"
        f"{yt_url_line}"
        f"📦 GitHub Repository:\n"
        f"{github_repo_url}\n\n"
        f"📄 Workflow Run:\n"
        f"{github_run_url}"
    )
    return send_telegram_message(message)

def report_failure(filename, error_message, remaining_queue, media_type='reel'):
    from zoneinfo import ZoneInfo
    current_time = datetime.now(ZoneInfo('America/New_York')).strftime("%I:%M %p %Z")
    emoji = "🖼️" if media_type == 'photo' else "🎥"
    message = (
        "❌ <b>Upload Failed</b>\n\n"
        f"📌 <b>Post Type:</b> {media_type.capitalize()} {emoji}\n\n"
        f"📁 <b>File Name:</b> {filename}\n\n"
        f"⚠️ <b>Error:</b> {error_message}\n\n"
        f"🕒 <b>Attempt Time:</b> {current_time}\n\n"
        f"⏰ <b>Next Scheduled Upload:</b> {get_next_run_message()}"
    )
    return send_telegram_message(message)
