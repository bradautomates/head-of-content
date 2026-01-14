#!/usr/bin/env python3
"""
Find top outlier YouTube videos using TubeLab API.
Runs two searches:
1. Direct keywords (min 5K views) - videos in your exact niche
2. Adjacent keywords (min 10K views) - videos your audience also watches

Downloads thumbnails and generates a markdown report.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


def load_env_file():
    """Load .env file from project root."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        env_path = current / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        os.environ.setdefault(key.strip(), value)
            return
        current = current.parent


def get_api_key():
    """Get TubeLab API key from environment."""
    load_env_file()
    api_key = os.environ.get("TUBELAB_API_KEY")
    if not api_key:
        print("Error: TUBELAB_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key from https://tubelab.net/settings/api", file=sys.stderr)
        sys.exit(1)
    return api_key


def search_outliers(queries: list[str], api_key: str, days_back: int = 30, min_views: int = 5000) -> list[dict]:
    """
    Search for outlier videos using TubeLab API.

    Args:
        queries: List of search keywords (up to 4)
        api_key: TubeLab API key
        days_back: How many days back to search
        min_views: Minimum view count filter

    Returns:
        List of video objects from API
    """
    base_url = "https://public-api.tubelab.net/v1/search/outliers"

    # Calculate date range
    published_after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")

    # Build query params - TubeLab accepts multiple query params
    params = [
        ("type", "video"),
        ("language", "en"),
        ("publishedAtFrom", published_after),
        ("viewCountFrom", str(min_views)),
        ("size", "20"),
        ("sortBy", "zScore"),
        ("sortOrder", "desc"),
    ]

    # Add each query as a separate parameter
    for q in queries[:4]:  # Max 4 keywords
        params.append(("query", q))

    url = f"{base_url}?{urlencode(params)}"

    req = Request(url)
    req.add_header("Authorization", f"Api-Key {api_key}")
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("hits", [])

    except HTTPError as e:
        print(f"API error: {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("Invalid API key. Check your TUBELAB_API_KEY.", file=sys.stderr)
            sys.exit(1)
        elif e.code == 429:
            print("Rate limit exceeded. Wait and try again.", file=sys.stderr)
            sys.exit(1)
        return []
    except URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return []


def score_video(video: dict) -> float:
    """
    Calculate a composite score for ranking videos.
    Balances outlier performance with recency.

    Score formula: zScore * recency_boost
    - zScore: How much video outperforms channel average
    - recency_boost: 1.0 for today, decays by 5% per day
    """
    stats = video.get("statistics", {})
    z_score = stats.get("zScore", 0) or 0

    # Parse publish date
    snippet = video.get("snippet", {})
    published_at = snippet.get("publishedAt", "")

    recency_boost = 1.0
    if published_at:
        try:
            pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            days_old = (datetime.now(pub_date.tzinfo) - pub_date).days
            # 5% decay per day, minimum 0.3x
            recency_boost = max(0.3, 1.0 - (days_old * 0.05))
        except (ValueError, TypeError):
            pass

    return z_score * recency_boost


def download_thumbnail(video: dict, output_dir: Path):
    """Download video thumbnail to output directory."""
    video_id = video.get("id")
    snippet = video.get("snippet", {})
    thumbnails = snippet.get("thumbnails", {})

    # Prefer high quality, fall back to medium, then default
    thumb_url = None
    for quality in ["high", "medium", "default"]:
        if quality in thumbnails and thumbnails[quality].get("url"):
            thumb_url = thumbnails[quality]["url"]
            break

    if not thumb_url or not video_id:
        return None

    output_path = output_dir / f"{video_id}.jpg"

    try:
        req = Request(thumb_url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urlopen(req, timeout=15) as response:
            output_path.write_bytes(response.read())

        return str(output_path)
    except (HTTPError, URLError) as e:
        print(f"Failed to download thumbnail for {video_id}: {e}", file=sys.stderr)
        return None


def fetch_transcript(video_id: str, api_key: str, output_dir: Path) -> str | None:
    """
    Fetch video transcript using TubeLab API.

    Args:
        video_id: YouTube video ID
        api_key: TubeLab API key
        output_dir: Directory to save transcript file

    Returns:
        Path to saved transcript file, or None if failed
    """
    url = f"https://public-api.tubelab.net/v1/video/transcript/{video_id}"

    req = Request(url)
    req.add_header("Authorization", f"Api-Key {api_key}")
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Extract transcript text from response
        # API returns segments with text, start time, duration
        segments = data.get("segments", [])
        if not segments:
            return None

        # Format transcript with timestamps
        transcript_lines = []
        for seg in segments:
            start = seg.get("start", 0)
            text = seg.get("text", "").strip()
            if text:
                # Format timestamp as MM:SS
                minutes = int(start // 60)
                seconds = int(start % 60)
                transcript_lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")

        if not transcript_lines:
            return None

        output_path = output_dir / f"{video_id}.txt"
        output_path.write_text("\n".join(transcript_lines), encoding="utf-8")
        return str(output_path)

    except HTTPError as e:
        if e.code == 404:
            # Transcript not available for this video
            pass
        else:
            print(f"Failed to fetch transcript for {video_id}: {e.code}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"Network error fetching transcript for {video_id}: {e.reason}", file=sys.stderr)
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing transcript for {video_id}: {e}", file=sys.stderr)
        return None


def format_number(n: int) -> str:
    """Format number with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def generate_report(
    direct_videos: list[dict],
    adjacent_videos: list[dict],
    output_dir: Path,
    thumbnail_dir: Path,
    keywords: list[str],
    adjacent_keywords: list[str]
) -> str:
    """Generate markdown report of top videos."""
    report_lines = [
        f"# YouTube Outlier Research Report",
        f"",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"---",
        f"",
        f"## Direct Niche Outliers",
        f"",
        f"**Keywords:** {', '.join(keywords)}",
        f"**Filter:** 5K+ views, last 30 days",
        f"",
    ]

    def add_video_section(videos: list[dict], start_num: int = 1) -> int:
        num = start_num
        for video in videos:
            video_id = video.get("id", "")
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            channel = snippet.get("channel", {})

            title = snippet.get("title", "Untitled")
            channel_title = channel.get("title", "Unknown")
            channel_subs = channel.get("subscribersCount", 0)
            views = stats.get("viewCount", 0)
            likes = stats.get("likeCount", 0)
            z_score = stats.get("zScore", 0) or 0
            published = snippet.get("publishedAt", "")[:10]

            # Calculate performance ratio
            avg_views = channel.get("averageViews", views)
            ratio = views / avg_views if avg_views > 0 else 1.0

            thumb_path = thumbnail_dir / f"{video_id}.jpg"
            thumb_ref = f"thumbnails/{video_id}.jpg" if thumb_path.exists() else ""

            report_lines.extend([
                f"### {num}. {title}",
                f"",
                f"**Channel:** {channel_title} ({format_number(channel_subs)} subs)",
                f"**Published:** {published}",
                f"**Views:** {format_number(views)} | **Likes:** {format_number(likes)}",
                f"**Outlier Score (zScore):** {z_score:.1f} | **vs Avg:** {ratio:.1f}x",
                f"**URL:** https://youtube.com/watch?v={video_id}",
                f"",
            ])

            if thumb_ref:
                report_lines.append(f"![Thumbnail]({thumb_ref})")
                report_lines.append("")

            report_lines.append("---")
            report_lines.append("")
            num += 1
        return num

    if direct_videos:
        add_video_section(direct_videos)
    else:
        report_lines.append("*No videos found matching criteria.*")
        report_lines.append("")

    report_lines.extend([
        f"## Adjacent Audience Outliers",
        f"",
        f"**Keywords:** {', '.join(adjacent_keywords)}",
        f"**Filter:** 10K+ views, last 30 days",
        f"",
    ])

    if adjacent_videos:
        add_video_section(adjacent_videos)
    else:
        report_lines.append("*No videos found matching criteria.*")
        report_lines.append("")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Find top outlier YouTube videos using TubeLab API"
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        required=True,
        help="Direct niche keywords (4 recommended)"
    )
    parser.add_argument(
        "--adjacent-keywords",
        nargs="+",
        required=True,
        help="Adjacent topic keywords your audience watches (4 recommended)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory (e.g., youtube-research/2026-01-12_143052)"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top videos per category (default: 5)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="How many days back to search (default: 30)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output raw JSON data"
    )

    args = parser.parse_args()

    api_key = get_api_key()

    # Setup directories
    output_dir = args.output_dir.resolve()
    thumbnails_dir = output_dir / "thumbnails"
    transcripts_dir = output_dir / "transcripts"

    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching for outlier videos...")
    print()

    # Search 1: Direct niche keywords (5K min views)
    print(f"Search 1: Direct niche")
    print(f"  Keywords: {', '.join(args.keywords)}")
    print(f"  Min views: 5K")

    direct_videos = search_outliers(
        queries=args.keywords,
        api_key=api_key,
        days_back=args.days,
        min_views=5000
    )
    print(f"  Found: {len(direct_videos)} videos")
    print()

    # Search 2: Adjacent keywords (10K min views)
    print(f"Search 2: Adjacent audience")
    print(f"  Keywords: {', '.join(args.adjacent_keywords)}")
    print(f"  Min views: 10K")

    adjacent_videos = search_outliers(
        queries=args.adjacent_keywords,
        api_key=api_key,
        days_back=args.days,
        min_views=10000
    )
    print(f"  Found: {len(adjacent_videos)} videos")
    print()

    # Score and rank videos
    def rank_videos(videos: list[dict], top_n: int) -> list[dict]:
        scored = [(score_video(v), v) for v in videos]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [v for _, v in scored[:top_n]]

    top_direct = rank_videos(direct_videos, args.top)
    top_adjacent = rank_videos(adjacent_videos, args.top)

    # Remove duplicates from adjacent that appear in direct
    direct_ids = {v.get("id") for v in top_direct}
    top_adjacent = [v for v in top_adjacent if v.get("id") not in direct_ids][:args.top]

    print(f"Selected top {len(top_direct)} direct + {len(top_adjacent)} adjacent videos")
    print()

    # Download thumbnails
    print("Downloading thumbnails...")
    for video in top_direct + top_adjacent:
        download_thumbnail(video, thumbnails_dir)

    # Fetch transcripts
    print("Fetching transcripts...")
    transcript_count = 0
    for video in top_direct + top_adjacent:
        video_id = video.get("id")
        if video_id and fetch_transcript(video_id, api_key, transcripts_dir):
            transcript_count += 1
    print(f"  Fetched {transcript_count} transcripts")
    print()

    # Generate report
    report_path = output_dir / "report.md"

    report = generate_report(
        top_direct,
        top_adjacent,
        output_dir,
        thumbnails_dir,
        args.keywords,
        args.adjacent_keywords
    )
    report_path.write_text(report)

    print(f"Report saved: {report_path}")

    # Save outliers JSON (required for video analysis)
    outliers_path = output_dir / "outliers.json"
    all_outliers = []
    for video in top_direct + top_adjacent:
        video_id = video.get("id", "")
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        channel = snippet.get("channel", {})

        # Normalize to format expected by video-content-analyzer
        outlier = {
            "id": video_id,
            "videoId": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channelTitle": channel.get("title", ""),
            "viewCount": stats.get("viewCount", 0),
            "likeCount": stats.get("likeCount", 0),
            "commentCount": stats.get("commentCount", 0),
            "zScore": stats.get("zScore", 0),
            "publishedAt": snippet.get("publishedAt", ""),
            "channelSubs": channel.get("subscribersCount", 0),
            "transcript_path": str(transcripts_dir / f"{video_id}.txt") if (transcripts_dir / f"{video_id}.txt").exists() else None,
        }
        all_outliers.append(outlier)

    outliers_data = {
        "outliers": all_outliers,
        "keywords": args.keywords,
        "adjacent_keywords": args.adjacent_keywords,
        "total_videos": len(all_outliers),
    }
    outliers_path.write_text(json.dumps(outliers_data, indent=2))
    print(f"Outliers JSON saved: {outliers_path}")

    # Optionally save raw JSON
    if args.json:
        json_path = output_dir / "raw-data.json"
        json_data = {
            "direct": top_direct,
            "adjacent": top_adjacent,
            "keywords": args.keywords,
            "adjacent_keywords": args.adjacent_keywords,
        }
        json_path.write_text(json.dumps(json_data, indent=2))
        print(f"Raw JSON saved: {json_path}")

    print()
    print("=== Top Direct Niche Videos ===")
    for i, video in enumerate(top_direct, 1):
        title = video.get("snippet", {}).get("title", "")[:55]
        views = video.get("statistics", {}).get("viewCount", 0)
        print(f"  {i}. {title}... ({format_number(views)} views)")

    print()
    print("=== Top Adjacent Audience Videos ===")
    for i, video in enumerate(top_adjacent, 1):
        title = video.get("snippet", {}).get("title", "")[:55]
        views = video.get("statistics", {}).get("viewCount", 0)
        print(f"  {i}. {title}... ({format_number(views)} views)")


if __name__ == "__main__":
    main()
