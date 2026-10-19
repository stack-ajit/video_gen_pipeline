# 🎬 AI Video Content Generation Pipeline

> Autonomous AI pipeline for generating, editing, and publishing viral YouTube Shorts and Instagram Reels with real stock footage, 8K cinematic AI art, center-aligned captions, and ducked background music.

---

## 📖 Developer Documentation
For the full component breakdown, file map, and architectural guide, see:
👉 **[`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md)**

For the interactive catalog of all generated videos, see:
👉 **[`output/CATALOG.md`](output/CATALOG.md)**

---

## ⚡ Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
# Copy .env.example to .env and insert your API keys

# 3. Generate a video
python main.py --topic "The underwater waterfall hiding in the Indian Ocean" --force

# 4. Generate and publish everywhere
python main.py --topic "The Roko's Basilisk thought experiment that terrified Silicon Valley" --publish-all

# 5. Run automated scheduler
python scheduler.py
```
