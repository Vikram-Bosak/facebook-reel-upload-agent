import os
import socket
import requests
try:
    from .logger import logger
except ImportError:
    from logger import logger

def check_internet(timeout=5):
    """
    Checks if there is an active internet connection.
    """
    try:
        # Try to resolve Google DNS and connect
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True, "Internet connection is active."
    except Exception as e:
        return False, f"Internet connection check failed: {e}"

def check_facebook_state(fb_state, page_id):
    """
    Verifies if the Facebook state JSON is present and valid JSON.
    """
    import json
    
    if not fb_state or not page_id:
        return False, "Facebook credentials (FB_STATE_JSON or FB_PAGE_ID) are missing from configuration."
        
    try:
        # Just verify it's valid JSON. We can't easily check if the session is still active
        # without launching Playwright, which is too heavy for a simple health check.
        state_data = json.loads(fb_state)
        if 'cookies' in state_data:
            return True, f"Facebook State JSON is valid. Ready for page: {page_id}"
        else:
            return False, "Facebook State JSON is missing 'cookies' array."
    except json.JSONDecodeError:
        return False, "FB_STATE_JSON is not a valid JSON string. Please regenerate it."
    except Exception as e:
        return False, f"Failed to validate Facebook State JSON: {e}"

def check_google_drive():
    """
    Checks if Google Drive service can connect and access the root folder.
    """
    try:
        try:
            from .drive_reader import get_drive_service
        except ImportError:
            from drive_reader import get_drive_service
            
        service = get_drive_service()
        root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        if not root_folder_id:
            return False, "GOOGLE_DRIVE_FOLDER_ID is missing from configuration."
            
        # Try to retrieve metadata for the root folder to verify connection/access
        folder = service.files().get(fileId=root_folder_id, fields="id, name").execute()
        return True, f"Google Drive API connection successful. Connected to folder: {folder.get('name')}"
    except Exception as e:
        return False, f"Google Drive connection check failed: {e}"

def run_all_health_checks(fb_state, page_id):
    """
    Runs all health checks and returns (is_healthy, status_results).
    """
    logger.info("Running system health checks...")
    results = {}
    is_healthy = True
    
    # Run Internet check
    ok, msg = check_internet()
    results["Internet"] = {"ok": ok, "message": msg}
    if not ok:
        is_healthy = False
        logger.error(f"Health Check Failed: {msg}")
    else:
        logger.info(f"Health Check Passed: {msg}")
        
    # Run Google Drive check
    ok, msg = check_google_drive()
    results["Google Drive"] = {"ok": ok, "message": msg}
    if not ok:
        is_healthy = False
        logger.error(f"Health Check Failed: {msg}")
    else:
        logger.info(f"Health Check Passed: {msg}")
        
    # Run Facebook check
    ok, msg = check_facebook_state(fb_state, page_id)
    results["Facebook"] = {"ok": ok, "message": msg}
    if not ok:
        is_healthy = False
        logger.error(f"Health Check Failed: {msg}")
    else:
        logger.info(f"Health Check Passed: {msg}")
        
    return is_healthy, results
