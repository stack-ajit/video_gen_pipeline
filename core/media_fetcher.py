import os
import subprocess
import logging
import re
import random
from pathlib import Path
from typing import Optional, List
import urllib.parse
import urllib.request
import requests
from PIL import Image

from config.config import PEXELS_API_KEY, PIXABAY_API_KEY, TEMP_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS, FFMPEG_BINARY

logger = logging.getLogger(__name__)

class MediaFetcher:
    def __init__(self, pexels_api_key: Optional[str] = None, pixabay_api_key: Optional[str] = None):
        self.pexels_api_key = pexels_api_key or PEXELS_API_KEY
        self.pixabay_api_key = pixabay_api_key or PIXABAY_API_KEY
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _fetch_single_subclip(
        self,
        scene_index: int,
        keyword: str,
        duration: float,
        visual_type: str,
        output_path: Path,
        narration: str = ""
    ) -> Path:
        """Retrieves or generates a single atomic visual clip of the given duration."""
        # Route 1: AI Art (for abstract, futuristic, prehistoric, or cosmic concepts)
        if visual_type == "ai_art":
            logger.info(f"Scene {scene_index}: Generating bespoke AI visual for '{keyword}' ({duration:.1f}s)...")
            return self._generate_ai_motion_clip(scene_index, keyword, duration, output_path, narration=narration)

        # Route 2: Specific Subject (Characters, celebrities, maps, diagrams, named entities)
        if visual_type == "specific_subject":
            logger.info(f"Scene {scene_index}: Searching authentic web visuals for specific subject '{keyword}' ({duration:.1f}s)...")
            if self._fetch_web_subject_clip(keyword, duration, output_path):
                return output_path
            # Fallback for specific subject: generate bespoke AI art
            return self._generate_ai_motion_clip(scene_index, keyword, duration, output_path, narration=narration)

        # Route 3: Atmospheric / Stock Video (Nature, oceans, space, drone shots)
        if self.pixabay_api_key:
            if self._fetch_pixabay_video(keyword, duration, output_path):
                return output_path

        # Route 4: Pexels API fallback if configured
        if self.pexels_api_key:
            if self._fetch_pexels_video(keyword, duration, output_path):
                return output_path

        # Route 5: If stock video had no relevant results, try authentic web imagery (map/diagram/photo)
        if self._fetch_web_subject_clip(keyword, duration, output_path):
            return output_path

        # Route 6: Ultimate Fallback - High-Quality AI Generation with Studio Motion
        logger.info(f"Scene {scene_index}: Stock video unavailable for '{keyword}', generating bespoke AI art...")
        return self._generate_ai_motion_clip(scene_index, keyword, duration, output_path, narration=narration)

    def fetch_clip_for_scene(
        self,
        scene_index: int,
        keyword: str,
        target_duration: float,
        visual_type: str = "stock_video",
        narration: str = "",
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Retrieves or generates a 1080x1920 vertical MP4 clip of target_duration.
        Pacing rule: Clips change dynamically every 2 to 3 seconds strictly,
        fusing real stock footage and bespoke AI art to keep viewer attention hooked!
        """
        work_dir = output_dir or TEMP_DIR
        final_clip_path = work_dir / f"scene_{scene_index:02d}_clip.mp4"

        # Determine number of visual cuts so that no clip stays on screen longer than 2.8s
        if target_duration <= 2.9:
            cut_durations = [target_duration]
        else:
            num_cuts = max(2, int(round(target_duration / 2.3)))
            base_dur = target_duration / num_cuts
            cut_durations = [round(base_dur, 2) for _ in range(num_cuts)]
            cut_durations[-1] = round(target_duration - sum(cut_durations[:-1]), 2)

        if len(cut_durations) == 1:
            return self._fetch_single_subclip(
                scene_index=scene_index,
                keyword=keyword,
                duration=cut_durations[0],
                visual_type=visual_type,
                output_path=final_clip_path,
                narration=narration
            )

        # Multi-cut generation: Alternate Real Video and AI Art across sub-cuts
        subclip_paths = []
        for i, cut_dur in enumerate(cut_durations):
            sub_path = work_dir / f"scene_{scene_index:02d}_sub{i+1}.mp4"

            # Determine cut visual type
            if visual_type == "specific_subject":
                if i == 0:
                    cut_type = "specific_subject"
                elif i % 2 == 1:
                    cut_type = "stock_video"
                else:
                    cut_type = "ai_art"
            else:
                # Alternate Real Video and AI Art:
                # If (scene_index + i) % 2 == 1 -> Real Stock Video, else AI Art
                if (scene_index + i) % 2 == 1:
                    cut_type = "stock_video"
                else:
                    cut_type = "ai_art"

            logger.info(
                f"Scene {scene_index} [Cut {i+1}/{len(cut_durations)} - {cut_dur:.1f}s]: "
                f"Fetching {cut_type} for '{keyword}'..."
            )
            self._fetch_single_subclip(
                scene_index=scene_index,
                keyword=keyword,
                duration=cut_dur,
                visual_type=cut_type,
                output_path=sub_path,
                narration=narration
            )
            subclip_paths.append(sub_path)

        # Concatenate subclips into the final scene clip
        concat_txt = work_dir / f"scene_{scene_index:02d}_concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in subclip_paths:
                f.write(f"file '{p.resolve().as_posix()}'\n")

        cmd = [
            FFMPEG_BINARY, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
            str(final_clip_path)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup subclips
        for p in subclip_paths + [concat_txt]:
            if p.exists():
                try: p.unlink()
                except Exception: pass

        return final_clip_path

    def _fetch_web_subject_clip(self, keyword: str, duration: float, output_path: Path) -> bool:
        """
        Retrieves authentic imagery for specific subjects (maps, diagrams, historical entities,
        named celebrities, artifacts) using Wikipedia REST API and Wikimedia Commons,
        then renders a studio-grade 1080x1920 clip with the dual-layer blurred canvas.
        """
        temp_img = output_path.with_name(f"temp_img_{output_path.stem}.jpg")

        # 1. Wikipedia Summary REST API (Official, curated high-res topic imagery)
        stop_words = {"map", "diagram", "photo", "picture", "image", "logo", "drawing", "illustration", "real"}
        clean_words = [w for w in re.split(r"[\s,\-_]+", keyword) if w.lower() not in stop_words and len(w) > 1]
        candidates = []
        if clean_words:
            candidates.append(" ".join(clean_words))
            if len(clean_words) >= 2:
                candidates.append(" ".join(clean_words[:2]))
            candidates.append(clean_words[0])

        for candidate in candidates:
            try:
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(candidate)}"
                resp = requests.get(wiki_url, headers=self.browser_headers, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    img_url = data.get("originalimage", {}).get("source") or data.get("thumbnail", {}).get("source")
                    if img_url and not img_url.endswith(".svg"):
                        r_img = requests.get(img_url, headers=self.browser_headers, timeout=8)
                        if r_img.status_code == 200 and len(r_img.content) > 15000:
                            with open(temp_img, "wb") as f:
                                f.write(r_img.content)
                            with Image.open(temp_img) as im:
                                im.verify()
                            if self._render_image_to_motion_clip(temp_img, duration, output_path):
                                if temp_img.exists():
                                    temp_img.unlink()
                                logger.info(f"Acquired verified Wikipedia imagery for '{candidate}': {data.get('title')}")
                                return True
            except Exception as e:
                logger.debug(f"Wikipedia summary lookup skipped for '{candidate}': {e}")

        # 2. Wikimedia Commons Search API (Files & Diagrams)
        try:
            wiki_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": "6",
                "gsrsearch": keyword,
                "gsrlimit": "6",
                "prop": "imageinfo",
                "iiprop": "url|mime"
            }
            r = requests.get(wiki_url, params=params, headers=self.browser_headers, timeout=8)
            pages = r.json().get("query", {}).get("pages", {})
            for k, v in pages.items():
                info = v.get("imageinfo", [{}])[0]
                mime = info.get("mime", "")
                img_url = info.get("url")
                if img_url and ("jpeg" in mime or "png" in mime or "jpg" in mime):
                    r_img = requests.get(img_url, headers=self.browser_headers, timeout=8)
                    if r_img.status_code == 200 and len(r_img.content) > 15000:
                        with open(temp_img, "wb") as f:
                            f.write(r_img.content)
                        with Image.open(temp_img) as im:
                            im.verify()
                        if self._render_image_to_motion_clip(temp_img, duration, output_path):
                            if temp_img.exists():
                                temp_img.unlink()
                            logger.info(f"Acquired verified Wikimedia Commons file for '{keyword}'.")
                            return True
        except Exception as e:
            logger.debug(f"Wikimedia search error for '{keyword}': {e}")

        if temp_img.exists():
            temp_img.unlink()
        return False

    def _render_image_to_motion_clip(self, image_path: Path, duration: float, output_path: Path) -> bool:
        """
        Converts an image into a studio-grade 1080x1920 9:16 MP4.
        Crops bottom 4.5% to ensure zero platform logos or badges.
        - For native vertical images (aspect ratio <= 0.65): Smooth cinematic slow zoom.
        - For landscape / square images (aspect ratio > 0.65): CapCut / TikTok dual-layer
          blurred background canvas with centered un-cropped foreground, ensuring heads
          and subjects are never cut off.
        """
        clean_temp = image_path.with_name(f"clean_{image_path.name}")
        try:
            total_frames = int(duration * FPS) + 5

            with Image.open(image_path) as im:
                w, h = im.size
                # Clean crop bottom 4.5% to eliminate any tiny platform badge or watermark
                cropped_h = h - int(h * 0.045)
                clean_img = im.crop((0, 0, w, max(1, cropped_h)))
                clean_img.save(clean_temp, quality=95)
                aspect_ratio = w / max(1, cropped_h)

            source_file = str(clean_temp)
            if aspect_ratio <= 0.65:
                # Native vertical 9:16 - cinematic center zoom
                vf_filter = (
                    f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                    f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                    f"zoompan=z='min(zoom+0.0006,1.08)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
                )
                cmd = [
                    FFMPEG_BINARY, "-y", "-loop", "1", "-i", source_file,
                    "-vf", vf_filter,
                    "-t", f"{duration:.2f}",
                    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                    str(output_path)
                ]
            else:
                # Option 1: Dual-layer Studio Canvas (Blurred Ambient Background + Full Subject Foreground)
                vf_complex = (
                    f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                    f"boxblur=25:5,eq=brightness=-0.15:contrast=1.05,"
                    f"zoompan=z='min(zoom+0.0006,1.08)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}[bg];"
                    f"[0:v]scale=1000:-2:force_original_aspect_ratio=decrease,"
                    f"pad=iw+6:ih+6:3:3:color=white@0.35[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                )
                cmd = [
                    FFMPEG_BINARY, "-y", "-loop", "1", "-i", source_file,
                    "-filter_complex", vf_complex,
                    "-t", f"{duration:.2f}",
                    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                    str(output_path)
                ]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            logger.error(f"Image motion rendering failed: {e}")
            return False
        finally:
            if clean_temp.exists():
                try: clean_temp.unlink()
                except Exception: pass

    def _is_tag_relevant(self, query: str, tags: str) -> bool:
        """
        Validates whether a stock video's tags genuinely match the semantic topic.
        Rejects false-positive matches (e.g. cars drifting for 'continental drift').
        """
        if not tags:
            return False

        tags_lower = tags.lower()
        tag_tokens = set(re.split(r"[\s,]+", tags_lower))

        # Irrelevant blacklist tags for educational/nature/science/history/space/mystery content
        blacklist = {
            "car", "cars", "drift", "drifting", "racing", "speed", "vehicle", "highway", "traffic",
            "advertising", "logo", "intro", "fashion", "shopping", "bikini", "sexy", "party"
        }

        # Clean query tokens
        stop_words = {
            "the", "a", "an", "and", "or", "in", "on", "of", "to", "for", "with", "by", "at",
            "video", "clip", "footage", "animation", "shot", "zoom", "3d", "4k", "hd", "real",
            "slow", "motion", "background", "loop", "scan"
        }
        query_words = [w.lower().strip() for w in re.split(r"[\s,\-_]+", query) if w.strip()]
        meaningful_query_words = [w for w in query_words if w not in stop_words and len(w) > 2]

        # If query is NOT explicitly about vehicles/cars, reject any video with car/racing tags
        if not any(w in {"car", "race", "drive", "vehicle", "automobile"} for w in meaningful_query_words):
            if any(b in tag_tokens for b in blacklist):
                logger.debug(f"Rejected stock video due to blacklisted tag match in '{tags}' for query '{query}'")
                return False

        # Must match at least one meaningful word or stem from the query
        for qw in meaningful_query_words:
            stem = qw[:4] if len(qw) >= 4 else qw
            for tag in tag_tokens:
                if stem in tag or tag in qw:
                    return True

        return False

    def _fetch_pixabay_video(self, keyword: str, duration: float, output_path: Path) -> bool:
        """Queries Pixabay for verified stock video with semantic tag validation."""
        stop_words = {"the", "a", "an", "and", "or", "in", "on", "of", "to", "for", "with", "video", "animation", "footage", "clip", "zoom", "scan"}
        words = [w for w in keyword.strip().split() if w.lower() not in stop_words]

        candidate_queries = []
        if len(words) >= 2:
            candidate_queries.append(" ".join(words[:2]))
        if words:
            candidate_queries.append(words[0])
        candidate_queries.append(keyword)

        for query in candidate_queries:
            for orientation in ["vertical", "all"]:
                try:
                    url = f"https://pixabay.com/api/videos/?key={self.pixabay_api_key}&q={urllib.parse.quote(query)}&orientation={orientation}&per_page=8"
                    resp = requests.get(url, headers=self.browser_headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        hits = data.get("hits", [])
                        for hit in hits:
                            tags = hit.get("tags", "")
                            # Validate that the video's tags actually match the query topic
                            if not self._is_tag_relevant(keyword, tags):
                                continue

                            videos = hit.get("videos", {})
                            video_info = videos.get("large") or videos.get("medium") or videos.get("small")
                            if video_info and video_info.get("url"):
                                download_url = video_info["url"]
                                temp_raw = output_path.with_name(f"raw_pixabay_{output_path.name}")

                                with requests.get(download_url, headers=self.browser_headers, stream=True, timeout=20) as r:
                                    r.raise_for_status()
                                    with open(temp_raw, "wb") as f:
                                        for chunk in r.iter_content(chunk_size=8192):
                                             f.write(chunk)

                                # Normalize and crop to pristine 1080x1920 9:16 vertical video
                                cmd = [
                                    FFMPEG_BINARY, "-y", "-i", str(temp_raw),
                                    "-t", f"{duration:.2f}",
                                    "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
                                    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                                    str(output_path)
                                ]
                                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                if temp_raw.exists():
                                    temp_raw.unlink()
                                logger.info(f"Successfully downloaded verified Pixabay stock video for '{query}' (tags: {tags[:40]}...).")
                                return True
                except Exception as e:
                    logger.debug(f"Pixabay attempt failed for '{query}' ({orientation}): {e}")

        return False

    def _fetch_pexels_video(self, keyword: str, duration: float, output_path: Path) -> bool:
        """Queries Pexels for a portrait orientation video."""
        try:
            url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(keyword)}&orientation=portrait&per_page=5"
            headers = {"Authorization": self.pexels_api_key}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                videos = data.get("videos", [])
                if videos:
                    for v in videos:
                        for vf in v.get("video_files", []):
                            if vf.get("width", 0) <= vf.get("height", 0) and vf.get("link"):
                                download_url = vf["link"]
                                temp_raw_video = output_path.with_name(f"raw_{output_path.name}")
                                urllib.request.urlretrieve(download_url, temp_raw_video)

                                cmd = [
                                    FFMPEG_BINARY, "-y", "-i", str(temp_raw_video),
                                    "-t", f"{duration:.2f}",
                                    "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
                                    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-an",
                                    str(output_path)
                                ]
                                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                if temp_raw_video.exists():
                                    temp_raw_video.unlink()
                                return True
        except Exception as e:
            logger.warning(f"Pexels fetch failed for '{keyword}': {e}")
        return False

    def _generate_ai_motion_clip(
        self, scene_index: int, keyword: str, duration: float, output_path: Path, narration: str = ""
    ) -> Path:
        """
        Downloads high-resolution AI art matching the keyword and script narration context,
        and applies a smooth Ken Burns slow-zoom motion filter using FFmpeg.
        """
        temp_img = output_path.with_suffix(".jpg")

        # Extract up to 8 meaningful words from narration to make the AI visual 100% relevant to the script
        clean_narr = re.sub(r"[^\w\s]", "", narration)
        stop_words = {"this", "that", "there", "here", "what", "when", "where", "with", "from", "your", "they", "them", "have", "been", "will", "would"}
        narr_words = [w for w in clean_narr.split() if len(w) > 3 and w.lower() not in stop_words][:8]
        narr_context = " ".join(narr_words)

        if narr_context:
            prompt = f"cinematic 8k, highly detailed, dramatic lighting, vertical wallpaper, {keyword}, {narr_context}"
        else:
            prompt = f"cinematic 8k, highly detailed, dramatic lighting, vertical wallpaper, {keyword}"

        encoded_prompt = urllib.parse.quote(prompt)
        seed = random.randint(1000, 999999)
        ai_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"

        try:
            req = urllib.request.Request(ai_url, headers=self.browser_headers)
            with urllib.request.urlopen(req, timeout=25) as response, open(temp_img, "wb") as out_file:
                out_file.write(response.read())
        except Exception as e:
            logger.warning(f"AI image download fallback triggered: {e}")
            unsplash_url = f"https://images.unsplash.com/photo-1451187580459-43490279c0fa?w={VIDEO_WIDTH}&h={VIDEO_HEIGHT}&fit=crop"
            urllib.request.urlretrieve(unsplash_url, temp_img)

        self._render_image_to_motion_clip(temp_img, duration, output_path)

        if temp_img.exists():
            temp_img.unlink()

        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = MediaFetcher()
    test_clip = fetcher.fetch_clip_for_scene(
        scene_index=1,
        keyword="Pikachu Pokemon",
        target_duration=4.5,
        visual_type="specific_subject"
    )
    print(f"Generated clip successfully: {test_clip} (Size: {test_clip.stat().st_size} bytes)")
