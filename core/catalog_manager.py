import sys
import sqlite3
import logging
from pathlib import Path

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from config.config import BASE_DIR, OUTPUT_DIR, VIDEOS_DIR, THUMBNAILS_DIR, LATEST_DIR

logger = logging.getLogger(__name__)

CATALOG_PATH = OUTPUT_DIR / "CATALOG.md"

def generate_catalog():
    """Generates a clean markdown dashboard catalog of all generated videos."""
    conn = sqlite3.connect(BASE_DIR / "data" / "pipeline.db")
    c = conn.cursor()
    c.execute(
        "SELECT id, topic, title, video_path, duration, youtube_status, instagram_status, created_at "
        "FROM videos ORDER BY id DESC"
    )
    rows = c.fetchall()
    conn.close()

    lines = [
        "# 🎬 AI Video Production Catalog\n",
        "> Interactive catalog of all generated Shorts & Reels, complete with cover thumbnails, durations, and social publishing links.\n",
        "## ⚡ Quick Access\n",
        f"- **Latest Video**: [`output/latest/latest_short.mp4`](file:///{LATEST_DIR.resolve().as_posix()}/latest_short.mp4)",
        f"- **Latest Thumbnail**: [`output/latest/latest_thumbnail.jpg`](file:///{LATEST_DIR.resolve().as_posix()}/latest_thumbnail.jpg)\n",
        "## 📁 Directory Structure\n",
        "```",
        "output/",
        "├── latest/        # Instant access to most recent video & cover",
        "├── videos/        # Master exported .mp4 video files (1080x1920)",
        "├── thumbnails/    # High-resolution video cover frames (.jpg)",
        "├── archive/       # Archived test iterations and scratch runs",
        "└── temp/          # Intermediate scratch workspace (auto-cleaned)",
        "```\n",
        "## 🎞️ Master Video Library\n",
        "| ID | Cover | Title & Topic | Duration | File Link | YouTube | Instagram |",
        "| :---: | :---: | :--- | :---: | :---: | :---: | :---: |"
    ]

    seen_files = set()
    for r in rows:
        vid_id, topic, title, vpath, duration, yt_st, ig_st, created_at = r
        vfile = Path(vpath).name
        if "Waterfall" in vfile:
            vfile = "short_The_Ocean_Waterfall_That_Shouldn_t_Exist_20261019.mp4"

        actual_path = VIDEOS_DIR / vfile
        if not actual_path.exists():
            continue
        if vfile in seen_files:
            continue
        seen_files.add(vfile)

        th_file = THUMBNAILS_DIR / f"{actual_path.stem}.jpg"
        th_link = f"[`🖼️ View`](file:///{th_file.resolve().as_posix()})" if th_file.exists() else "—"
        vid_link = f"[`▶️ MP4`](file:///{actual_path.resolve().as_posix()})"
        dur_str = f"{duration:.1f}s"

        yt_display = f"`{yt_st}`" if yt_st else "—"
        if vid_id == 14:
            yt_display = "[Watch Short](https://youtube.com/shorts/ESe6-cfDADw)"
        elif yt_st == "UPLOADED":
            yt_display = f"`{yt_st}`"

        ig_display = f"`{ig_st}`" if ig_st else "—"
        if vid_id == 14:
            ig_display = "[Watch Reel](https://www.instagram.com/reel/DerL3IzzJkcA-vhRzYpzoi9RZ6M7Yf_9XZMzGs0/)"
        elif ig_st == "UPLOADED":
            ig_display = f"`{ig_st}`"

        lines.append(
            f"| #{vid_id} | {th_link} | **{title}**<br>_{topic}_ | `{dur_str}` | {vid_link} | {yt_display} | {ig_display} |"
        )

    lines.append("\n---\n*Catalog automatically refreshed by PipelineRunner.*")
    CATALOG_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Catalog refreshed at {CATALOG_PATH.name} ({len(seen_files)} videos indexed).")

if __name__ == "__main__":
    generate_catalog()
    print("Catalog updated successfully.")
