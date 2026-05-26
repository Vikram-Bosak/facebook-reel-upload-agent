# AI Facebook Reel Automation Agent

A fully automated cloud-based system designed to upload short videos from Google Drive directly to Facebook Reels using GitHub Actions.

This system runs automatically 24/7, fetching videos, generating AI SEO titles and descriptions, uploading them, and sending success/failure reports via Telegram.

## Features

- **Google Drive Integration**: Automatically scans a specific folder for new videos.
- **AI SEO Optimization**: Uses OpenAI to generate viral titles, descriptions, and hashtags based on the video filename.
- **Facebook Graph API**: Uploads videos directly to a Facebook Page as Reels.
- **Telegram Reporting**: Sends instant notifications on upload success or failure.
- **Duplicate Prevention & Database Sync**: Tracks uploaded files using SQLite. To support ephemeral runners in GitHub Actions, the local database (`reels.db`) is automatically synced to the root of your Google Drive folder before and after each run.
- **GitHub Actions**: Fully automated runtime scheduling (every 4 hours).

## Setup Instructions

### 1. Prerequisites

You will need accounts/keys for the following services:
- **Facebook Page**: To upload the Reels.
- **Facebook Developer App**: To get the Graph API Access Token.
- **Google Cloud Console**: To create a Service Account for Google Drive access.
- **Telegram Bot**: To send notifications.
- **OpenAI API Key**: To generate SEO content.

### 2. Environment Variables & GitHub Secrets

Create a copy of `.env.example` as `.env` for local testing.
For GitHub Actions, add these exact keys as **Repository Secrets** in your GitHub repository:

| Variable | Description |
|---|---|
| `FB_ACCESS_TOKEN` | Facebook Page Access Token (Needs `pages_manage_posts`, `pages_read_engagement`). |
| `FB_PAGE_ID` | Your Facebook Page ID. |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather. |
| `TELEGRAM_CHAT_ID` | Your Chat ID (where the bot will send messages). |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The entire JSON string of your Google Service Account key (For GitHub Actions). |
| `GOOGLE_DRIVE_FOLDER_ID` | The ID of the parent folder in Google Drive (from the URL). |
| `OPENAI_API_KEY` | Your OpenAI API key for GPT-3.5/4. |

### 3. Google Drive Setup

1. Create a main folder in Google Drive (e.g., `Facebook-Reels`) and get its ID from the URL. This is your `GOOGLE_DRIVE_FOLDER_ID`.
2. Share this folder with the email address of your Google Service Account (e.g., `your-service-account@your-project.iam.gserviceaccount.com`), giving it **Editor** access.
3. The script will automatically create `Pending`, `Uploaded`, and `Failed` subfolders inside this main folder.
4. Place your `.mp4` videos in the `Pending` folder.

### 4. Running Locally

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Make sure FFmpeg is installed on your system.
5. Set your variables in `.env`. For local runs, set `GOOGLE_APPLICATION_CREDENTIALS` to the path of your downloaded `service-account.json` file.
6. Run the script: `python src/scheduler.py`

### 5. Running via GitHub Actions

Once you push this code to GitHub and set up your Repository Secrets, the workflow defined in `.github/workflows/upload.yml` will run automatically every 4 hours. You can also trigger it manually from the "Actions" tab.

### 6. Logging & Monitoring

The agent logs its activity to both the standard console (stdout) and to a local log file:
- Log location: `logs/agent.log`
- Each log statement contains timestamps and log levels (`INFO`, `WARNING`, `ERROR`) to trace agent operations and API interaction success or failure.

