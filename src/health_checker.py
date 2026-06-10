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

def check_facebook_token(access_token, page_id):
    """
    Verifies if the Facebook access token is valid and has access to the page.
    """
    if not access_token or not page_id:
        return False, "Facebook credentials (access token or page ID) are missing from configuration."
        
    url = f"https://graph.facebook.com/v19.0/me?access_token={access_token}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            if str(user_data.get('id')) == str(page_id):
                return True, f"Facebook API connection successful. Verified access via Page Token for: {user_data.get('name')} ({page_id})"
            
            accounts_url = f"https://graph.facebook.com/v19.0/me/accounts?limit=100&access_token={access_token}"
            acc_resp = requests.get(accounts_url, timeout=10)
            if acc_resp.status_code == 200:
                pages = acc_resp.json().get('data', [])
                for page in pages:
                    if str(page.get('id')) == str(page_id):
                        return True, f"Facebook API connection successful. Verified access to page via User Token: {page.get('name')} ({page_id})"
                return False, f"Facebook API connection successful, but target Page ID {page_id} was not found in user accounts."
            else:
                return False, f"Facebook API reachable, but failed to query page accounts: {acc_resp.text}"
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get('error', {}).get('message', 'Unknown error')
                err_code = err_data.get('error', {}).get('code', 'unknown')
                return False, f"Facebook token validation failed: {err_msg} (code: {err_code})"
            except Exception:
                return False, f"Facebook token validation failed with status {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Failed to connect to Facebook API: {e}"

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

def run_all_health_checks(access_token, page_id):
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
    ok, msg = check_facebook_token(access_token, page_id)
    results["Facebook"] = {"ok": ok, "message": msg}
    if not ok:
        is_healthy = False
        logger.error(f"Health Check Failed: {msg}")
    else:
        logger.info(f"Health Check Passed: {msg}")
        
    return is_healthy, results
