import os
import sys
from dotenv import load_dotenv

# Add src to Python path so we can run this file directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logger import logger
from database import get_daily_upload_count
from queue_manager import process_next_video
from drive_reader import get_drive_service, get_daily_upload_count_from_drive

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

    # Check daily upload limits (Max 5 per day) directly from Drive
    logger.info("Checking daily upload count from Google Drive...")
    daily_count = get_daily_upload_count_from_drive(service, root_folder_id)
    logger.info(f"Current daily uploads today: {daily_count}/5")
    
    if daily_count >= 5:
        logger.warning("Daily upload limit of 5 reached. Exiting scheduler.")
        return
        
    # Process the next video in the queue
    process_next_video()
    
if __name__ == "__main__":
    main()
