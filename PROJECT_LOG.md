# AI Video Content Generation Pipeline - Project Log

All progress, setup steps, architectural decisions, and module implementations are recorded here chronologically.

---

## [2026-10-11] - Project Inception & Phase 1 Setup

### Completed
- **Architecture & Planning**: Created [IMPLEMENTATION_PLAN.md](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/IMPLEMENTATION_PLAN.md) mapping out all 8 phases inspired by the TechCrunch automation repo and `pipeline.txt`.
- **Environment & Foundation**:
  - Prepared [requirements.txt](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/requirements.txt) with all dependencies installed.
  - Installed `google-genai` modern SDK and pinned `gemini-3.8-flash` model.
  - Created [.env.example](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/.env.example) and loaded runtime config.
  - Confirmed system `ffmpeg` binary availability with libass support.
  - Built [config/config.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/config/config.py) and [config/prompts.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/config/prompts.py) with structured Pydantic schemas.
- **LLM Script Engine ([core/llm_engine.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/llm_engine.py))**:
  - Powered by Gemini 3.8 Flash.
  - Generates viral hook, 5-7 scene breakdowns with precise visual queries and narration.
- **Voiceover & Subtitles ([core/tts_engine.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/tts_engine.py))**:
  - Neural text-to-speech using Microsoft Edge TTS (`en-US-ChristopherNeural`).
  - Extracts exact millisecond-accurate timestamps and SRT subtitle files.
- **Visual Asset Fetcher ([core/media_fetcher.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/media_fetcher.py))**:
  - Pexels Video API integration for 9:16 vertical clips.
  - Free high-res AI visual generation fallback + smooth Ken Burns zoom-in motion filter.
- **Video Composer ([core/video_composer.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/video_composer.py))**:
  - Lossless concat of video clips and audio tracks.
  - Generates ambient synth background music bed with auto-ducking to 12% under speech.
  - Burns high-visibility yellow/white bold subtitles centered in lower third.
- **Database Tracking ([core/database.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/database.py))**:
  - SQLite database (`data/pipeline.db`) tracking processed topics, video file paths, durations, and social upload states.
- **Social Media Publishing ([publishers/youtube_publisher.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/publishers/youtube_publisher.py))**:
  - YouTube Data API v3 OAuth2 uploader tagging videos for Shorts shelf indexing.
- **Master Orchestrator ([main.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/main.py))**:
  - CLI runner connecting all stages with `--topic`, `--force`, and `--publish-youtube` flags.
- **Scheduler ([scheduler.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/scheduler.py))**:
  - Background scheduler running every N hours using topics queue in [topics.txt](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/topics.txt).

- **Milestone 1 Test Completed**:
  - Successfully generated and rendered full vertical short-form video: [output/final/short_Why_Nothing_Can_Beat_The_Speed_Of_Light_20261011_211112.mp4](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/output/final/short_Why_Nothing_Can_Beat_The_Speed_Of_Light_20261011_211112.mp4)
  - **Topic**: *"Why You Cannot Travel Faster Than Light"*
  - **Title**: *"Why Nothing Can Beat The Speed Of Light"*
  - **Hook**: *"The universe has a strict speed limit, and trying to break it breaks reality itself."*
  - **Specs**: 1080x1920 (9:16 vertical), 41.0 seconds duration, 6.69 MB file size.
  - **Audio & Subtitles**: Christopher Neural TTS, synced ambient BGM, animated captions burned into lower-third.
  - **Database Status**: Video Record #1 inserted into SQLite with status `PENDING`.

- **Media Fetcher Enhanced**:
  - Pexels paused new API key issuances. Added full integration with **Pixabay Video API** (instant free keys) as primary stock video source.
  - Retained zero-key AI image + Ken Burns zoom motion fallback.

- **YouTube Credentials Installed**:
  - Successfully detected, moved, and verified [client_secret.json](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/client_secret.json) from Google Cloud Console with installed Desktop OAuth client ID.
  - YouTube publishing pipeline is primed for 1-click publishing.

- **Pixabay Stock Video Engine Fixed & Verified**:
  - Identified that Pixabay's Cloudflare layer requires a modern browser `User-Agent` header (default Python request agents trigger 403 Forbidden).
  - Verified user's API key `58010896-702a507db345d119b3d70775e` now successfully retrieves and streams real 1080x1920 HD vertical stock footage.
  - Implemented multi-stage search fallback (full phrase -> 2 words -> main subject).

- **Caption Positioning & Viral Pacing Upgrades**:
  - Bound subtitles to explicit `PlayResX=1080,PlayResY=1920` canvas with `MarginV=180` and `Alignment=2` (pinned to the bottom third, perfectly clearing phone UI bars).
  - Switched subtitle chunking from 6 words down to punchy 3–4 word bursts with font size 54 and bold black outline for viral short-form retention.
  - Enhanced FFmpeg output to studio quality (`-crf 18`, pristine H.264).
  - Improved Gemini prompt to force concrete, tangible physical subjects for exact stock footage matching.

### Current State & Ready Actions
- Full generation and publication pipeline is completely configured and ready for both **YouTube Shorts** and **Instagram Reels**.
- Commands available:
  - YouTube upload:
    ```powershell
    python main.py --topic "Your Topic" --publish-youtube
    ```
  - Instagram Reels upload:
    ```powershell
    python main.py --topic "Your Topic" --publish-instagram
    ```
  - Dual simultaneous publishing (YouTube + Instagram):
    ```powershell
    python main.py --topic "Your Topic" --publish-all
    ```
  - Autonomous scheduled publishing:
    ```powershell
    python scheduler.py
    ```

- **Audio Truncation (Last 10 Seconds Silence) Diagnosed & Fixed**:
  - **Root Cause**: In [core/video_composer.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/video_composer.py), the final FFmpeg muxing command contained the `-shortest` flag without explicit stream mapping. Because of demuxer timestamp handling between concatenated video chunks and the mixed audio stream, `-shortest` triggered an early audio EOF approximately 10 seconds before the video ended, resulting in zero audio (RMS = 0.0000) during the final scene.
  - **Fix Implemented**:
    1. Removed `-shortest` from the final FFmpeg command.
    2. Added explicit stream mapping: `-map 0:v:0 -map 1:a:0`.
    3. Applied exact target duration trimming: `-t f"{total_duration:.2f}"`.
    4. Added audio timestamp resampling (`aresample=async=1000`) and set `dropout_transition=0` in `amix` to ensure uninterrupted audio and background music across scene boundaries right up to the final millisecond.
  - **Verification**: Verified via RMS analysis across all seconds that audio volume is maintained throughout the full video duration with zero silent gaps.

- **Dual-Mode Visual Engine (Pop Culture & Specific Subjects) Implemented & Verified**:
  - **Issue**: Scenes with specific characters or pop culture items (e.g., Pikachu, Monopoly Man, Darth Vader) received generic or unrelated stock video from Pixabay because royalty-free stock libraries do not host copyrighted or specific branded subjects.
  - **Solution Implemented**:
    1. **Schema & Prompt Upgrade ([config/prompts.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/config/prompts.py))**:
       - Added `visual_type` field (`'specific_subject'` vs `'stock_video'`).
       - Strict instructions to Gemini to provide exact real names (e.g., `'Pikachu Pokemon'`, `'Monopoly Man Uncle Pennybags'`, `'Darth Vader Star Wars'`, `'Fruit of the Loom logo'`) instead of generic euphemisms (`'yellow toy figure'`).
    2. **Authentic Web Sourcing ([core/media_fetcher.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/media_fetcher.py))**:
       - Implemented `_fetch_web_subject_clip()` using Bing Images + Wikimedia Commons with automated PIL image integrity validation.
       - Implemented `_render_image_to_motion_clip()` converting high-resolution authentic subject images into studio-quality 1080x1920 9:16 vertical video clips with cinematic Ken Burns slow-zoom motion.
       - Dynamic fallback hierarchy: Exact subject image -> Pixabay HD vertical stock video -> Pollinations AI art.
  - **Verification**: Verified on *"The Mandela Effect"* topic:
    - Scene 1: Pixabay Stock Video (`human brain neon glitch`)
    - Scene 2: Authentic Subject Visual (`Pikachu Pokemon`)
    - Scene 3: Authentic Subject Visual (`Monopoly Man Uncle Pennybags`)
    - Scene 4: Authentic Subject Visual (`Fruit of the Loom logo`)
    - Scene 5: Authentic Subject Visual (`Darth Vader Star Wars`)
    - Scene 6: Pixabay Stock Video (`multiverse wormhole portal`)
    - Rendered to [output/videos/short_3_Mandela_Effects_That_Prove_Your_Memory_20261013_021006.mp4](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/output/videos/short_3_Mandela_Effects_That_Prove_Your_Memory_20261013_021006.mp4) with 100% visual relevance.

- **Output Directory Restructured into Clean Categories**:
  - **Structure**:
    ```
    output/
    ├── videos/       # Finished, studio-grade vertical .mp4 videos (no junk)
    ├── thumbnails/   # Crisp cover thumbnails (.jpg) for YouTube & Instagram
    └── temp/         # Ephemeral workspace, automatically purged between runs
    ```
  - **Enhancements**:
    1. Migrated all 8 final videos into [output/videos](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/output/videos).
    2. Migrated all cover thumbnails into [output/thumbnails](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/output/thumbnails).
    3. Purged 23 stale diagnostic files from `output/temp/`.
    4. Automatically cleans `output/temp/` at the start of every run in [main.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/main.py).
    5. Updated [publishers/instagram_publisher.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/publishers/instagram_publisher.py) and [core/video_composer.py](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/core/video_composer.py) to automatically route cover images to `output/thumbnails/`.
    6. Updated SQLite database records in `data/pipeline.db` to reference the new clean paths.

- **System Schematic & Architecture Blueprint Added**:
  - Created [PIPELINE_ARCHITECTURE.md](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/PIPELINE_ARCHITECTURE.md) featuring full Mermaid flowchart schematics, sequence diagrams, and technical specifications for the entire automated engine.

- **Edge-TTS WebSocket 403 Handshake Error Resolved**:
  - **Issue**: Microsoft recently rolled out a protocol change to Edge Read-Aloud endpoints requiring updated `Sec-MS-GEC` token generation, causing `WSServerHandshakeError: 403` on `edge-tts` v7.2.8.
  - **Fix**: Upgraded `edge-tts` to `7.3.1` (which incorporates the new handshake signatures) and updated [requirements.txt](file:///c:/Users/BIT/Downloads/ai_video_content_gen_pipeline/requirements.txt). Speech synthesis and millisecond SRT generation tested and fully verified.



