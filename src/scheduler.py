import os
import sys
import argparse
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta

# Add src to Python path so we can run this file directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logger import logger
from database import get_daily_upload_count
from queue_manager import process_next_video
from drive_reader import get_drive_service, get_daily_upload_count_from_drive, count_pending_videos, has_uploaded_since_datetime
from health_checker import run_all_health_checks
from watchdog import update_heartbeat

def get_latest_scheduled_slot_time(est_now):
    """
    Computes the start datetime of the latest scheduled slot that should have run.
    Scheduled slots: 00:00, 08:00, 12:00, 16:00, 20:00 EST.
    """
    scheduled_hours = sorted([0, 8, 12, 16, 20])
    slot_hour = None
    for h in reversed(scheduled_hours):
        if est_now.hour >= h:
            slot_hour = h
            break
            
    if slot_hour is not None:
        return est_now.replace(hour=slot_hour, minute=0, second=0, microsecond=0)
    else:
        # Fallback to the 8:00 PM slot of the previous day
        prev_day = est_now - timedelta(days=1)
        return prev_day.replace(hour=20, minute=0, second=0, microsecond=0)

def validate_env():
    """Validates that all required environment variables are present and correct."""
    required = {
        'FB_ACCESS_TOKEN': "Facebook Page Access Token is required to post Reels.",
        'FB_PAGE_ID': "Facebook Page ID is required to target the correct page.",
        'GOOGLE_DRIVE_FOLDER_ID': "Google Drive Folder ID is required to read/write videos and database.",
    }
    
    # Check credentials path
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable is missing.")
        return False
        
    if not os.path.exists(creds_path):
        logger.error(f"Google Drive credentials file not found at: {creds_path}")
        return False
        
    missing = []
    for var, desc in required.items():
        if not os.environ.get(var):
            logger.error(f"Missing environment variable: {var} - {desc}")
            missing.append(var)
            
    if missing:
        return False
        
    return True

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI Facebook Reel Automation Agent Scheduler")
    parser.add_argument('--force', action='store_true', help='Force upload bypassing time slot locks')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    update_heartbeat("starting")
    
    logger.info("Initializing AI Facebook Reel Automation Agent...")
    
    if not validate_env():
        logger.error("Environment validation failed. Exiting.")
        update_heartbeat("failed_env_validation")
        sys.exit(1)
        
    # Initialize Drive service
    service = None
    root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    try:
        service = get_drive_service()
        logger.info("Successfully connected to Google Drive API.")
    except Exception as e:
        logger.error(f"Failed to connect to Google Drive: {e}")
        update_heartbeat("unhealthy", {"error": f"Failed to connect to Google Drive: {e}"})
        sys.exit(1)

    # Run active health checks before checking files or scheduling
    access_token = os.environ.get('FB_ACCESS_TOKEN')
    page_id = os.environ.get('FB_PAGE_ID')
    is_healthy, health_results = run_all_health_checks(access_token, page_id)
    if not is_healthy:
        logger.error(f"System health check failed. Aborting cycle. Results: {health_results}")
        update_heartbeat("unhealthy", health_results)
        try:
            from telegram_reporter import report_failure
            report_failure("System Health Check", f"Critical Health Check Failure:\n{health_results}", 0)
        except Exception as tel_err:
            logger.error(f"Failed to send health failure notification: {tel_err}")
        return

    # Check if we have pending videos
    pending_count = count_pending_videos()
    logger.info(f"Pending videos in Google Drive: {pending_count}")
    if pending_count == 0:
        logger.info("No pending videos found in Google Drive. Exiting.")
        update_heartbeat("idle", {"message": "No pending videos in Google Drive."})
        return

    # Check daily upload limits (Max 5 per day) directly from Drive (EST timezone based)
    logger.info("Checking daily upload count from Google Drive (US Eastern Time)...")
    daily_count = get_daily_upload_count_from_drive(service, root_folder_id)
    logger.info(f"Current daily uploads today (EST): {daily_count}/5")
    
    if daily_count >= 5:
        logger.warning("Daily upload limit of 5 reached. Exiting scheduler.")
        update_heartbeat("idle", {"message": "Daily upload limit of 5 reached."})
        return

    # Determine force upload status
    force_upload = args.force or os.environ.get('FORCE_UPLOAD') == 'true'

    if force_upload:
        logger.info("Force upload enabled. Bypassing US time slot check.")
    else:
        # Time slot logic (US Eastern Time)
        est_now = datetime.now(ZoneInfo('America/New_York'))
        logger.info(f"Current time in US Eastern Time: {est_now.strftime('%Y-%m-%d %I:%M %p %Z')}")

        latest_slot_dt = get_latest_scheduled_slot_time(est_now)
        latest_slot_dt_utc = latest_slot_dt.astimezone(timezone.utc)
        
        # Check if an upload has already occurred in/since the latest slot
        if has_uploaded_since_datetime(service, root_folder_id, latest_slot_dt_utc):
            logger.info(f"Already uploaded a video during or after the latest slot ({latest_slot_dt.strftime('%I:%M %p %Z')}). Skipping.")
            update_heartbeat("idle", {"message": f"Already uploaded in slot {latest_slot_dt.strftime('%I:%M %p %Z')}"})
            return

        logger.info(f"No upload detected for latest slot ({latest_slot_dt.strftime('%I:%M %p %Z')}). Missed slot/catch-up triggered!")

    # Process the next video in the queue with safety wrapping
    update_heartbeat("processing")
    try:
        success = process_next_video()
        if success:
            update_heartbeat("healthy", {"message": "Cycle completed successfully"})
        else:
            update_heartbeat("healthy", {"message": "Checked queue, no upload was performed"})
    except Exception as e:
        logger.error(f"Critical error in queue manager: {e}", exc_info=True)
        update_heartbeat("error", {"error": str(e)})
        try:
            from telegram_reporter import report_failure
            report_failure("Queue Manager Process", f"Critical Queue Manager failure: {e}", pending_count)
        except Exception as tel_err:
            logger.error(f"Failed to report crash to Telegram: {tel_err}")


if __name__ == "__main__":
    main()
