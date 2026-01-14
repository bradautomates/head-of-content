# Content Ideas Template

Use this template structure when generating `content-ideas.md`.

```markdown
# Content Ideas

Generated: {date}
Research window: Last 30 days

## Executive Summary

- **Total posts analyzed**: {sum across platforms}
- **Total outliers identified**: {sum}
- **Platforms covered**: X, Instagram, YouTube

---

## Top Content Ideas

### Priority Tier 1: Emerging Ideas (X-sourced)

Ideas from X that show high engagement but haven't saturated other platforms yet.

| Idea/Topic | X Engagement | Instagram Presence | YouTube Presence | Opportunity Score |
|------------|--------------|-------------------|------------------|-------------------|
| {topic} | {score} | Low/Medium/High | Low/Medium/High | {calculated} |

#### 1. {Topic Title}

- **Source Tweet**: @{username} - "{tweet excerpt}"
- **Why it's working**: {analysis}
- **Engagement proof**: {likes}L / {RTs}RT / {replies}R
- **Cross-platform potential**: {assessment}
- **Suggested angles**:
  - {angle 1}
  - {angle 2}
  - {angle 3}

[Repeat for top 10 X-sourced ideas]

---

### Priority Tier 2: Cross-Platform Winners

Ideas performing well across multiple platforms (validated at scale).

| Topic | X Performance | IG Performance | YT Performance |
|-------|--------------|----------------|----------------|
| {topic} | {outlier?} | {outlier?} | {outlier?} |

#### 1. {Topic Title}

- **Platforms validated**: X, Instagram, YouTube
- **Best performing format per platform**:
  - X: {format/style}
  - IG: {format/style}
  - YT: {format/style}
- **Combined engagement**: {total}
- **Why it resonates**: {analysis}

[Repeat for top 5 cross-platform ideas]

---

### Priority Tier 3: Platform-Specific Hits

Strong performers that work best on one platform.

#### Instagram-Native Ideas
[List top 3 with context]

#### YouTube-Native Ideas
[List top 3 with context]

---

## Trending Topics & Hashtags

### Cross-Platform Trending

| Topic | X Rank | IG Rank | YT Rank |
|-------|--------|---------|---------|
[Merged from all platforms]

### Platform-Specific Trends

#### X/Twitter
{Top hashtags and keywords from outliers}

#### Instagram
{Top hashtags and keywords from outliers}

#### YouTube
{Top keywords and topics from outliers}

---

## Content Calendar Suggestions

Based on identified topics, here's a suggested 2-week content calendar:

| Day | Platform | Content Idea | Format | Hook Formula |
|-----|----------|--------------|--------|--------------|
| Mon | X | {idea} | Thread | {hook} |
| Tue | IG Reels | {idea} | Tutorial | {hook} |
| Wed | YouTube | {idea} | Short | {hook} |
[Continue for 2 weeks]

---

## Data Sources

- X Research: {run_folder} ({outlier_count} outliers from {total} posts)
- Instagram Research: {run_folder} ({outlier_count} outliers from {total} posts)
- YouTube Research: {run_folder} ({outlier_count} outliers from {total} videos)
```

## Opportunity Score Calculation

For X-sourced ideas:

```
opportunity_score = (x_engagement × 1.5) / (instagram_saturation + youtube_saturation + 1)
```

Where:
- `x_engagement` = normalized engagement rate on X (0-10 scale based on outlier percentile)
- `instagram_saturation`:
  - 0 = not present in Instagram outliers
  - 0.5 = low (mentioned in 1-2 outliers)
  - 1.0 = medium (3-5 outliers)
  - 1.5 = high (6+ outliers)
- `youtube_saturation` = same scale

Higher score = more opportunity (high engagement, low saturation elsewhere).

## Cross-Platform Topic Matching

1. Extract all keywords/hashtags from each platform's outliers
2. Normalize: lowercase, remove # and @, stem common variations
3. Find terms appearing in 2+ platforms
4. Rank by combined engagement across platforms
