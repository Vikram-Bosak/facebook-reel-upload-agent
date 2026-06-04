import os
from playwright.sync_api import sync_playwright

def generate_state():
    print("Starting Playwright to generate Facebook session state...")
    print("A browser window will open. Please log into your Facebook account.")
    print("If you manage a Page via Profile Switch, switch to the Page profile now.")
    print("If you use Meta Business Suite, just logging in is enough.")
    
    with sync_playwright() as p:
        # We launch chromium in headed mode so you can see the UI and log in
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Go to Facebook
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
        
        # Wait for user input to continue
        input("\n--- PRESS ENTER HERE AFTER YOU HAVE LOGGED IN AND SWITCHED TO YOUR PAGE ---")
        
        # Save the authentication state (cookies, localStorage, etc.)
        state_file = "state.json"
        context.storage_state(path=state_file)
        
        print(f"\nSuccess! Authentication state saved to {state_file}")
        print("Please copy the contents of this file and save it in your GitHub Secrets as FB_STATE_JSON.")
        
        browser.close()

if __name__ == "__main__":
    generate_state()
