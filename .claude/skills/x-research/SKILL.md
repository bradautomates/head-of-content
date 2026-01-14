---
name: x-research
description: |
  Research high-performing X/Twitter content from tracked accounts using Apify's Tweet Scraper V2.
  Identifies outlier tweets, trending topics, and content patterns to inform content strategy.

  Use when asked to:
  - Find trending tweets or content in a niche
  - Research what's performing on X/Twitter
  - Identify high-performing tweet patterns
  - Analyze competitors' X content
  - Generate content ideas from X trends
  - Run X/Twitter research

  Triggers: "x research", "twitter research", "find trending tweets", "analyze x accounts",
  "what's working on twitter", "content research x", "tweet analysis"
---

# X/Twitter Research

Research high-performing tweets from tracked accounts, identify outliers, and optionally analyze video content for hooks and structure.

## Prerequisites

- `APIFY_TOKEN` environment variable or in `.env`
- `GEMINI_API_KEY` environment variable or in `.env` (for video analysis)
- `apify-client` and `google-genai` Python packages
- Accounts configured in `.claude/context/x-accounts.md`

Verify setup:
```bash
python3 -c "
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from apify_client import ApifyClient
assert os.environ.get('APIFY_TOKEN'), 'APIFY_TOKEN not set'
" && echo "Prerequisites OK"
```

## Workflow

### 1. Create Run Folder

```bash
RUN_FOLDER="x-research/$(date +%Y-%m-%d_%H%M%S)" && mkdir -p "$RUN_FOLDER" && echo "$RUN_FOLDER"
```

### 2. Fetch Tweets

```bash
python3 .claude/skills/x-research/scripts/fetch_tweets.py \
  --days 30 \
  --max-items 100 \
  --output {RUN_FOLDER}/raw.json
```

Parameters:
- `--days`: Days back to search (default: 30)
- `--max-items`: Max tweets per account (default: 100)
- `--handles`: Override accounts file with specific handles

**API Limits:** Minimum 50 tweets per query required. Wait a couple minutes between runs.

### 3. Identify Outliers

```bash
python3 .claude/skills/x-research/scripts/analyze_posts.py \
  --input {RUN_FOLDER}/raw.json \
  --output {RUN_FOLDER}/outliers.json \
  --threshold 2.0
```

Output JSON contains:
- `total_posts`: Number of tweets analyzed
- `outlier_count`: Number of outliers found
- `topics`: Top hashtags, mentions, and keywords
- `content_patterns`: Analysis of what formats perform well
- `accounts`: List of accounts analyzed
- `outliers`: Array of outlier tweets with engagement metrics

### 4. Analyze Videos with AI (Optional)

If outliers contain video content:

```bash
python3 .claude/skills/video-content-analyzer/scripts/analyze_videos.py \
  --input {RUN_FOLDER}/outliers.json \
  --output {RUN_FOLDER}/video-analysis.json \
  --platform x \
  --max-videos 5
```

Note: X/Twitter is primarily text-based. Video analysis is optional and only useful when outliers contain video posts.

### 5. Generate Report

Read `{RUN_FOLDER}/outliers.json` (and optionally `{RUN_FOLDER}/video-analysis.json`), then generate `{RUN_FOLDER}/report.md`.

**Report Structure:**

```markdown
# X/Twitter Research Report

Generated: {date}

## Summary

- **Total tweets analyzed**: {total_posts}
- **Outlier tweets identified**: {outlier_count}
- **Outlier rate**: {percentage}%

## Top Performing Tweets (Outliers)

### 1. @{username} ({name})

> {tweet_text}

- **URL**: {url}
- **Date**: {created_at}
- **Engagement**: {likes} likes | {retweets} RTs | {replies} replies | {bookmarks} bookmarks
- **Engagement Score**: {score}
- **Engagement Rate**: {rate}%
- **Followers**: {followers}

[Repeat for top 15 outliers]

## Top Performing Hooks (if video analysis available)

### Hook 1: {technique} - @{username}
- **Opening**: "{opening_line}"
- **Why it works**: {attention_grab}
- **Replicable Formula**: {replicable_formula}
- [Watch Video]({url})

## Trending Topics

### Top Hashtags
[From outliers.json topics.hashtags]

### Top Keywords
[From outliers.json topics.keywords]

### Top Mentions
[From outliers.json topics.mentions]

## Content Patterns in Outliers

| Pattern | Count | Percentage |
|---------|-------|------------|
| Contains media | {count} | {pct}% |
| Contains external link | {count} | {pct}% |
| Thread format | {count} | {pct}% |
| Quote tweet | {count} | {pct}% |
| Asks a question | {count} | {pct}% |
| List/numbered format | {count} | {pct}% |
| Short (<100 chars) | {count} | {pct}% |
| Medium (100-200 chars) | {count} | {pct}% |
| Long (>200 chars) | {count} | {pct}% |

## Actionable Takeaways

[Synthesize patterns into 4-6 specific recommendations]

## Accounts Analyzed

[List accounts]
```

Focus on actionable insights. Content patterns and trending topics are key for X/Twitter research.

## Quick Reference

Full pipeline:
```bash
RUN_FOLDER="x-research/$(date +%Y-%m-%d_%H%M%S)" && mkdir -p "$RUN_FOLDER" && \
python3 .claude/skills/x-research/scripts/fetch_tweets.py -o "$RUN_FOLDER/raw.json" && \
python3 .claude/skills/x-research/scripts/analyze_posts.py -i "$RUN_FOLDER/raw.json" -o "$RUN_FOLDER/outliers.json"
```

With video analysis (optional):
```bash
python3 .claude/skills/video-content-analyzer/scripts/analyze_videos.py -i "$RUN_FOLDER/outliers.json" -o "$RUN_FOLDER/video-analysis.json" -p x
```

Then read JSON files and generate the report.

## Engagement Metrics

**Engagement Score (weighted):**
- Bookmarks: 4x (highest signal - saved for reference)
- Replies: 3x (active conversation)
- Retweets: 2x (amplification)
- Quotes: 2x (engagement with commentary)
- Likes: 1x (passive approval)

**Outlier Detection:** Tweets with engagement rate > mean + (threshold x std_dev)

**Engagement Rate:** (score / followers) x 100

## Output Location

All output goes to timestamped run folders:
```
x-research/
└── {YYYY-MM-DD_HHMMSS}/
    ├── raw.json            # Raw tweet data from Apify
    ├── outliers.json       # Outliers with metadata and topics
    ├── video-analysis.json # AI video analysis (optional)
    └── report.md           # Final report
```
