import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
try:
    from .logger import logger
except ImportError:
    from logger import logger

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_path or not os.path.exists(creds_path):
        raise Exception(f"Google Drive credentials not found at {creds_path}")
        
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES)
        
    return build('drive', 'v3', credentials=creds)

def get_folder_id(service, parent_id, folder_name):
    """Finds a folder by name inside a parent folder."""
    query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        # Create it if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0]['id']

def setup_folders(service, root_folder_id):
    """Ensures Pending, Uploaded, and Failed folders exist."""
    pending_id = get_folder_id(service, root_folder_id, 'Pending')
    uploaded_id = get_folder_id(service, root_folder_id, 'Uploaded')
    failed_id = get_folder_id(service, root_folder_id, 'Failed')
    return pending_id, uploaded_id, failed_id

def get_next_video():
    """
    Finds the first MP4 video in the 'Pending' folder, downloads it to temp/,
    and returns its file path, drive file ID, and the uploaded/failed folder IDs.
    Returns None if no videos are found.
    """
    root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    if not root_folder_id:
        raise Exception("GOOGLE_DRIVE_FOLDER_ID is missing.")
        
    service = get_drive_service()
    pending_id, uploaded_id, failed_id = setup_folders(service, root_folder_id)
    
    # Get the oldest video in Pending folder
    query = f"'{pending_id}' in parents and mimeType='video/mp4' and trashed=false"
    results = service.files().list(
        q=query, 
        orderBy="createdTime asc", 
        pageSize=1, 
        fields="files(id, name)"
    ).execute()
    
    items = results.get('files', [])
    if not items:
        return None
        
    file_id = items[0]['id']
    file_name = items[0]['name']
    
    # Download the file
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file_name)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(temp_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    logger.info(f"Downloading {file_name} from Google Drive...")
    while done is False:
        status, done = downloader.next_chunk()
    
    logger.info(f"Downloaded {file_name} successfully.")
    
    return {
        'path': temp_path,
        'filename': file_name,
        'file_id': file_id,
        'pending_id': pending_id,
        'uploaded_id': uploaded_id,
        'failed_id': failed_id,
        'service': service
    }

def move_file(service, file_id, current_folder_id, new_folder_id):
    """Moves a file from one folder to another in Google Drive."""
    # Retrieve the existing parents to remove
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    
    # Move the file to the new folder
    service.files().update(
        fileId=file_id,
        addParents=new_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

def count_pending_videos():
    """Returns the number of remaining videos in the Pending folder."""
    try:
        root_folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        service = get_drive_service()
        pending_id = get_folder_id(service, root_folder_id, 'Pending')
        
        query = f"'{pending_id}' in parents and mimeType='video/mp4' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        return len(results.get('files', []))
    except Exception as e:
        logger.error(f"Failed to count pending videos: {e}")
        return 0

def get_daily_upload_count_from_drive(service, root_folder_id):
    """
    Counts the number of files in the 'Uploaded' folder in Google Drive
    created today (UTC).
    """
    from datetime import datetime, timezone
    try:
        uploaded_id = get_folder_id(service, root_folder_id, 'Uploaded')
        
        # Start of today (UTC)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        query = f"'{uploaded_id}' in parents and createdTime >= '{today_start}' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        return len(results.get('files', []))
    except Exception as e:
        logger.error(f"Failed to count daily uploads from Drive: {e}")
        return 0

def download_db(service, root_folder_id):
    """
    Looks for reels.db in the Google Drive root folder. If found, downloads it to database/reels.db.
    Returns the file ID of the database file on Google Drive, or None if not found.
    """
    try:
        # Import dynamically to avoid circular import if database imports drive_reader
        try:
            from .database import DB_PATH, DB_DIR
        except ImportError:
            from database import DB_PATH, DB_DIR

        query = f"'{root_folder_id}' in parents and name='reels.db' and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        
        if not items:
            logger.info("No reels.db database found on Google Drive. Will initialize fresh.")
            return None
            
        file_id = items[0]['id']
        os.makedirs(DB_DIR, exist_ok=True)
        
        request = service.files().get_media(fileId=file_id)
        with open(DB_PATH, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
        logger.info("Successfully downloaded reels.db from Google Drive.")
        return file_id
    except Exception as e:
        logger.error(f"Failed to download database from Google Drive: {e}")
        return None

def upload_db(service, root_folder_id, db_file_id=None):
    """
    Uploads/overwrites database/reels.db to the root folder in Google Drive.
    """
    try:
        # Import dynamically to avoid circular import
        try:
            from .database import DB_PATH
        except ImportError:
            from database import DB_PATH

        if not os.path.exists(DB_PATH):
            logger.warning("Local database reels.db does not exist. Skipping upload.")
            return None

        media = MediaFileUpload(DB_PATH, mimetype='application/x-sqlite3', resumable=True)
        
        if db_file_id:
            # Update existing file
            service.files().update(
                fileId=db_file_id,
                media_body=media
            ).execute()
            logger.info("Successfully updated existing reels.db on Google Drive.")
            return db_file_id
        else:
            # Search again to prevent duplicates in case another runner or step created it
            query = f"'{root_folder_id}' in parents and name='reels.db' and trashed=false"
            results = service.files().list(q=query, fields="files(id)").execute()
            items = results.get('files', [])
            
            if items:
                db_file_id = items[0]['id']
                service.files().update(
                    fileId=db_file_id,
                    media_body=media
                ).execute()
                logger.info("Successfully updated reels.db on Google Drive (resolved dynamic match).")
                return db_file_id
            else:
                # Create new file
                file_metadata = {
                    'name': 'reels.db',
                    'parents': [root_folder_id]
                }
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                new_id = file.get('id')
                logger.info(f"Created reels.db on Google Drive with ID: {new_id}")
                return new_id
    except Exception as e:
        logger.error(f"Failed to upload database to Google Drive: {e}")
        return db_file_id
