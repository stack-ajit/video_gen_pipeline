import json
import logging
import re
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types

from config.config import GEMINI_API_KEY, TEMP_DIR
from config.prompts import VideoScript, SCRIPT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

def sanitize_script_text(text: str) -> str:
    """Removes em dashes, en dashes, and redundant dashes for clean speech and captions."""
    if not text:
        return text
    # Replace em-dashes (—), en-dashes (–), horizontal bars (―), and multiple hyphens with clean commas
    text = re.sub(r"[—–―]", ", ", text)
    text = re.sub(r"--+", ", ", text)
    # Clean up double punctuation and extra whitespace
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

class LLMEngine:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.8-flash"):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Please set GEMINI_API_KEY in your .env or env file."
            )
        
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)

    def generate_script(self, topic: str, custom_instructions: str = "") -> VideoScript:
        """
        Generates a viral short-form video script with scene breakdowns for the given topic.
        Returns a validated VideoScript Pydantic model.
        """
        prompt = f"""Generate a high-retention 30-50 second viral video script for YouTube Shorts / Instagram Reels.

TOPIC: {topic}
"""
        if custom_instructions:
            prompt += f"\nADDITIONAL INSTRUCTIONS: {custom_instructions}\n"

        fallback_models = [self.model_name, "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-pro-latest"]
        last_error = None

        for model_to_try in fallback_models:
            logger.info(f"Generating video script for topic: '{topic}' using model {model_to_try}...")
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_to_try,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SCRIPT_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_schema=VideoScript,
                            temperature=0.7,
                        )
                    )
                    raw_text = response.text.strip()
                    data = json.loads(raw_text)
                    video_script = VideoScript(**data)

                    # Sanitize all narrations and text to eliminate em-dashes
                    for scene in video_script.scenes:
                        scene.narration = sanitize_script_text(scene.narration)
                    video_script.hook = sanitize_script_text(video_script.hook)
                    video_script.call_to_action = sanitize_script_text(video_script.call_to_action)

                    # Save generated script for debugging & audit trail
                    output_file = TEMP_DIR / "last_generated_script.json"
                    output_file.write_text(json.dumps(video_script.model_dump(), indent=2), encoding="utf-8")
                    logger.info(f"Script generated successfully with {len(video_script.scenes)} scenes. Saved to {output_file}")
                    
                    return video_script
                except Exception as e:
                    last_error = e
                    logger.warning(f"Model {model_to_try} attempt {attempt+1}/3 encountered error: {e}. Retrying...")
                    import time
                    time.sleep(2)

        logger.error(f"All fallback models failed. Last error: {last_error}")
        raise last_error


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = LLMEngine()
    test_script = engine.generate_script("Why Neutron Stars Are the Scariest Objects in the Universe")
    print("\n" + "="*50)
    print(f"TITLE: {test_script.title}")
    print(f"HOOK: {test_script.hook}")
    print(f"TOTAL SCENES: {len(test_script.scenes)}")
    print("="*50)
    for s in test_script.scenes:
        print(f"[{s.scene_index}] Visual: '{s.visual_keyword}' | Narration: {s.narration}")
    print("="*50)
    print(f"CTA: {test_script.call_to_action}")
