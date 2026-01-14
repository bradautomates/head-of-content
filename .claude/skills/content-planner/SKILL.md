---
name: content-planner
description: |
  Orchestrate comprehensive content research across X, Instagram, YouTube, and TikTok platforms.
  Runs all research skills in parallel via subagents, then aggregates findings into
  actionable content plans and platform-specific intelligence playbooks.

  Use when asked to:
  - Create a content plan for social media
  - Research content across all platforms
  - Generate content ideas from multiple sources
  - Build a content strategy playbook
  - Aggregate research from X, Instagram, YouTube, TikTok
  - Run comprehensive content research
  - Create platform playbooks

  Triggers: "content plan", "content planner", "research all platforms",
  "comprehensive research", "content strategy", "multi-platform research",
  "create playbooks", "aggregate research"
---

# Content Planner

Orchestrate parallel research across X, Instagram, YouTube, and TikTok, then aggregate findings into content ideas and platform-specific playbooks.

## Prerequisites

Same as individual research skills:
- `APIFY_TOKEN` for X, Instagram, and TikTok research
- `TUBELAB_API_KEY` for YouTube research
- `GEMINI_API_KEY` for video analysis
- Accounts configured in `.claude/context/` for each platform

**CRITICAL - Subagent Environment Setup**: Each subagent must load environment variables from the `.env` file in the `head-of-marketing` working directory before executing any API calls:
```bash
export $(cat .env | grep -v '^#' | xargs)
```

## Workflow

### 1. Read User Context

Read all files in `.claude/context/` to understand the user's niche, target audience, and accounts to research. Pass this context to each subagent.

### 2. Create Master Run Folder

```bash
RUN_FOLDER="content-plans/$(date +%Y-%m-%d_%H%M%S)" && mkdir -p "$RUN_FOLDER" && echo "$RUN_FOLDER"
```

### 3. Launch Research Subagents in Parallel

Use the Task tool to launch 4 subagents simultaneously:

**Subagent 1 - X Research:**
```
Execute the x-research skill:
1. Create run folder in x-research/
2. Fetch tweets (30 days, 100 max per account)
3. Analyze for outliers
4. Run video analysis if video content found
5. Generate report

Return: The run folder path and a JSON summary with:
- run_folder: path to the run folder
- total_posts: number analyzed
- outlier_count: outliers found
- top_topics: top 5 hashtags/keywords
```

**Subagent 2 - Instagram Research:**
```
Execute the instagram-research skill:
1. Create run folder in instagram-research/
2. Fetch reels (30 days, 50 per account)
3. Analyze for outliers
4. Run video analysis on top 5
5. Generate report

Return: The run folder path and a JSON summary with:
- run_folder: path to the run folder
- total_posts: number analyzed
- outlier_count: outliers found
- top_topics: top 5 hashtags/keywords
```

**Subagent 3 - YouTube Research:**
```
Execute the youtube-research skill:
1. Read channel context from .claude/context/youtube-channel.md
2. Analyze channel for keywords
3. Search for outliers
4. Filter to top 3 relevant videos
5. Run video analysis
6. Generate report

Return: The run folder path and a JSON summary with:
- run_folder: path to the run folder
- total_videos: number analyzed
- outlier_count: outliers found
- top_topics: top 5 keywords
```

**Subagent 4 - TikTok Research:**
```
Execute the tiktok-research skill:
1. Create run folder in tiktok-research/
2. Fetch videos (30 days, 50 per account)
3. Analyze for outliers
4. Run video analysis on top 5
5. Generate report

Return: The run folder path and a JSON summary with:
- run_folder: path to the run folder
- total_videos: number analyzed
- outlier_count: outliers found
- top_topics: top 5 hashtags/sounds/keywords
```

### 4. Collect Research Results

After all subagents complete, read from each platform's latest run folder:

```
x-research/{latest}/
├── outliers.json
└── video-analysis.json (if exists)

instagram-research/{latest}/
├── outliers.json
└── video-analysis.json

youtube-research/{latest}/
├── outliers.json
└── video-analysis.json

tiktok-research/{latest}/
├── outliers.json
└── video-analysis.json
```

### 5. Generate Content Ideas

Read `references/content-ideas-template.md` for the full template structure.

Key aggregation tasks:
1. **Extract topics** from each platform's outliers
2. **Cross-reference** to find topics appearing on multiple platforms
3. **Identify X-sourced emerging ideas** (high X engagement, low presence elsewhere)
4. **Calculate opportunity scores** for X ideas:
   ```
   opportunity_score = (x_engagement × 1.5) / (instagram_saturation + youtube_saturation + tiktok_saturation + 1)
   ```
   - `instagram_saturation`: 0 (not present), 0.5 (low), 1 (medium), 1.5 (high)
   - `youtube_saturation`: same scale
   - `tiktok_saturation`: same scale
5. **Generate 2-week calendar** with platform-specific content suggestions

Write to: `{RUN_FOLDER}/content-ideas.md`

### 6. Generate Platform Playbooks

For each platform, read `references/playbook-template.md` and generate:

- `{RUN_FOLDER}/x-playbook.md`
- `{RUN_FOLDER}/instagram-playbook.md`
- `{RUN_FOLDER}/youtube-playbook.md`
- `{RUN_FOLDER}/tiktok-playbook.md`

Each playbook extracts from the platform's research:
- Winning hooks with replicable formulas (from video-analysis.json)
- Format analysis and content patterns
- Content structure breakdowns
- CTA strategies
- Trending topics and hashtags
- Top 15 outliers with analysis
- Actionable takeaways

### 7. Present Summary

Output to user:
- Total content analyzed across all platforms
- Number of outliers identified per platform
- Key cross-platform insights (2-3 bullets)
- Top 3 emerging ideas from X
- Links to all generated files

## Output Structure

```
content-plans/
└── {YYYY-MM-DD_HHMMSS}/
    ├── content-ideas.md          # Cross-platform ideas (X-primary)
    ├── x-playbook.md             # X/Twitter intelligence playbook
    ├── instagram-playbook.md     # Instagram intelligence playbook
    ├── youtube-playbook.md       # YouTube intelligence playbook
    └── tiktok-playbook.md        # TikTok intelligence playbook
```

## Cross-Platform Topic Matching

To identify cross-platform winners:

1. Extract keywords/hashtags from each platform's outliers
2. Normalize terms (lowercase, remove # and @)
3. Find intersection of high-frequency terms
4. Score by combined engagement across platforms

## Quick Reference

Full orchestration:
1. Create master run folder
2. Launch 4 research subagents in parallel (Task tool with 4 invocations)
3. Wait for all subagents to complete
4. Read all outliers.json and video-analysis.json files
5. Generate content-ideas.md using cross-platform analysis
6. Generate 4 platform playbooks
7. Present summary to user
