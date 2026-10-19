import argparse
import logging
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config.config import BASE_DIR
from core.llm_engine import LLMEngine
from core.tts_engine import TTSEngine
from core.media_fetcher import MediaFetcher
from core.video_composer import VideoComposer
from core.database import Database
from publishers.youtube_publisher import YouTubePublisher
from publishers.instagram_publisher import InstagramPublisher

# Configure crisp console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PipelineRunner")

class ContentGenerationPipeline:
    def __init__(self):
        self.llm = LLMEngine()
        self.tts = TTSEngine()
        self.media_fetcher = MediaFetcher()
        self.composer = VideoComposer()
        self.db = Database()
        self.youtube = YouTubePublisher()
        self.instagram = InstagramPublisher()

    def _clean_temp_dir(self):
        """Purges stale scene assets and temporary files from temp directory."""
        from config.config import TEMP_DIR
        for item in TEMP_DIR.glob("*"):
            # Preserve last generated script for inspection/debugging
            if item.is_file() and item.name != "last_generated_script.json":
                try:
                    item.unlink()
                except Exception:
                    pass

    def run(
        self,
        topic: str,
        publish_youtube: bool = False,
        publish_instagram: bool = False,
        privacy_status: str = "unlisted",
        force: bool = False
    ) -> Path:
        """
        Executes the entire end-to-end video creation and publication pipeline.
        """
        print("\n" + "=" * 65)
        print(f"🎬 STARTING AUTOMATED VIDEO PIPELINE FOR TOPIC:\n   '{topic}'")
        print("=" * 65)

        # Step 1: Duplicate check
        if not force and self.db.is_topic_processed(topic):
            logger.warning(f"Topic '{topic}' was already processed previously. Use --force to re-generate.")
            return None

        # Clean temp directory for fresh assets
        self._clean_temp_dir()

        # Step 2: Generate Script with Gemini
        logger.info("🧠 Step 1/5: Generating high-retention script with Google Gemini...")
        script = self.llm.generate_script(topic)
        print(f"\n📌 TITLE: {script.title}")
        print(f"🎣 HOOK:  {script.hook}")
        print(f"🎞️  SCENES: {len(script.scenes)}\n")

        # Step 3: Synthesize Voiceover & Timings
        logger.info("🎙️ Step 2/5: Synthesizing neural voiceover with Edge-TTS...")
        scene_audio_data = self.tts.process_scenes_audio(script.scenes)

        # Step 4: Sourcing / Generating Visual Clips
        logger.info("🎥 Step 3/5: Sourcing 1080x1920 vertical video clips...")
        processed_scenes = []
        for scene_info in scene_audio_data:
            scene_idx = scene_info["scene_index"]
            keyword = scene_info["visual_keyword"]
            duration = scene_info["duration"]

            clip_path = self.media_fetcher.fetch_clip_for_scene(
                scene_index=scene_idx,
                keyword=keyword,
                target_duration=duration,
                visual_type=scene_info.get("visual_type", "stock_video"),
                narration=scene_info.get("narration", "")
            )
            scene_info["clip_path"] = clip_path
            processed_scenes.append(scene_info)

        # Step 5: Video Composition (Concat + BGM + Subtitle Burn)
        logger.info("🎞️ Step 4/5: Compositing final video, background music, and subtitles...")
        final_video_path = self.composer.compose_video(
            title=script.title,
            scene_data=processed_scenes
        )

        total_duration = sum(s["duration"] for s in processed_scenes)

        # Step 6: Record in Database
        video_id = self.db.save_video_record(
            topic=topic,
            title=script.title,
            description=script.description,
            tags=script.tags,
            video_path=final_video_path,
            duration=total_duration
        )
        logger.info(f"Saved video record #{video_id} to database.")

        # Step 7: Publishing (Optional)
        if publish_youtube:
            logger.info("🚀 Step 5/5: Uploading video to YouTube Shorts...")
            try:
                yt_id = self.youtube.upload_short(
                    video_path=final_video_path,
                    title=script.title,
                    description=script.description,
                    tags=script.tags,
                    privacy_status=privacy_status
                )
                self.db.update_status(video_id, "youtube", "UPLOADED")
                print(f"\n🎉 LIVE ON YOUTUBE SHORTS: https://youtube.com/shorts/{yt_id}")
            except Exception as e:
                logger.error(f"YouTube upload skipped or failed: {e}")
                self.db.update_status(video_id, "youtube", "FAILED")

        if publish_instagram:
            logger.info("📸 Step 5/5: Uploading Reel to Instagram...")
            try:
                caption = f"{script.title}\n\n{script.description}"
                reel_url = self.instagram.upload_reel(
                    video_path=final_video_path,
                    caption=caption
                )
                self.db.update_status(video_id, "instagram", "UPLOADED")
                print(f"\n🎉 LIVE ON INSTAGRAM REELS: {reel_url}")
            except Exception as e:
                logger.error(f"Instagram upload skipped or failed: {e}")
                self.db.update_status(video_id, "instagram", "FAILED")

        # Step 8: Maintain Clean Output Organization & Refresh Catalog
        self._update_output_management(final_video_path)

        print("\n" + "=" * 65)
        print(f"✅ VIDEO GENERATION COMPLETE!")
        print(f"📁 FINAL VIDEO: {final_video_path}")
        print(f"⏱️ DURATION:    {total_duration:.1f} seconds")
        print(f"📋 CATALOG:     {BASE_DIR / 'output' / 'CATALOG.md'}")
        print("=" * 65 + "\n")

        return final_video_path

    def _update_output_management(self, final_video_path: Path):
        """Maintains clean output/ organization: updates latest/, cleans temp chunks, and refreshes catalog."""
        try:
            import shutil
            from config.config import LATEST_DIR, THUMBNAILS_DIR, TEMP_DIR
            from core.catalog_manager import generate_catalog

            # 1. Update output/latest/
            latest_vid = LATEST_DIR / "latest_short.mp4"
            shutil.copy2(final_video_path, latest_vid)

            thumb_path = THUMBNAILS_DIR / f"{final_video_path.stem}.jpg"
            if thumb_path.exists():
                shutil.copy2(thumb_path, LATEST_DIR / "latest_thumbnail.jpg")

            # 2. Clean temporary scene clips and audio chunks from output/temp/
            for f in TEMP_DIR.iterdir():
                if f.is_file() and f.name != "last_generated_script.json":
                    try:
                        f.unlink()
                    except Exception:
                        pass

            # 3. Refresh interactive catalog
            generate_catalog()
            logger.info("Maintained clean output structure and refreshed CATALOG.md.")
        except Exception as e:
            logger.warning(f"Output organization post-hook skipped: {e}")


def main():
    parser = argparse.ArgumentParser(description="AI Short-Form Video Generation Pipeline")
    parser.add_argument("--topic", type=str, required=True, help="Topic for the video")
    parser.add_argument("--publish-youtube", action="store_true", help="Upload result to YouTube Shorts")
    parser.add_argument("--publish-instagram", action="store_true", help="Upload result to Instagram Reels")
    parser.add_argument("--publish-all", action="store_true", help="Upload result to both YouTube and Instagram")
    parser.add_argument("--privacy", type=str, default="unlisted", choices=["public", "unlisted", "private"], help="YouTube privacy status")
    parser.add_argument("--force", action="store_true", help="Re-generate even if topic exists in database")

    args = parser.parse_args()

    pub_yt = args.publish_youtube or args.publish_all
    pub_ig = args.publish_instagram or args.publish_all

    pipeline = ContentGenerationPipeline()
    pipeline.run(
        topic=args.topic,
        publish_youtube=pub_yt,
        publish_instagram=pub_ig,
        privacy_status=args.privacy,
        force=args.force
    )


if __name__ == "__main__":
    main()
