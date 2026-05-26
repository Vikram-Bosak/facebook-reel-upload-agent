import os
import hashlib
import ffmpeg
import time
try:
    from .database import is_duplicate, insert_reel, update_reel_metadata, mark_reel_uploaded, mark_reel_failed
    from .seo_generator import generate_seo_metadata, format_caption
    from .facebook_uploader import upload_reel
    from .telegram_reporter import report_success, report_failure
    from .drive_reader import get_next_video, move_file, count_pending_videos
    from .logger import logger
except ImportError:
    from database import is_duplicate, insert_reel, update_reel_metadata, mark_reel_uploaded, mark_reel_failed
    from seo_generator import generate_seo_metadata, format_caption
    from facebook_uploader import upload_reel
    from telegram_reporter import report_success, report_failure
    from drive_reader import get_next_video, move_file, count_pending_videos
    from logger import logger

def get_file_hash(filepath):
    """Calculates MD5 hash of the file to prevent exact duplicates."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def validate_video(filepath):
    """
    Validates if video meets Facebook Reels constraints:
    - MP4 format
    - < 60 seconds
    - < 100 MB
    - Vertical orientation (width < height, or 9:16 approx)
    """
    try:
        # Check file size (100 MB max)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > 100:
            return False, "File exceeds 100MB limit"
            
        probe = ffmpeg.probe(filepath)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if not video_stream:
            return False, "No video stream found"
            
        # Check duration
        duration = float(video_stream.get('duration', 0))
        if duration > 60.5:
            return False, f"Video too long: {duration} seconds (Max 60s)"
            
        # Check orientation
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        if width > height:
            return False, "Video is horizontal, must be vertical (9:16)"
            
        return True, "Valid"
    except FileNotFoundError:
        return False, "FFmpeg/FFprobe was not found on your system PATH. Please install FFmpeg and make sure it is added to the PATH."
    except ffmpeg.Error as e:
        return False, f"FFmpeg error parsing video: {e}"
    except Exception as e:
        return False, f"Error validating video: {e}"

def process_next_video():
    """Main workflow to process one video from the queue."""
    video_info = get_next_video()
    if not video_info:
        logger.info("No pending videos found in Google Drive.")
        return False
        
    filepath = video_info['path']
    filename = video_info['filename']
    file_id = video_info['file_id']
    service = video_info['service']
    
    remaining_queue = count_pending_videos() - 1
    
    logger.info(f"Processing video: {filename}")
    
    try:
        # Duplicate Check
        file_hash = get_file_hash(filepath)
        if is_duplicate(filename, file_hash):
            raise Exception("Duplicate file detected based on filename or hash.")
            
        # Video Validation
        is_valid, msg = validate_video(filepath)
        if not is_valid:
            raise Exception(f"Video validation failed: {msg}")
            
        # Database tracking (prevent parallel processing)
        if not insert_reel(filename, file_hash):
            raise Exception("Failed to lock file in database. Might be processing already.")
            
        # AI SEO Generation
        logger.info("Generating SEO metadata via OpenAI...")
        seo = generate_seo_metadata(filename)
        caption = format_caption(seo)
        update_reel_metadata(filename, seo['title'], seo['description'], seo['hashtags'])
        
        # Facebook Upload with Retries
        logger.info("Uploading to Facebook Reels...")
        max_retries = 3
        retry_delays = [60, 300, 900] # 1 min, 5 min, 15 min
        fb_url = None
        
        for attempt in range(max_retries):
            try:
                fb_url = upload_reel(filepath, caption)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.warning(f"Upload attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Upload failed after {max_retries} attempts: {e}")
                    
        # Success Handling
        mark_reel_uploaded(filename, fb_url)
        report_success(filename, seo['title'], fb_url, remaining_queue)
        
        # Move file in Drive
        move_file(service, file_id, video_info['pending_id'], video_info['uploaded_id'])
        logger.info("Process completed successfully. Video uploaded and moved to 'Uploaded' folder.")
        
    except Exception as e:
        # Failure Handling
        logger.error(f"Error processing video: {e}")
        mark_reel_failed(filename)
        report_failure(filename, str(e), remaining_queue)
        
        # Move file in Drive to Failed
        try:
            move_file(service, file_id, video_info['pending_id'], video_info['failed_id'])
            logger.info("Video moved to 'Failed' folder in Google Drive.")
        except Exception as move_err:
            logger.error(f"Also failed to move file in Drive: {move_err}")
            
    finally:
        # Cleanup temp file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Temporary file cleaned up: {filepath}")
            except Exception as cleanup_err:
                logger.error(f"Failed to cleanup temporary file {filepath}: {cleanup_err}")
            
    return True
