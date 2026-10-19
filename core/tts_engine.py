import asyncio
import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import edge_tts
from moviepy import AudioFileClip

from config.config import DEFAULT_VOICE, VOICE_RATE, TEMP_DIR
from config.prompts import Scene

logger = logging.getLogger(__name__)

def sanitize_narration(text: str) -> str:
    """Removes em dashes, en dashes, and redundant dashes for smooth speech and clean captions."""
    if not text:
        return text
    text = re.sub(r"[—–―]", ", ", text)
    text = re.sub(r"--+", ", ", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

class TTSEngine:
    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = VOICE_RATE):
        self.voice = voice
        self.rate = rate

    async def _synthesize_clip_async(
        self, text: str, output_audio_path: Path
    ) -> Tuple[float, List[Dict]]:
        """
        Synthesizes a single text snippet to MP3 and extracts precise word boundaries.
        Returns: (duration_in_seconds, word_cues)
        """
        clean_text = sanitize_narration(text)
        communicate = edge_tts.Communicate(
            clean_text, self.voice, rate=self.rate, boundary="WordBoundary"
        )
        word_cues = []

        with open(output_audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    word_cues.append({
                        "start": start_sec,
                        "end": start_sec + dur_sec,
                        "text": chunk["text"]
                    })

        # Calculate exact duration using MoviePy AudioFileClip
        audio_clip = AudioFileClip(str(output_audio_path))
        duration = audio_clip.duration
        audio_clip.close()

        return duration, word_cues

    def synthesize_scene(self, text: str, output_audio_path: Path) -> Tuple[float, List[Dict]]:
        """Synchronous wrapper for scene audio synthesis."""
        return asyncio.run(self._synthesize_clip_async(text, output_audio_path))

    def process_scenes_audio(self, scenes: List[Scene], output_dir: Optional[Path] = None) -> List[Dict]:
        """
        Synthesizes individual audio files for each scene in the script.
        Returns list of metadata dicts with exact word cues for millisecond subtitle alignment.
        """
        work_dir = output_dir or TEMP_DIR
        scene_audio_results = []
        total_duration = 0.0

        logger.info(f"Synthesizing voiceover for {len(scenes)} scenes using voice '{self.voice}' (boundary=WordBoundary)...")

        for idx, scene in enumerate(scenes, 1):
            audio_filename = work_dir / f"scene_{idx:02d}_audio.mp3"
            duration, word_cues = self.synthesize_scene(scene.narration, audio_filename)
            total_duration += duration

            logger.info(f"Scene {idx} synthesized: {duration:.2f}s ({len(word_cues)} words) -> {audio_filename.name}")
            scene_audio_results.append({
                "scene_index": scene.scene_index,
                "narration": scene.narration,
                "visual_keyword": scene.visual_keyword,
                "visual_type": getattr(scene, "visual_type", "stock_video"),
                "audio_path": audio_filename,
                "duration": duration,
                "word_cues": word_cues
            })

        logger.info(f"All scenes synthesized successfully. Total voiceover length: {total_duration:.2f}s")
        return scene_audio_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tts = TTSEngine()
    test_scenes = [
        Scene(scene_index=1, narration="Did you know neutron stars are the densest objects in space?", visual_keyword="neutron star space"),
        Scene(scene_index=2, narration="A single teaspoon would weigh billions of tons on Earth.", visual_keyword="gravity weight planet")
    ]
    results = tts.process_scenes_audio(test_scenes)
    for r in results:
        print(f"Scene {r['scene_index']}: {r['duration']:.2f}s | Audio: {r['audio_path']}")
