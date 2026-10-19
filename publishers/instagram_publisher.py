import os
import logging
from pathlib import Path
from typing import Optional

from config.config import BASE_DIR, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD

logger = logging.getLogger(__name__)

SESSION_FILE = BASE_DIR / "instagram_session.json"

class InstagramPublisher:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or INSTAGRAM_USERNAME
        self.password = password or INSTAGRAM_PASSWORD
        self.client = None

    def _get_client(self):
        """Initializes and authenticates instagrapi Client with session reuse."""
        from instagrapi import Client

        if not self.username or not self.password:
            raise ValueError(
                "Instagram credentials not set. Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in your .env file."
            )

        cl = Client()
        cl.delay_range = [2, 5]  # Human-like delay between API calls

        # 1. Try to load cached session to avoid frequent login verification challenges
        if SESSION_FILE.exists():
            try:
                cl.load_settings(str(SESSION_FILE))
                cl.login(self.username, self.password)
                logger.info("Logged in to Instagram using cached session.")
                self.client = cl
                return cl
            except Exception as e:
                logger.warning(f"Cached Instagram session expired or failed ({e}). Re-logging in...")

        # 2. Fresh login
        logger.info(f"Logging in to Instagram as @{self.username}...")
        cl.login(self.username, self.password)
        cl.dump_settings(str(SESSION_FILE))
        logger.info(f"Logged in successfully. Session saved to {SESSION_FILE.name}")
        self.client = cl
        return cl

    def upload_reel(self, video_path: Path, caption: str) -> Optional[str]:
        """
        Uploads a vertical 9:16 video to Instagram as a Reel.
        Returns the Reel URL.
        """
        logger.info(f"Uploading Reel to Instagram: {video_path.name}...")
        cl = self._get_client()

        # Format caption with #Reels
        if "#Reels" not in caption:
            caption = f"{caption}\n\n#Reels #ExplorePage"

        try:
            media = cl.clip_upload(
                str(video_path),
                caption=caption
            )
            reel_url = f"https://www.instagram.com/reel/{media.code}/"
            logger.info(f"Reel uploaded successfully! URL: {reel_url}")
            return reel_url
        except Exception as e:
            logger.error(f"Instagram Reel upload failed: {e}")
            raise
        finally:
            # Move instagrapi's auto-generated thumbnail to thumbnails directory
            thumb_candidate = Path(f"{video_path}.jpg")
            if thumb_candidate.exists():
                try:
                    from config.config import THUMBNAILS_DIR
                    clean_thumb = THUMBNAILS_DIR / f"{video_path.stem}.jpg"
                    thumb_candidate.replace(clean_thumb)
                    logger.debug(f"Moved thumbnail to {clean_thumb}")
                except Exception:
                    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("InstagramPublisher module loaded.")
