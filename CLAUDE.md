# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Claude Code skills repository for social media content research and marketing automation. It contains skills that research high-performing content across X/Twitter, Instagram, YouTube, and TikTok, then analyze videos with AI to extract replicable hooks and patterns.

## Environment Setup

Required environment variables (configure in `.env`):
- `APIFY_TOKEN` - For X, Instagram, and TikTok scraping (get from https://console.apify.com/account/integrations)
- `TUBELAB_API_KEY` - For YouTube outlier detection (get from https://tubelab.net/settings/api)
- `GEMINI_API_KEY` - For video analysis and thumbnail generation (get from https://aistudio.google.com/api-keys)

Python packages needed: `apify-client`, `google-genai`, `requests`, `python-dotenv`, `opencv-python-headless`, `mediapipe`, `Pillow`, `numpy`

Load env vars in subagents:
```bash
export $(cat .env | grep -v '^#' | xargs)
```

## Skills Architecture

All skills live in `.claude/skills/` and follow a consistent pattern:

### Research Skills (platform-specific)
Each creates timestamped run folders with `raw.json` → `outliers.json` → `video-analysis.json` → `report.md`:

- **x-research**: Fetches tweets via Apify, identifies engagement outliers
- **instagram-research**: Fetches reels via Apify, identifies outliers, analyzes top 5 videos
- **youtube-research**: Uses TubeLab API for outlier detection, analyzes top 3 relevant videos
- **tiktok-research**: Fetches TikToks via Apify, identifies outliers, analyzes top 5 videos

### Support Skills
- **video-content-analyzer**: Gemini AI analysis of video hooks, structure, and CTAs. Used by all research skills.
- **content-planner**: Orchestrates all 4 research skills in parallel, aggregates into content ideas and platform playbooks

## Context Files

Configure research targets in `.claude/context/`:
- `x-accounts.md` - X/Twitter handles to monitor
- `instagram-accounts.md` - Instagram accounts to track
- `tiktok-accounts.md` - TikTok accounts to track
- `youtube-channel.md` - Your channel info and niche for relevance filtering
- `reference_images/` - Face photos for thumbnail generation (pose-encoded filenames)

## Output Structure

Research outputs go to platform-specific timestamped folders:
```
{platform}-research/{YYYY-MM-DD_HHMMSS}/
├── raw.json            # Raw API data
├── outliers.json       # Outliers with engagement metrics
├── video-analysis.json # AI-extracted hooks and patterns
└── report.md           # Human-readable report

content-plans/{YYYY-MM-DD_HHMMSS}/
├── content-ideas.md    # Cross-platform aggregated ideas
└── {platform}-playbook.md  # Platform-specific intelligence
```

## Key Commands

Run individual research:
```bash
python3 .claude/skills/{platform}-research/scripts/fetch_{platform}.py --output {folder}/raw.json
python3 .claude/skills/{platform}-research/scripts/analyze_posts.py --input {folder}/raw.json --output {folder}/outliers.json
python3 .claude/skills/video-content-analyzer/scripts/analyze_videos.py --input {folder}/outliers.json --output {folder}/video-analysis.json --platform {platform}
```

YouTube research (different pattern):
```bash
python3 .claude/skills/youtube-research/scripts/get_channel_videos.py CHANNEL_ID --format summary
python3 .claude/skills/youtube-research/scripts/find_outliers.py --keywords k1 k2 k3 k4 --adjacent-keywords a1 a2 a3 a4 --output-dir {folder}
```

## Engagement Scoring

- **X**: Bookmarks 4x, Replies 3x, Retweets 2x, Quotes 2x, Likes 1x
- **Instagram/TikTok**: Likes + 3×Comments + engagement bonuses for shares/saves/views
- **YouTube**: zScore × recency_boost (5%/day decay)

Outlier threshold: engagement rate > mean + (2.0 × std_dev)
