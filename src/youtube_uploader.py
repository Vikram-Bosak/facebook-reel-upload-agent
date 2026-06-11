import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

try:
    from .logger import logger
except ImportError:
    from logger import logger

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_youtube_service():
    creds = None
    # Use an environment variable for the token JSON to support GitHub Actions
    token_json = os.environ.get('YOUTUBE_OAUTH_TOKEN_JSON')
    
    if token_json:
        try:
            creds_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        except Exception as e:
            logger.error(f"Failed to parse YOUTUBE_OAUTH_TOKEN_JSON: {e}")
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed YouTube OAuth token.")
            except Exception as e:
                logger.error(f"Failed to refresh YouTube token: {e}")
                creds = None
        
        if not creds:
            # Fallback for local testing if running interactively
            client_secret_file = os.environ.get('YOUTUBE_CLIENT_SECRETS_FILE', 'client_secrets.json')
            if os.path.exists(client_secret_file):
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info(f"New token generated. Please save this JSON as YOUTUBE_OAUTH_TOKEN_JSON: {creds.to_json()}")
            else:
                raise Exception("Missing YOUTUBE_OAUTH_TOKEN_JSON environment variable or client_secrets.json file.")

    return build('youtube', 'v3', credentials=creds)

def upload_youtube_shorts(video_path, title, description, tags=None):
    """
    Uploads a video to YouTube as a Short.
    Returns the video URL if successful, otherwise raises an exception.
    """
    try:
        youtube = get_youtube_service()
        
        # YouTube Shorts requirements: 
        # - Max 60 seconds (already validated in queue_manager)
        # - Vertical aspect ratio (already validated in queue_manager)
        # - Include #Shorts in title or description helps algorithm
        
        if tags is None:
            tags = []
            
        # Ensure #Shorts is somewhere
        if '#shorts' not in title.lower() and '#shorts' not in description.lower():
            description += "\n#Shorts"
            
        if 'shorts' not in [t.lower() for t in tags]:
            tags.append("Shorts")

        body = {
            'snippet': {
                'title': title[:100], # YouTube title limit is 100 chars
                'description': description[:5000], # Description limit is 5000
                'tags': tags[:15], # Recommend max 15 tags
                'categoryId': '24' # 24 is Entertainment
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Call the API's videos.insert method to create and upload the video.
        logger.info(f"Uploading to YouTube Shorts: {title}")
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )
        
        # Execute upload
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                logger.info(f"YouTube Upload Progress: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        if not video_id:
            raise Exception("Failed to get Video ID from YouTube API response.")
            
        video_url = f"https://youtube.com/shorts/{video_id}"
        logger.info(f"Successfully uploaded to YouTube Shorts: {video_url}")
        
        return video_url
        
    except Exception as e:
        logger.error(f"YouTube Shorts upload failed: {e}")
        raise

def upload_youtube_community_post(image_path, text):
    """
    Dummy function for YouTube Community Post.
    The official YouTube Data API v3 does not support uploading Community Posts.
    """
    logger.warning("YouTube Community Posts via official Data API v3 is not supported. Skipping.")
    return None
