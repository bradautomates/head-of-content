---
name: video-content-analyzer
description: |
  Analyze short-form videos with Gemini AI to extract hooks, content structure, and replicable patterns.
  Supports Instagram Reels, TikTok, and YouTube Shorts.

  Use when asked to:
  - Analyze video content for hooks and structure
  - Extract replicable formulas from viral videos
  - Understand why a video performed well
  - Get AI analysis of video content patterns

  Triggers: "analyze videos", "extract hooks", "video analysis", "analyze reels",
  "what makes this video work", "hook analysis", "content structure analysis"
---

# Video Content Analyzer

Analyze short-form videos with Gemini AI to extract hooks, content structure, delivery style, and CTA strategies.

## Prerequisites

- `GEMINI_API_KEY` environment variable
- `google-genai` and `requests` Python packages

## Usage

```bash
python3 .claude/skills/video-content-analyzer/scripts/analyze_videos.py \
  --input outliers.json \
  --output video-analysis.json \
  --platform instagram \
  --max-videos 5
```

### Parameters

| Arg | Description |
|-----|-------------|
| `--input`, `-i` | Input JSON file with outlier posts (required) |
| `--output`, `-o` | Output JSON file for results (required) |
| `--platform`, `-p` | Platform: `instagram`, `tiktok`, or `youtube` (default: instagram) |
| `--max-videos`, `-n` | Max videos to analyze (default: 5) |

## Input Format

Accepts outlier JSON from platform-specific research skills. Handles both formats:
- Direct list: `[{post1}, {post2}, ...]`
- Wrapped: `{"outliers": [{post1}, {post2}, ...]}`

The script automatically maps platform-specific fields:

| Platform | Video URL Fields | Caption | Username |
|----------|-----------------|---------|----------|
| Instagram | `videoUrl` | `caption` | `ownerUsername` |
| TikTok | `videoUrl`, `video_url`, `webVideoUrl` | `text`, `desc` | `authorUsername` |
| YouTube | `videoUrl`, `url` | `title` | `channelTitle` |

**TikTok Note**: The Apify TikTok Scraper returns `webVideoUrl` (the TikTok page URL) rather than a direct video download URL. Gemini will attempt to analyze from this page URL.

## Output

Returns JSON array with analysis for each video:

```json
[
  {
    "post_id": "ABC123",
    "username": "creator",
    "url": "https://...",
    "platform": "instagram",
    "likes": 50000,
    "comments": 1200,
    "views": 500000,
    "analysis": {
      "hook": {
        "technique": "pattern-interrupt",
        "opening_line": "Stop scrolling if you...",
        "attention_grab": "Creates urgency and targets specific audience",
        "replicable_formula": "Stop scrolling if you [pain point]"
      },
      "content_structure": {
        "format": "problem-solution",
        "sections": [...],
        "pacing": "fast",
        "retention_techniques": ["pattern interrupts", "text overlays"]
      },
      "delivery_style": {
        "speaking": "direct-to-camera",
        "energy": "high-energy",
        "text_overlays": true,
        "visual_style": "quick cuts with b-roll"
      },
      "cta_strategy": {
        "type": "follow",
        "cta_text": "Follow for more tips",
        "placement": "end"
      },
      "why_it_works": "..."
    }
  }
]
```

## Hook Techniques

The analyzer identifies these hook types:
- `pattern-interrupt` - Breaks expected patterns
- `question` - Opens with engaging question
- `bold-claim` - Makes surprising statement
- `story-tease` - Hints at compelling narrative
- `visual-shock` - Striking visual opening
- `curiosity-gap` - Creates information gap
- `direct-address` - Speaks to specific audience
- `controversial-take` - Polarizing opinion
- `relatable-pain` - Targets common struggle
- `transformation-preview` - Shows before/after

## Content Formats

- `problem-solution` - Present problem, offer fix
- `listicle` - Numbered tips/items
- `story` - Narrative arc
- `tutorial` - Step-by-step how-to
- `before-after` - Transformation reveal
- `day-in-life` - Lifestyle content
- `reaction` - Response to other content
- `hot-take` - Opinion piece
- `tool-demo` - Product/tool showcase
