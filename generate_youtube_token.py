import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube Data API v3 upload scope
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def generate_token():
    print("=========================================")
    print("YouTube OAuth Token Generator")
    print("=========================================")
    print("Ensure you have downloaded your 'client_secret.json' from Google Cloud Console.")
    print("Place it in the same directory as this script.\n")
    
    client_secrets_file = "client_secret.json"
    
    if not os.path.exists(client_secrets_file):
        print(f"ERROR: '{client_secrets_file}' not found!")
        print("Please download it from Google Cloud Console (APIs & Services -> Credentials) and rename it to 'client_secret.json'.")
        return

    try:
        # Run the local server flow
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Output the credentials to JSON
        creds_json = creds.to_json()
        
        with open("youtube_token.json", "w") as f:
            f.write(creds_json)
            
        print("\n✅ SUCCESS! Token generated successfully.")
        print("=========================================")
        print("Below is your token JSON. Copy everything between the curly braces {} (including the braces):")
        print("=========================================\n")
        print(creds_json)
        print("\n=========================================")
        print("Next Steps:")
        print("1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions")
        print("2. Create a new Repository Secret named: YOUTUBE_OAUTH_TOKEN_JSON")
        print("3. Paste the entire JSON output above as the value.")
        print("=========================================")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to generate token: {e}")

if __name__ == "__main__":
    generate_token()
