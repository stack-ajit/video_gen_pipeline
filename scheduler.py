import logging
import time
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from apscheduler.schedulers.blocking import BlockingScheduler

from main import ContentGenerationPipeline
from config.config import BASE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Scheduler")

TOPICS_FILE = BASE_DIR / "topics.txt"

# Default topics pool if topics.txt is empty
DEFAULT_TOPIC_POOL = [
    "What Would Happen If The Earth Stopped Spinning for 5 Seconds?",
    "The Dark Truth About Quantum Computing",
    "How The James Webb Space Telescope Broke Physics",
    "Why The Mariana Trench is More Dangerous Than Outer Space",
    "The 3 Most Powerful Artificial Intelligence Models in 2026",
    "Can We Survive If The Sun Disappeared Tomorrow?"
]

def get_next_topic() -> str:
    """Pulls the next topic from topics.txt or falls back to curated pool."""
    if TOPICS_FILE.exists():
        lines = [line.strip() for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            next_topic = lines[0]
            # Remove the consumed topic from file
            TOPICS_FILE.write_text("\n".join(lines[1:]), encoding="utf-8")
            return next_topic

    # Pick from default pool
    for topic in DEFAULT_TOPIC_POOL:
        pipeline = ContentGenerationPipeline()
        if not pipeline.db.is_topic_processed(topic):
            return topic

    return "The Mystery of Dark Matter and Dark Energy"

def scheduled_job():
    topic = get_next_topic()
    logger.info(f"Running scheduled video generation for topic: '{topic}'")
    try:
        pipeline = ContentGenerationPipeline()
        pipeline.run(topic=topic, publish_youtube=False)
    except Exception as e:
        logger.error(f"Scheduled generation failed: {e}")

def start_scheduler(interval_hours: int = 6):
    scheduler = BlockingScheduler()
    logger.info(f"Starting content scheduler. Jobs will run every {interval_hours} hours.")
    # Add interval job
    scheduler.add_job(scheduled_job, "interval", hours=interval_hours)
    
    # Run once immediately on start
    scheduled_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

if __name__ == "__main__":
    start_scheduler(interval_hours=6)
