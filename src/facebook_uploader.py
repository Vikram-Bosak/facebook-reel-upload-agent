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
            
            # Load the saved session state (cookies, local storage)
            context = browser.new_context(
                storage_state=temp_state_path,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Use stealth mode via context (or generic bypass techniques if stealth library not working flawlessly)
            page = context.new_page()

            # Navigate directly to the Facebook Reels composer
            # Alternative is Meta Business Suite, but basic Facebook Profile reels creator is often simpler
            upload_url = f"https://www.facebook.com/reels/create/?page_id={page_id}"
            logger.info(f"Navigating to {upload_url}")
            
            page.goto(upload_url, wait_until="networkidle")
            
            # Give the page a moment to render properly
            page.wait_for_timeout(3000)
            
            # Check if we were redirected to a login page (meaning session expired)
            if "/login" in page.url:
                raise Exception("Session expired or invalid. Please generate a new FB_STATE_JSON.")

            # Step 1: Upload Video File
            logger.info("Locating file input element...")
            # Wait for file input element to be available in the DOM
            file_input = page.locator("input[type='file'][accept*='video']")
            file_input.wait_for(state="attached", timeout=15000)
            
            logger.info(f"Uploading file: {video_path}")
            file_input.set_input_files(video_path)
            
            # Wait for upload processing (this can take a while depending on file size)
            logger.info("Waiting for file to be processed...")
            page.wait_for_timeout(5000) # Give it an initial 5 seconds
            
            # Click the 'Next' button
            logger.info("Clicking 'Next' button...")
            next_button = page.locator("div[role='button']:has-text('Next')")
            # There might be multiple next buttons or it might take a second to become clickable
            next_button.last.click()
            
            page.wait_for_timeout(2000)
            
            # Step 2: Description and Details
            logger.info("Entering caption...")
            
            # Facebook uses a contenteditable div for the description
            textbox = page.locator("div[role='textbox'][contenteditable='true']")
            textbox.wait_for(state="visible", timeout=10000)
            
            # Clear if needed and type caption
            textbox.click()
            textbox.type(caption, delay=10) # human-like typing
            
            page.wait_for_timeout(2000)
            
            # Step 3: Publish
            logger.info("Clicking 'Publish' button...")
            publish_button = page.locator("div[role='button']:has-text('Publish')")
            publish_button.last.click()
            
            # Step 4: Wait for completion
            logger.info("Waiting for publish to complete...")
            # We wait until we are redirected back to the Reels feed or profile
            # Usually after publish, a dialog appears or URL changes. We'll wait a bit.
            page.wait_for_timeout(10000)
            
            # Assuming success if no crash. Playwright doesn't easily return the URL immediately
            # like the API did. We will return a generic profile reels link.
            logger.info("Reel published successfully.")
            return f"https://www.facebook.com/{page_id}/reels/"

    except Exception as e:
        logger.error(f"Playwright Upload Error: {e}")
        # Capture screenshot for debugging if possible
        try:
            if 'page' in locals():
                page.screenshot(path="error_screenshot.png")
                logger.info("Saved error screenshot to error_screenshot.png")
        except:
            pass
        raise Exception(f"Facebook Playwright Upload Failed: {str(e)}")
    finally:
        if 'browser' in locals():
            browser.close()
        # Clean up temp file
        if os.path.exists(temp_state_path):
            os.remove(temp_state_path)
