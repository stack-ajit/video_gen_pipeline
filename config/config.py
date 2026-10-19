from pathlib import Path
import os
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables (.env or env)
env_file = BASE_DIR / ".env"
if not env_file.exists():
    env_file = BASE_DIR / "env"
load_dotenv(dotenv_path=env_file)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# Directory Paths
OUTPUT_DIR = BASE_DIR / "output"
VIDEOS_DIR = OUTPUT_DIR / "videos"
FINAL_DIR = VIDEOS_DIR  # Alias for backward compatibility
THUMBNAILS_DIR = OUTPUT_DIR / "thumbnails"
LATEST_DIR = OUTPUT_DIR / "latest"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
TEMP_DIR = OUTPUT_DIR / "temp"
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
FONTS_DIR = ASSETS_DIR / "fonts"

# Video Specifications (Standard Vertical 9:16 Shorts / Reels)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Audio / TTS Defaults
DEFAULT_VOICE = "en-US-AvaMultilingualNeural"  # Expressive, natural conversational female voice
FALLBACK_VOICE = "en-US-EmmaMultilingualNeural"
VOICE_RATE = "+3%"  # Crisp, engaging short-form pacing
BGM_VOLUME = 0.22  # Clear, audible background music volume ducked relative to narration
VOICE_VOLUME = 1.0

# Subtitle Styling (High-Retention Creator Center-Aligned Style)
SUBTITLE_FONT = "Arial Black"
SUBTITLE_FONT_SIZE = 64
SUBTITLE_PRIMARY_COLOR = "&H0000F5FF"  # High-visibility vibrant yellow/gold
SUBTITLE_OUTLINE_COLOR = "&H00000000"  # Solid black outline
SUBTITLE_OUTLINE_WIDTH = 4.5
SUBTITLE_SHADOW_DEPTH = 2.0
SUBTITLE_ALIGNMENT = 2  # Centered horizontally
SUBTITLE_MARGIN_V = 720  # Positioned at eye-level sweet spot, safe from Shorts/Reels UI
SUBTITLE_MARGIN_H = 80   # Safe margins away from side engagement icons
FONT_NAME = SUBTITLE_FONT
FONT_SIZE = SUBTITLE_FONT_SIZE

# FFmpeg Binary Resolver (Uses system ffmpeg or bundled imageio_ffmpeg)
def get_ffmpeg_binary() -> str:
    import shutil
    bin_path = shutil.which("ffmpeg")
    if bin_path:
        return bin_path
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

FFMPEG_BINARY = get_ffmpeg_binary()

# YouTube Settings
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", str(BASE_DIR / "client_secret.json"))

# Ensure runtime directories exist
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
LATEST_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)
