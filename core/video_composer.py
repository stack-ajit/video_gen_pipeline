import os
import subprocess
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
import datetime

from config.config import (
    BASE_DIR,
    FINAL_DIR,
    TEMP_DIR,
    MUSIC_DIR,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    FPS,
    BGM_VOLUME,
    VOICE_VOLUME,
    FFMPEG_BINARY,
    SUBTITLE_FONT,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_PRIMARY_COLOR,
    SUBTITLE_OUTLINE_COLOR,
    SUBTITLE_OUTLINE_WIDTH,
    SUBTITLE_SHADOW_DEPTH,
    SUBTITLE_ALIGNMENT,
    SUBTITLE_MARGIN_V,
    SUBTITLE_MARGIN_H,
)

logger = logging.getLogger(__name__)

class VideoComposer:
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.final_dir = FINAL_DIR
        self.music_dir = MUSIC_DIR

    def compose_video(
        self,
        title: str,
        scene_data: List[Dict],
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Takes processed scene data (clips + audio + subtitle timings) and renders
        the final 1080x1920 MP4 video with synced audio, background music, and burned subtitles.
        """
        logger.info(f"Starting video composition for '{title}' ({len(scene_data)} scenes)...")

        # 1. Prepare Concat File for Video Clips
        concat_txt = self.temp_dir / "video_concat_list.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for scene in scene_data:
                clip_path = Path(scene["clip_path"]).resolve()
                f.write(f"file '{clip_path.as_posix()}'\n")

        stitched_video = self.temp_dir / "stitched_raw_video.mp4"
        cmd_concat_video = [
            FFMPEG_BINARY, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
            str(stitched_video)
        ]
        subprocess.run(cmd_concat_video, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        total_duration = sum(scene["duration"] for scene in scene_data)

        # 2. Prepare Concat File for Audio Tracks
        audio_concat_txt = self.temp_dir / "audio_concat_list.txt"
        with open(audio_concat_txt, "w", encoding="utf-8") as f:
            for scene in scene_data:
                audio_path = Path(scene["audio_path"]).resolve()
                f.write(f"file '{audio_path.as_posix()}'\n")

        master_voiceover = self.temp_dir / "master_voiceover.mp3"
        cmd_concat_audio = [
            FFMPEG_BINARY, "-y", "-f", "concat", "-safe", "0",
            "-i", str(audio_concat_txt),
            "-af", "aresample=async=1000",
            "-c:a", "libmp3lame",
            str(master_voiceover)
        ]
        subprocess.run(cmd_concat_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Build Synchronized Master SRT Subtitle File
        master_srt_path = self.temp_dir / "master_subtitles.srt"
        self._build_master_srt(scene_data, master_srt_path)

        # 4. Prepare Background Music Track
        bgm_track = self._get_or_create_bgm_track(title)

        # 5. Mix Audio (Voiceover + Ducked BGM with smooth outro fade)
        master_audio_mixed = self.temp_dir / "master_audio_mixed.mp3"
        fade_out_start = max(1.0, total_duration - 1.5)
        filter_complex = (
            f"[0:a]aresample=async=1000,volume={VOICE_VOLUME}[v];"
            f"[1:a]loudnorm=I=-20:TP=-1.5:LRA=11,volume={BGM_VOLUME},aloop=loop=-1:size=2e+09,afade=t=out:st={fade_out_start:.2f}:d=1.5[b];"
            f"[v][b]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[outa]"
        )
        cmd_mix_audio = [
            FFMPEG_BINARY, "-y",
            "-i", str(master_voiceover),
            "-i", str(bgm_track),
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame",
            str(master_audio_mixed)
        ]
        subprocess.run(cmd_mix_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 6. Burn Subtitles and Combine Video + Audio into Final Render
        safe_title = re.sub(r"[^\w\-_]", "_", title)[:40]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not output_filename:
            output_filename = f"short_{safe_title}_{timestamp}.mp4"

        final_output_path = self.final_dir / output_filename

        # Windows FFmpeg subtitles filter path escaping with explicit 1080x1920 PlayRes
        escaped_srt = str(master_srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
        subtitle_filter = (
            f"subtitles='{escaped_srt}':force_style='"
            f"PlayResX=1080,PlayResY=1920,"
            f"Fontname={SUBTITLE_FONT},Bold=1,FontSize={SUBTITLE_FONT_SIZE},"
            f"PrimaryColour={SUBTITLE_PRIMARY_COLOR},"
            f"OutlineColour={SUBTITLE_OUTLINE_COLOR},"
            f"BorderStyle=1,Outline={SUBTITLE_OUTLINE_WIDTH},Shadow={SUBTITLE_SHADOW_DEPTH},"
            f"Alignment={SUBTITLE_ALIGNMENT},MarginV={SUBTITLE_MARGIN_V},"
            f"MarginL={SUBTITLE_MARGIN_H},MarginR={SUBTITLE_MARGIN_H}'"
        )

        logger.info(f"Rendering final composition with burned subtitles to {final_output_path}...")
        cmd_final = [
            FFMPEG_BINARY, "-y",
            "-i", str(stitched_video),
            "-i", str(master_audio_mixed),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-t", f"{total_duration:.2f}",
            "-vf", subtitle_filter,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(final_output_path)
        ]
        subprocess.run(cmd_final, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Extract crisp cover thumbnail into thumbnails directory
        try:
            from config.config import THUMBNAILS_DIR
            cover_path = THUMBNAILS_DIR / f"{final_output_path.stem}.jpg"
            cmd_thumb = [
                FFMPEG_BINARY, "-y", "-ss", "00:00:01",
                "-i", str(final_output_path),
                "-vframes", "1", "-q:v", "2",
                str(cover_path)
            ]
            subprocess.run(cmd_thumb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        logger.info(f"Video composition finished successfully: {final_output_path} ({final_output_path.stat().st_size / (1024*1024):.2f} MB)")
        return final_output_path

    def _chunk_narration(self, text: str, max_words: int = 3) -> List[str]:
        """
        Splits narration into balanced 2-3 word chunks so subtitles are punchy,
        center-aligned, and never leave an awkward single-word orphan line.
        """
        words = text.strip().split()
        if not words:
            return []
        total = len(words)
        if total <= max_words:
            return [" ".join(words)]

        num_chunks = max(1, (total + max_words - 1) // max_words)
        base_len, rem = divmod(total, num_chunks)
        chunks = []
        idx = 0
        for i in range(num_chunks):
            count = base_len + (1 if i < rem else 0)
            chunks.append(" ".join(words[idx : idx + count]))
            idx += count
        return chunks

    def _build_master_srt(self, scene_data: List[Dict], output_srt: Path):
        """
        Compiles continuous timestamps for all scenes into a single .srt file.
        Uses exact word cues captured from Edge-TTS WordBoundary events so speech
        and subtitles are aligned to the millisecond, with 0 em-dashes and no flicker.
        """
        entries = []
        accumulated_offset = 0.0
        counter = 1

        for scene in scene_data:
            duration = scene["duration"]
            narration = scene.get("narration", "")
            word_cues = scene.get("word_cues")

            if word_cues:
                # Group exact word cues into balanced 2-3 word chunks
                max_words = 3
                total = len(word_cues)
                num_chunks = max(1, (total + max_words - 1) // max_words)
                base_len, rem = divmod(total, num_chunks)

                scene_chunks = []
                idx = 0
                for i in range(num_chunks):
                    count = base_len + (1 if i < rem else 0)
                    group = word_cues[idx : idx + count]
                    text_str = " ".join(w["text"] for w in group)
                    # Strip any em dashes, en dashes, or multiple hyphens
                    text_str = re.sub(r"[—–―]", "", text_str)
                    text_str = re.sub(r"--+", "", text_str)
                    text_str = re.sub(r"\s+", " ", text_str).strip()

                    start_t = accumulated_offset + group[0]["start"]
                    end_t = accumulated_offset + group[-1]["end"]

                    scene_chunks.append({
                        "start": start_t,
                        "end": end_t,
                        "text": text_str.upper()
                    })
                    idx += count

                # Smooth micro-gaps (<0.35s) between chunks to prevent subtitle blinking/flicker
                for i in range(len(scene_chunks) - 1):
                    gap = scene_chunks[i+1]["start"] - scene_chunks[i]["end"]
                    if 0 < gap < 0.35:
                        scene_chunks[i]["end"] = scene_chunks[i+1]["start"]

                # Ensure last chunk does not exceed scene boundary
                if scene_chunks:
                    scene_chunks[-1]["end"] = min(scene_chunks[-1]["end"], accumulated_offset + duration)

                for chunk in scene_chunks:
                    if chunk["text"]:
                        entries.append(
                            f"{counter}\n"
                            f"{self._format_srt_time(chunk['start'])} --> {self._format_srt_time(chunk['end'])}\n"
                            f"{chunk['text']}\n"
                        )
                        counter += 1
            else:
                # Fallback if word_cues were not available
                clean_narration = re.sub(r"[—–―]", "", narration)
                clean_narration = re.sub(r"--+", "", clean_narration).strip()
                chunks = self._chunk_narration(clean_narration, max_words=3)
                chunk_duration = duration / max(len(chunks), 1)

                for i, chunk in enumerate(chunks):
                    c_start = accumulated_offset + (i * chunk_duration)
                    c_end = c_start + chunk_duration
                    entries.append(
                        f"{counter}\n"
                        f"{self._format_srt_time(c_start)} --> {self._format_srt_time(c_end)}\n"
                        f"{chunk.upper()}\n"
                    )
                    counter += 1

            accumulated_offset += duration

        output_srt.write_text("\n".join(entries), encoding="utf-8")

    def _format_srt_time(self, seconds: float) -> str:
        millis = int((seconds - int(seconds)) * 1000)
        td = datetime.timedelta(seconds=int(seconds))
        hours, remainder = divmod(td.seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _download_default_bgm_tracks(self):
        """Downloads starter royalty-free background music tracks for Shorts/Reels."""
        import urllib.request
        logger.info("Initializing royalty-free background music library in assets/music/...")
        tracks = {
            "suspense_mystery.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Descent.mp3",
            "playful_hook.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%20Snitch.mp3",
            "chill_aesthetic.mp3": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clean%20Soul.mp3",
        }
        for name, url in tracks.items():
            dest = self.music_dir / name
            if not dest.exists():
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=25) as r, open(dest, "wb") as f:
                        while chunk := r.read(65536):
                            f.write(chunk)
                    logger.info(f"Downloaded BGM track '{name}' ({dest.stat().st_size} bytes).")
                except Exception as e:
                    logger.warning(f"Failed downloading {name}: {e}")

    def _get_or_create_bgm_track(self, title: str = "") -> Path:
        """
        Selects a mood-appropriate royalty-free background track from assets/music,
        ducked at a gentle background level like popular TikTok/Reels videos.
        """
        title_lower = title.lower()

        available_tracks = {
            f.stem: f for f in self.music_dir.iterdir()
            if f.is_file() and f.suffix in [".mp3", ".wav", ".m4a"]
        }

        if not available_tracks:
            self._download_default_bgm_tracks()
            available_tracks = {
                f.stem: f for f in self.music_dir.iterdir()
                if f.is_file() and f.suffix in [".mp3", ".wav", ".m4a"]
            }

        suspense_words = {
            "dark", "mystery", "secret", "deep", "ocean", "trench", "space", "terrifying", "terrified",
            "scariest", "danger", "disappear", "black hole", "quantum", "unreal", "waterfall",
            "ai", "artificial intelligence", "experiment", "banned", "basilisk", "roko", "silicon",
            "robot", "simulation", "matrix", "horror", "warning", "deadly", "borehole", "void"
        }
        curiosity_words = {
            "brain", "psychology", "mind", "quirk", "mandela", "weird", "hack", "facts",
            "eye contact", "sleep", "syndrome", "effect", "illusion", "trick"
        }

        if any(w in title_lower for w in suspense_words) and "suspense_mystery" in available_tracks:
            chosen = available_tracks["suspense_mystery"]
        elif any(w in title_lower for w in curiosity_words) and "playful_hook" in available_tracks:
            chosen = available_tracks["playful_hook"]
        elif "chill_aesthetic" in available_tracks:
            chosen = available_tracks["chill_aesthetic"]
        elif available_tracks:
            chosen = list(available_tracks.values())[0]
        else:
            chosen = self.music_dir / "suspense_mystery.mp3"

        logger.info(f"Selected background music: '{chosen.name}' (volume ducked to {BGM_VOLUME*100:.0f}%)")
        return chosen


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("VideoComposer module loaded.")
