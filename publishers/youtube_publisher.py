import os
import logging
from pathlib import Path
from typing import List, Optional
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config.config import BASE_DIR, YOUTUBE_CLIENT_SECRET_FILE

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = BASE_DIR / "youtube_token.json"

class YouTubePublisher:
    def __init__(self, client_secret_file: Optional[str] = None):
        self.client_secret_file = client_secret_file or YOUTUBE_CLIENT_SECRET_FILE

    def get_authenticated_service(self):
        """Authenticates with YouTube Data API v3 using OAuth 2.0."""
        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not Path(self.client_secret_file).exists():
                    raise FileNotFoundError(
                        f"YouTube client secrets file not found at: {self.client_secret_file}. "
                        "Download your client_secret.json from Google Cloud Console to enable YouTube uploads."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

        return build("youtube", "v3", credentials=creds)

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str],
        privacy_status: str = "public"
    ) -> Optional[str]:
        """
        Uploads a vertical video as a YouTube Short.
        Returns the uploaded video ID.
        """
        # Ensure #Shorts tag is in title and description
        if "#Shorts" not in title:
            title = f"{title} #Shorts"
        if "#Shorts" not in description:
            description = f"{description}\n\n#Shorts #Viral"

        logger.info(f"Uploading '{title}' to YouTube ({privacy_status})...")
        try:
            youtube = self.get_authenticated_service()
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags,
                    "categoryId": "28"  # Science & Technology
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%")

            video_id = response.get("id")
            logger.info(f"Video uploaded successfully! URL: https://youtube.com/shorts/{video_id}")
            return video_id
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("YouTubePublisher module initialized.")
