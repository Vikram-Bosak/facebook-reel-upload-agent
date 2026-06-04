import os
import time
import json
import tempfile
from playwright.sync_api import sync_playwright

try:
    from .logger import logger
except ImportError:
    from logger import logger

def get_fb_state():
    """Retrieves the Facebook session state from the environment variable."""
    state_json = os.environ.get('FB_STATE_JSON')
    page_id = os.environ.get('FB_PAGE_ID')
    return state_json, page_id

def upload_reel(video_path, caption, title=None):
    """
    Uploads a video to Facebook Reels using Playwright browser automation.
    Requires FB_STATE_JSON to be set in the environment.
    """
    state_json_str, page_id = get_fb_state()
    
    if not state_json_str or not page_id:
        raise Exception("Facebook configuration missing. Ensure FB_STATE_JSON and FB_PAGE_ID are set.")

    logger.info("Initializing Playwright for Facebook Reel upload...")
    
    # Write the state string to a temporary file because Playwright expects a file path
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write(state_json_str)
        temp_state_path = f.name

    try:
        with sync_playwright() as p:
            # Run headless for GitHub Actions or background processing
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            try:
                # Load the saved session state (cookies, local storage)
                context = browser.new_context(
                    storage_state=temp_state_path,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                page = context.new_page()

                # Navigate directly to the Facebook Reels composer
                upload_url = f"https://www.facebook.com/reels/create/?page_id={page_id}"
                logger.info(f"Navigating to {upload_url}")
                
                page.goto(upload_url, wait_until="domcontentloaded", timeout=60000)
                
                # Give the page a moment to render properly
                page.wait_for_timeout(5000)
                
                # Check if we were redirected to a login page (meaning session expired)
                if "/login" in page.url:
                    raise Exception("Session expired or invalid. Please generate a new FB_STATE_JSON.")

                # Step 1: Upload Video File
                logger.info("Locating file input element...")
                file_input = page.locator("input[type='file'][accept*='video']")
                file_input.wait_for(state="attached", timeout=30000)
                
                logger.info(f"Uploading file: {video_path}")
                file_input.set_input_files(video_path)
                
                # Wait for upload processing
                logger.info("Waiting for file to be processed...")
                page.wait_for_timeout(8000)
                
                # Click the 'Next' button
                logger.info("Clicking 'Next' button...")
                next_button = page.locator("div[role='button']:has-text('Next')")
                next_button.last.click()
                
                page.wait_for_timeout(3000)
                
                # Step 2: Description and Details
                logger.info("Entering caption...")
                textbox = page.locator("div[role='textbox'][contenteditable='true']")
                textbox.wait_for(state="visible", timeout=15000)
                
                textbox.click()
                textbox.type(caption, delay=10)
                
                page.wait_for_timeout(3000)
                
                # Step 3: Publish
                logger.info("Clicking 'Publish' button...")
                publish_button = page.locator("div[role='button']:has-text('Publish')")
                publish_button.last.click()
                
                # Step 4: Wait for completion
                logger.info("Waiting for publish to complete...")
                page.wait_for_timeout(15000)
                
                logger.info("Reel published successfully.")
                return f"https://www.facebook.com/{page_id}/reels/"

            except Exception as e:
                logger.error(f"Playwright Upload Error: {e}")
                raise Exception(f"Facebook Playwright Upload Failed: {str(e)}")
            finally:
                browser.close()
    finally:
        # Clean up temp file
        if os.path.exists(temp_state_path):
            os.remove(temp_state_path)
