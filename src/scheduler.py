import os
import sys
import argparse
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import datetime

# Add src to Python path so we can run this file directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logger import logger
from database import get_daily_upload_count
from queue_manager import process_next_video
from drive_reader import get_drive_service, get_daily_upload_count_from_drive, count_pending_videos, has_already_uploaded_in_slot

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
    
    logger.info("Initializing AI Facebook Reel Automation Agent...")
    
    if not validate_env():
        logger.error("Environment validation failed. Exiting.")
        sys.exit(1)
        
    # Initialize Drive service
    service = None
    root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    try:
        service = get_drive_service()
        logger.info("Successfully connected to Google Drive API.")
    except Exception as e:
        logger.error(f"Failed to connect to Google Drive: {e}")
        sys.exit(1)

    # Check if we have pending videos
    pending_count = count_pending_videos()
    logger.info(f"Pending videos in Google Drive: {pending_count}")
    if pending_count == 0:
        logger.info("No pending videos found in Google Drive. Exiting.")
        return

    # Check daily upload limits (Max 5 per day) directly from Drive (EST timezone based)
    logger.info("Checking daily upload count from Google Drive (US Eastern Time)...")
    daily_count = get_daily_upload_count_from_drive(service, root_folder_id)
    logger.info(f"Current daily uploads today (EST): {daily_count}/5")
    
    if daily_count >= 5:
        logger.warning("Daily upload limit of 5 reached. Exiting scheduler.")
        return

    # Determine force upload status
    force_upload = args.force or os.environ.get('FORCE_UPLOAD') == 'true'

    if force_upload:
        logger.info("Force upload enabled. Bypassing US time slot check.")
    else:
        # Time slot logic (US Eastern Time)
        est_now = datetime.now(ZoneInfo('America/New_York'))
        current_hour = est_now.hour
        logger.info(f"Current time in US Eastern Time: {est_now.strftime('%Y-%m-%d %I:%M %p %Z')}")

        SCHEDULED_HOURS = {0, 8, 12, 16, 20} # midnight, 8am, noon, 4pm, 8pm EST
        
        if current_hour not in SCHEDULED_HOURS:
            logger.info(f"Current hour {current_hour} is not a scheduled US time slot. Skipping upload.")
            return

        # Check if an upload has already occurred in the current slot
        if has_already_uploaded_in_slot(service, root_folder_id, est_now):
            logger.info(f"Already uploaded a video during this slot hour ({current_hour} EST). Skipping.")
            return

        logger.info(f"Time slot match found ({current_hour} EST) and limit check passed.")

    # Process the next video in the queue
    process_next_video()

if __name__ == "__main__":
    main()
