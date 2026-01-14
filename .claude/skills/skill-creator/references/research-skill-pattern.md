# Research Skill Core Implementation Pattern

This document defines the canonical implementation pattern for social media research skills. All research skills should follow this structure for consistency and maintainability.

## Pattern Overview

Research skills follow a **3-stage pipeline**:

1. **Fetch** - Retrieve raw content from platform via API
2. **Analyze** - Identify outliers using engagement metrics
3. **Report** - Generate actionable report with AI-analyzed hooks (optional)

```
┌─────────┐     ┌─────────┐     ┌──────────────────┐     ┌─────────┐
│  Fetch  │ ──▶ │ Analyze │ ──▶ │ Video Analysis   │ ──▶ │ Report  │
│ Script  │     │ Script  │     │ (video-content-  │     │ (Claude │
│         │     │         │     │  analyzer skill) │     │ generates)
└─────────┘     └─────────┘     └──────────────────┘     └─────────┘
   raw.json      outliers.json   video-analysis.json      report.md
```

---

## Directory Structure

```
{platform}-research/
├── SKILL.md
└── scripts/
    ├── fetch_{platform}.py      # Stage 1: Fetch content
    └── analyze_posts.py         # Stage 2: Identify outliers
```

Video analysis is handled by the shared `video-content-analyzer` skill.

---

## SKILL.md Structure

### Frontmatter

```yaml
---
name: {platform}-research
description: |
  Research high-performing {Platform} content from tracked accounts using {API provider}.
  Identifies outlier content, analyzes top {N} videos with AI, and generates reports with actionable hook formulas.

  Use when asked to:
  - Find trending {Platform} content in a niche
  - Research what's performing on {Platform}
  - Identify high-performing {content type} patterns
  - Analyze competitors' {Platform} content
  - Generate content ideas from {Platform} trends
  - Run {Platform} research
  - Find viral {content type}
  - Analyze hooks and content structure

  Triggers: "{platform} research", "find trending {content}", "analyze {platform} accounts",
  "what's working on {platform}", "content research {platform}", "{content} analysis", "{platform} trends"
---
```

### Body Sections

1. **Title** - `# {Platform} Research`
2. **Description** - One-line summary
3. **Prerequisites** - Required env vars, packages, account files
4. **Workflow** - Numbered steps (see below)
5. **Quick Reference** - One-liner pipeline command
6. **Engagement Metrics** - Score formula and outlier detection
7. **Platform-Specific Fields** (optional) - API field mappings

---

## Workflow Steps (Standard)

### Step 1: Create Run Folder

```bash
RUN_FOLDER="{platform}-research/$(date +%Y-%m-%d_%H%M%S)" && mkdir -p "$RUN_FOLDER" && echo "$RUN_FOLDER"
```

### Step 2: Fetch Content

```bash
python3 .claude/skills/{platform}-research/scripts/fetch_{platform}.py \
  --days 30 \
  --limit 50 \
  --output {RUN_FOLDER}/raw.json
```

**Standard Parameters:**
| Parameter | Description | Default |
|-----------|-------------|---------|
| `--days` | Days back to search | 30 |
| `--limit` | Max items per account | 50 |
| `--output` | Output JSON path | required |
| `--accounts-file` | Path to accounts markdown | `.claude/context/{platform}-accounts.md` |

### Step 3: Identify Outliers

```bash
python3 .claude/skills/{platform}-research/scripts/analyze_posts.py \
  --input {RUN_FOLDER}/raw.json \
  --output {RUN_FOLDER}/outliers.json \
  --threshold 2.0
```

**Standard Parameters:**
| Parameter | Description | Default |
|-----------|-------------|---------|
| `--input` | Raw JSON from fetch | required |
| `--output` | Outliers JSON output | required |
| `--threshold` | Outlier std dev multiplier | 2.0 |

**Output JSON Schema:**
```json
{
  "generated": "ISO timestamp",
  "total_posts": 150,
  "outlier_count": 12,
  "threshold": 2.0,
  "topics": {
    "hashtags": [["tag", count], ...],
    "keywords": [["word", count], ...]
  },
  "accounts": ["username1", "username2"],
  "outliers": [/* post objects with _engagement_score, _engagement_rate */]
}
```

### Step 4: Analyze Top Videos with AI

```bash
python3 .claude/skills/video-content-analyzer/scripts/analyze_videos.py \
  --input {RUN_FOLDER}/outliers.json \
  --output {RUN_FOLDER}/video-analysis.json \
  --platform {platform} \
  --max-videos 5
```

### Step 5: Generate Report

Claude reads `outliers.json` and `video-analysis.json`, then writes `report.md`.

---

## Report Structure (Standard)

```markdown
# {Platform} Research Report

Generated: {date}

## Top Performing Hooks

Ranked by engagement. Use these formulas for your content.

### Hook 1: {technique} - @{username}
- **Opening**: "{opening_line}"
- **Why it works**: {attention_grab}
- **Replicable Formula**: {replicable_formula}
- **Engagement**: {likes} likes, {comments} comments, {views} views
- [Watch Video]({url})

[Repeat for each analyzed video]

## Content Structure Patterns

| Video | Format | Pacing | Key Retention Techniques |
|-------|--------|--------|--------------------------|
| @username | {format} | {pacing} | {techniques} |

## CTA Strategies

| Video | CTA Type | CTA Text | Placement |
|-------|----------|----------|-----------|
| @username | {type} | "{cta_text}" | {placement} |

## All Outliers

| Rank | Username | Likes | Comments | Views | Engagement Rate |
|------|----------|-------|----------|-------|-----------------|
[List all outliers with metrics and links]

## Trending Topics

### Top Hashtags
[From outliers.json topics.hashtags]

### Top Keywords
[From outliers.json topics.keywords]

## Actionable Takeaways

[Synthesize patterns into 4-6 specific recommendations]

## Accounts Analyzed
[List accounts]
```

---

## Script Implementation Patterns

### Fetch Script (`fetch_{platform}.py`)

```python
#!/usr/bin/env python3
"""
Fetch {Platform} content from specified accounts using {API provider}.
Requires {API_TOKEN} environment variable (or in .env file).
"""

# Standard imports
import os, sys, json, argparse
from datetime import datetime, timedelta
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API client import with error handling
try:
    from api_client import Client
except ImportError:
    print("Error: api-client not installed. Run: pip install api-client")
    sys.exit(1)


def parse_accounts_file(accounts_path: str) -> list[str]:
    """Parse {platform}-accounts.md and extract usernames."""
    usernames = []
    with open(accounts_path, 'r') as f:
        in_table = False
        for line in f:
            line = line.strip()
            if line.startswith('| Username') or line.startswith('| Handle'):
                in_table = True
                continue
            if line.startswith('|---'):
                continue
            if in_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    username = parts[1]
                    if username.startswith('@') and not username.startswith('@example'):
                        usernames.append(username.lstrip('@'))
    return usernames


def fetch_content(usernames: list[str], ...) -> list[dict]:
    """Fetch content from API."""
    token = os.environ.get('{API_TOKEN}')
    if not token:
        print("Error: {API_TOKEN} environment variable not set")
        sys.exit(1)

    # ... API call logic ...

    return items


def main():
    parser = argparse.ArgumentParser(description='Fetch {Platform} content')
    parser.add_argument('--accounts-file', '-a',
                        default='.claude/context/{platform}-accounts.md')
    parser.add_argument('--usernames', '-u', nargs='+',
                        help='Override accounts file')
    parser.add_argument('--days', '-d', type=int, default=30)
    parser.add_argument('--limit', '-l', type=int, default=50)
    parser.add_argument('--output', '-o', required=True)

    args = parser.parse_args()

    # Parse accounts
    if args.usernames:
        usernames = [u.lstrip('@') for u in args.usernames]
    else:
        usernames = parse_accounts_file(args.accounts_file)

    # Fetch and save
    items = fetch_content(usernames, args.days, args.limit)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(items, f, indent=2, default=str)

    print(f"Fetched {len(items)} items")
    print("Use analyze_posts.py to identify outliers.")


if __name__ == '__main__':
    main()
```

### Analyze Script (`analyze_posts.py`)

```python
#!/usr/bin/env python3
"""
Identify outlier {Platform} posts based on engagement metrics.
Outputs JSON with outliers and metadata for report generation.
"""

import json, argparse, statistics, re
from datetime import datetime
from pathlib import Path
from collections import Counter


def calculate_engagement_score(post: dict) -> float:
    """Calculate weighted engagement score."""
    # Platform-specific weights
    likes = post.get('likesCount', 0) or 0
    comments = post.get('commentsCount', 0) or 0
    # ... additional metrics ...
    return likes + (3 * comments)  # Adjust weights per platform


def calculate_engagement_rate(post: dict) -> float:
    """Calculate engagement rate relative to follower count."""
    followers = post.get('followerCount', 0) or 1
    return (calculate_engagement_score(post) / followers) * 100


def identify_outliers(posts: list[dict], threshold: float = 2.0) -> list[dict]:
    """Identify outlier posts with engagement rate > mean + (threshold × std_dev)."""
    for post in posts:
        post['_engagement_score'] = calculate_engagement_score(post)
        post['_engagement_rate'] = calculate_engagement_rate(post)

    rates = [p['_engagement_rate'] for p in posts]
    if len(rates) < 2:
        return posts

    mean_rate = statistics.mean(rates)
    std_dev = statistics.stdev(rates)
    threshold_value = mean_rate + (threshold * std_dev)

    outliers = [p for p in posts if p['_engagement_rate'] > threshold_value]
    outliers.sort(key=lambda x: x['_engagement_score'], reverse=True)
    return outliers


def extract_topics(posts: list[dict]) -> dict:
    """Extract trending hashtags and keywords."""
    hashtags = Counter()
    keywords = Counter()
    # ... extraction logic ...
    return {
        'hashtags': hashtags.most_common(20),
        'keywords': keywords.most_common(30)
    }


def main():
    parser = argparse.ArgumentParser(description='Identify outliers')
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=True)
    parser.add_argument('--threshold', '-t', type=float, default=2.0)

    args = parser.parse_args()

    posts = json.load(open(args.input))
    outliers = identify_outliers(posts, args.threshold)
    topics = extract_topics(posts)

    output = {
        'generated': datetime.now().isoformat(),
        'total_posts': len(posts),
        'outlier_count': len(outliers),
        'threshold': args.threshold,
        'topics': topics,
        'accounts': list(set(p.get('username', '') for p in posts)),
        'outliers': outliers
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2, default=str)


if __name__ == '__main__':
    main()
```

---

## Engagement Score Formulas by Platform

### X/Twitter
```
score = likes + (2 × retweets) + (3 × replies) + (2 × quotes) + (4 × bookmarks)
```

### Instagram
```
score = likes + (3 × comments) + (0.1 × views)
```

### TikTok
```
score = likes + (3 × comments) + (2 × shares) + (2 × saves) + (0.05 × views)
```

### YouTube
Videos ranked by `zScore × recency_boost` where:
- zScore: How much video outperforms channel average
- recency_boost: 1.0 for today, decays 5%/day (min 0.3×)

---

## Outlier Detection Formula

All platforms use the same statistical outlier detection:

```
outlier_threshold = mean(engagement_rate) + (threshold × std_dev(engagement_rate))
```

Where:
- `engagement_rate = (engagement_score / followers) × 100`
- `threshold` = 2.0 (default, configurable)

---

## Accounts File Format

All skills read accounts from `.claude/context/{platform}-accounts.md`:

```markdown
# {Platform} Accounts

| Handle | Niche | Notes |
|--------|-------|-------|
| @username1 | Category | Description |
| @username2 | Category | Description |
```

---

## Key Design Principles

1. **Separation of concerns** - Fetch and analyze are separate scripts
2. **Normalized output** - Analyze script outputs consistent JSON schema
3. **Shared video analysis** - Use `video-content-analyzer` skill, don't duplicate
4. **Claude generates report** - Scripts output structured data; Claude synthesizes
5. **Engagement rate over raw score** - Normalize by followers for fair comparison
6. **Configurable threshold** - Default 2.0 std dev, adjustable per run
