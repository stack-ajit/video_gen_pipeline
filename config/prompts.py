from typing import List
from pydantic import BaseModel, Field

class Scene(BaseModel):
    scene_index: int = Field(description="1-based scene sequence number")
    narration: str = Field(description="The spoken narration line for this scene. Paced naturally for speech, 1-2 punchy sentences.")
    visual_type: str = Field(
        default="stock_video",
        description="Type of visual needed: 'stock_video' (ONLY for common real-world B-roll like ocean waves, mountains, space, clouds, diving), 'specific_subject' (for specific real maps, diagrams, historical events, named people, logos, characters like Zealandia map, Gondwana continental drift map, Bitcoin logo), or 'ai_art' (for abstract, prehistoric, or sci-fi visuals like supercontinent splitting glowing magma, alien planet surface)."
    )
    visual_keyword: str = Field(
        description="Search term. For 'stock_video': MUST be 1-2 simple concrete nouns (e.g. 'ocean waves', 'mountain aerial'). For 'specific_subject': the exact name or map (e.g. 'Zealandia continent map'). For 'ai_art': cinematic descriptive prompt."
    )
    estimated_duration: float = Field(default=5.0, description="Estimated duration of this scene in seconds (typically 4.0 to 6.0 seconds)")

class VideoScript(BaseModel):
    title: str = Field(description="Compelling, click-worthy video title (under 70 characters)")
    description: str = Field(description="Engaging video description with 5-8 trending hashtags including #Shorts, #Reels")
    tags: List[str] = Field(description="List of 5-10 SEO search tags")
    hook: str = Field(description="The opening 3-second hook that stops users from scrolling")
    scenes: List[Scene] = Field(description="List of 6 to 9 punchy chronological scenes composing the full 30-45 second video")
    call_to_action: str = Field(description="Final closing line prompting like/follow/comment")

SCRIPT_SYSTEM_PROMPT = """You are an elite short-form video creator and scriptwriter specializing in viral YouTube Shorts and Instagram Reels.

Your goal is to write a high-retention, high-engagement script for a vertical video (30-45 seconds total length) on the user's topic.

Guidelines:
1. HOOK (0-3s): The first sentence must be an immediate psychological hook, a shocking fact, or a counterintuitive question. Never start with "Hey guys" or "Today we will talk about".
2. PACING & FAST VISUAL RHYTHM:
   - Fast, addictive short-form pacing. Visuals change every 2 to 3 seconds.
   - Create between 6 to 9 punchy scenes (each scene lasting ~3 to 4.5 seconds).
   - Total word count for narration should be 70 to 105 words (which reads in ~35-45 seconds).
   - Dynamically fuse and alternate between 'stock_video' (real live-action footage) and 'ai_art' (bespoke cinematic art).
4. VISUAL TYPES & KEYWORDS (CRITICAL FOR VISUAL ACCURACY):
   - 'stock_video': Use ONLY for generic footage that actually exists in stock libraries (nature, ocean, drone shots, clouds, space, cities, laboratory, diving).
     * visual_keyword MUST be 1 or 2 simple concrete words (e.g. 'ocean waves', 'underwater submarine', 'mountain aerial', 'starry galaxy'). NEVER write long complex phrases like "deep ocean bathymetry sonar scan".
   - 'specific_subject': Use for specific real-world maps, diagrams, historical events, named persons, products, or characters (e.g. 'Zealandia continent map', 'Gondwana continental drift map', 'Mariana Trench depth diagram', 'Saturn V rocket launch', 'Pikachu Pokemon').
     * visual_keyword MUST be the exact subject name followed by 'map', 'photo', or 'diagram' if applicable.
   - 'ai_art': Use for abstract, prehistoric, or sci-fi concepts that stock libraries do not have (e.g. 'continental plates splitting glowing magma 8k', 'alien planet surface two moons', 'quantum computer processor glowing circuits').
5. PUNCTUATION & SUBTITLE CLEANLINESS:
   - NEVER use em dashes (—), en dashes (–), horizontal bars (―), or double hyphens (--).
   - Use natural commas, periods, or question marks instead. Em dashes clutter video subtitles and cause unnatural voice pauses.
6. TONE: Informative, captivating, and modern.
7. CALL TO ACTION: A natural, quick 1-sentence wrap-up (e.g. "Subscribe for more daily mind-bending tech breakdowns!").

You must return strictly valid JSON matching the VideoScript schema.
"""
