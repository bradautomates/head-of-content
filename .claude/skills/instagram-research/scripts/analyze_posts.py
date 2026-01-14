#!/usr/bin/env python3
"""
Identify outlier Instagram posts/reels based on engagement metrics.
Outputs JSON with outliers and metadata for report generation.
"""

import json
import argparse
import statistics
from datetime import datetime
from pathlib import Path
from collections import Counter
import re


def load_posts(input_path: str) -> list[dict]:
    """Load posts from JSON file."""
    with open(input_path, 'r') as f:
        return json.load(f)


def calculate_engagement_score(post: dict) -> float:
    """
    Calculate weighted engagement score.
    - Comments (3x): Active engagement
    - Likes (1x): Passive approval
    - Video views (0.1x): Weighted lower due to auto-play
    """
    likes = post.get('likesCount', 0) or 0
    comments = post.get('commentsCount', 0) or 0
    video_views = post.get('videoViewCount', 0) or post.get('videoPlayCount', 0) or 0
    return likes + (3 * comments) + (0.1 * video_views)


def calculate_engagement_rate(post: dict) -> float:
    """Calculate engagement rate relative to follower count."""
    followers = post.get('ownerFollowersCount', 0) or 0
    engagement = calculate_engagement_score(post)
    if followers == 0:
        return engagement
    return (engagement / followers) * 100


def identify_outliers(posts: list[dict], threshold_multiplier: float = 2.0) -> list[dict]:
    """
    Identify outlier posts with engagement rate > mean + (threshold × std_dev).
    """
    if not posts:
        return []

    for post in posts:
        post['_engagement_score'] = calculate_engagement_score(post)
        post['_engagement_rate'] = calculate_engagement_rate(post)

    rates = [p['_engagement_rate'] for p in posts]
    if len(rates) < 2:
        return posts

    mean_rate = statistics.mean(rates)
    std_dev = statistics.stdev(rates) if len(rates) > 1 else 0
    threshold = mean_rate + (threshold_multiplier * std_dev)

    outliers = [p for p in posts if p['_engagement_rate'] > threshold]
    outliers.sort(key=lambda x: x['_engagement_score'], reverse=True)
    return outliers


def extract_topics(posts: list[dict]) -> dict:
    """Extract trending hashtags, mentions, and keywords."""
    hashtags = Counter()
    keywords = Counter()

    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
        'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
        'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but',
        'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by',
        'for', 'with', 'about', 'against', 'between', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up',
        'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further',
        'then', 'once', 'here', 'there', 'your', 'my', 'his', 'her', 'its',
        'our', 'their', 'get', 'got', 'like', 'dont', 'im', 'ive', 'youre',
        'https', 'http', 'amp', 'link', 'bio', 'comment', 'follow', 'check'
    }

    for post in posts:
        caption = post.get('caption', '') or ''

        # Hashtags
        post_hashtags = post.get('hashtags', []) or []
        if isinstance(post_hashtags, list):
            hashtags.update([h.lower().lstrip('#') for h in post_hashtags])
        hashtags.update(re.findall(r'#(\w+)', caption.lower()))

        # Keywords
        text_clean = re.sub(r'https?://\S+', '', caption)
        text_clean = re.sub(r'[@#]\w+', '', text_clean)
        text_words = re.findall(r'\b[a-zA-Z]{4,}\b', text_clean.lower())
        keywords.update([w for w in text_words if w not in stop_words])

    return {
        'hashtags': hashtags.most_common(20),
        'keywords': keywords.most_common(30)
    }


def main():
    parser = argparse.ArgumentParser(description='Identify Instagram outliers')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file')
    parser.add_argument('--threshold', '-t', type=float, default=2.0,
                        help='Outlier threshold multiplier (default: 2.0)')

    args = parser.parse_args()

    print(f"Loading posts from: {args.input}")
    posts = load_posts(args.input)
    print(f"Loaded {len(posts)} posts/reels")

    print(f"Identifying outliers (threshold: {args.threshold}x std dev)...")
    outliers = identify_outliers(posts, args.threshold)
    print(f"Found {len(outliers)} outlier posts")

    print("Extracting topics...")
    topics = extract_topics(posts)

    # Build output with metadata
    output = {
        'generated': datetime.now().isoformat(),
        'total_posts': len(posts),
        'outlier_count': len(outliers),
        'threshold': args.threshold,
        'topics': topics,
        'accounts': list(set(p.get('ownerUsername', '') for p in posts if p.get('ownerUsername'))),
        'outliers': outliers
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Outliers saved to: {args.output}")
    print(f"- {len(outliers)} outliers identified")
    if topics['hashtags']:
        print(f"- Top hashtag: #{topics['hashtags'][0][0]}")
    if topics['keywords']:
        print(f"- Top keyword: {topics['keywords'][0][0]}")


if __name__ == '__main__':
    main()
