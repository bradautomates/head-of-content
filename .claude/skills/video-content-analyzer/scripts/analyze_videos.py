#!/usr/bin/env python3
"""
Analyze short-form videos with Gemini AI.
Supports Instagram Reels, TikTok, and YouTube Shorts.
Focuses on content structure, hooks, and replicable patterns.
"""

import json
import argparse
import os
import io
import time
import re
from pathlib import Path

# Conditional imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_MODEL = "gemini-2.5-flash"

# Platform-specific field mappings
PLATFORM_MAPPINGS = {
    "instagram": {
        "video_url": ["videoUrl"],
        "post_id": ["shortCode", "id"],
        "caption": ["caption"],
        "username": ["ownerUsername"],
        "url": ["url"],
        "likes": ["likesCount"],
        "comments": ["commentsCount"],
        "views": ["videoViewCount", "videoPlayCount"],
        "is_video": lambda p: (
            p.get('videoUrl') and (
                p.get('type', '').lower() == 'video' or
                p.get('productType', '').lower() == 'clips' or
                p.get('isVideo')
            )
        ),
    },
    "tiktok": {
        "video_url": ["videoUrl", "video_url", "webVideoUrl"],
        "post_id": ["id", "video_id"],
        "caption": ["text", "desc", "caption", "description"],
        "username": ["authorUsername", "author", "authorMeta.name", "username"],
        "url": ["webVideoUrl", "url"],
        "likes": ["diggCount", "likes", "likesCount"],
        "comments": ["commentCount", "comments", "commentsCount"],
        "views": ["playCount", "plays", "viewCount", "views"],
        "is_video": lambda p: bool(get_field(p, ["videoUrl", "video_url", "webVideoUrl"])),
    },
    "youtube": {
        "video_url": ["videoUrl", "url"],
        "post_id": ["videoId", "id"],
        "caption": ["title", "description"],
        "username": ["channelTitle", "channel", "author"],
        "url": ["url", "videoUrl"],
        "likes": ["likeCount", "likes"],
        "comments": ["commentCount", "comments"],
        "views": ["viewCount", "views"],
        "is_video": lambda p: True,  # YouTube results are always videos
    },
}

VIDEO_ANALYSIS_PROMPT = '''Analyze this short-form video focusing on CONTENT STRUCTURE and HOOK TECHNIQUE.

CAPTION/TITLE CONTEXT:
{caption}

Analyze the video and return a JSON object with this exact structure:

{{
    "hook": {{
        "technique": "<one of: pattern-interrupt, question, bold-claim, story-tease, visual-shock, curiosity-gap, direct-address, controversial-take, relatable-pain, transformation-preview>",
        "opening_line": "<exact words or description of what's said/shown in first 3 seconds>",
        "attention_grab": "<why this hook works - be specific about the psychological trigger>",
        "replicable_formula": "<template version of this hook that could be adapted, e.g. 'If you [action], you're [consequence]'>"
    }},
    "content_structure": {{
        "format": "<one of: problem-solution, listicle, story, tutorial, before-after, day-in-life, reaction, transformation, hot-take, tool-demo>",
        "sections": [
            {{
                "name": "<section name like 'Hook', 'Problem', 'Solution', 'CTA'>",
                "duration_pct": <percentage of video>,
                "description": "<what happens in this section>"
            }}
        ],
        "pacing": "<one of: rapid-fire, fast, moderate, slow>",
        "retention_techniques": ["<list techniques used to keep viewers watching>"]
    }},
    "delivery_style": {{
        "speaking": "<one of: direct-to-camera, voiceover, text-only, mixed, no-speech>",
        "energy": "<one of: high-energy, conversational, calm-authority, urgent>",
        "text_overlays": <true/false>,
        "visual_style": "<description of editing style, transitions, b-roll usage>"
    }},
    "cta_strategy": {{
        "type": "<one of: comment-keyword, link-bio, follow, save, share, dm, none>",
        "cta_text": "<exact CTA if present>",
        "placement": "<where in video the CTA appears>"
    }},
    "why_it_works": "<2-3 sentence analysis of why this content performs well>"
}}

Focus on ACTIONABLE insights that could be replicated. Be specific about techniques.
Return ONLY valid JSON, no other text.'''


def get_field(post: dict, field_names: list, default=None):
    """Get field value trying multiple possible field names."""
    for name in field_names:
        # Handle nested fields like "authorMeta.name"
        if '.' in name:
            parts = name.split('.')
            value = post
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is not None:
                return value
        elif name in post and post[name] is not None:
            return post[name]
    return default


def extract_post_data(post: dict, platform: str) -> dict:
    """Extract normalized data from a post using platform mapping."""
    mapping = PLATFORM_MAPPINGS.get(platform, PLATFORM_MAPPINGS["instagram"])

    return {
        "video_url": get_field(post, mapping["video_url"]),
        "post_id": get_field(post, mapping["post_id"], "unknown"),
        "caption": get_field(post, mapping["caption"], ""),
        "username": get_field(post, mapping["username"], "unknown"),
        "url": get_field(post, mapping["url"], ""),
        "likes": get_field(post, mapping["likes"], 0) or 0,
        "comments": get_field(post, mapping["comments"], 0) or 0,
        "views": get_field(post, mapping["views"], 0) or 0,
        "engagement_score": post.get('_engagement_score', 0),
        "engagement_rate": post.get('_engagement_rate', 0),
    }


def is_video_post(post: dict, platform: str) -> bool:
    """Check if post is a video using platform-specific logic."""
    mapping = PLATFORM_MAPPINGS.get(platform, PLATFORM_MAPPINGS["instagram"])
    is_video_fn = mapping.get("is_video", lambda p: bool(get_field(p, mapping["video_url"])))
    return is_video_fn(post)


def parse_response(text: str) -> dict:
    """Parse Gemini response, handling markdown code blocks."""
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"raw_analysis": text}


def download_video(video_url: str, timeout: int = 60) -> bytes:
    """Download video from URL."""
    response = requests.get(video_url, timeout=timeout)
    response.raise_for_status()
    return response.content


def upload_video_to_gemini(client, video_bytes: bytes, display_name: str):
    """Upload video bytes to Gemini File API."""
    buffer = io.BytesIO(video_bytes)
    file = client.files.upload(
        file=buffer,
        config=types.UploadFileConfig(
            mime_type='video/mp4',
            display_name=display_name
        )
    )
    return file


def wait_for_processing(client, file, timeout: int = 300):
    """Wait for Gemini to process uploaded file."""
    start = time.time()
    while time.time() - start < timeout:
        file = client.files.get(name=file.name)
        if file.state.name == "ACTIVE":
            return file
        elif file.state.name == "FAILED":
            raise RuntimeError(f"File processing failed: {file.name}")
        time.sleep(5)
    raise TimeoutError(f"File processing timeout: {file.name}")


def analyze_video(client, video_source, caption: str) -> dict:
    """Analyze video with Gemini."""
    prompt = VIDEO_ANALYSIS_PROMPT.format(caption=caption[:1000] if caption else "No caption")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[video_source, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
    )

    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                return parse_response(part.text)

    return {"error": "No response from Gemini"}


def analyze_videos(outliers: list[dict], platform: str = "instagram", max_videos: int = 5) -> list[dict]:
    """
    Analyze top outlier videos with Gemini AI.

    Args:
        outliers: List of outlier posts from any platform
        platform: Platform name for field mapping (instagram, tiktok, youtube)
        max_videos: Maximum number of videos to analyze

    Returns:
        List of analysis results for each video.
    """
    if not GEMINI_AVAILABLE:
        print("Error: google-genai package not installed")
        print("  Install with: pip install google-genai")
        return []

    if not REQUESTS_AVAILABLE:
        print("Error: requests package not installed")
        return []

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return []

    client = genai.Client(api_key=api_key)

    # Filter to videos only using platform-specific logic
    video_posts = [p for p in outliers if is_video_post(p, platform)][:max_videos]

    if not video_posts:
        print("No video content found in outliers")
        return []

    print(f"Analyzing {len(video_posts)} {platform} videos with Gemini AI...")
    results = []

    for i, post in enumerate(video_posts, 1):
        data = extract_post_data(post, platform)
        video_url = data["video_url"]

        if not video_url:
            print(f"  [{i}/{len(video_posts)}] Skipping - no video URL")
            continue

        print(f"  [{i}/{len(video_posts)}] Analyzing @{data['username']} - {data['post_id']}...")

        result = {
            "post_id": data["post_id"],
            "username": data["username"],
            "url": data["url"],
            "platform": platform,
            "engagement_score": data["engagement_score"],
            "engagement_rate": data["engagement_rate"],
            "likes": data["likes"],
            "comments": data["comments"],
            "views": data["views"],
        }

        try:
            # Try direct URL first
            try:
                analysis = analyze_video(client, video_url, data["caption"])
                if 'error' not in analysis and 'raw_analysis' not in analysis:
                    result['analysis'] = analysis
                    hook = analysis.get('hook', {}).get('technique', 'analyzed')
                    print(f"    Done: {hook}")
                    results.append(result)
                    time.sleep(2)
                    continue
            except Exception:
                print(f"    Direct URL failed, trying upload...")

            # Fallback: download and upload
            video_bytes = download_video(video_url)
            print(f"    Downloaded {len(video_bytes) / 1024 / 1024:.1f} MB")

            file = upload_video_to_gemini(client, video_bytes, f"{platform}_{data['post_id']}")
            print(f"    Uploaded, processing...")

            file = wait_for_processing(client, file)
            analysis = analyze_video(client, file, data["caption"])
            result['analysis'] = analysis

            hook = analysis.get('hook', {}).get('technique', 'analyzed')
            print(f"    Done: {hook}")

            # Cleanup
            try:
                client.files.delete(name=file.name)
            except:
                pass

            results.append(result)
            time.sleep(2)

        except Exception as e:
            print(f"    Error: {e}")
            result['error'] = str(e)
            results.append(result)

    successful = sum(1 for r in results if 'analysis' in r)
    print(f"Successfully analyzed {successful}/{len(video_posts)} videos")

    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze short-form videos with Gemini AI')
    parser.add_argument('--input', '-i', required=True,
                        help='Input JSON file with outlier posts')
    parser.add_argument('--output', '-o', required=True,
                        help='Output JSON file for video analysis results')
    parser.add_argument('--platform', '-p', default='instagram',
                        choices=['instagram', 'tiktok', 'youtube'],
                        help='Platform for field mapping (default: instagram)')
    parser.add_argument('--max-videos', '-n', type=int, default=5,
                        help='Maximum videos to analyze (default: 5)')

    args = parser.parse_args()

    print(f"Loading outliers from: {args.input}")
    with open(args.input, 'r') as f:
        data = json.load(f)

    # Handle both list format and dict with 'outliers' key
    if isinstance(data, dict) and 'outliers' in data:
        outliers = data['outliers']
    else:
        outliers = data
    print(f"Loaded {len(outliers)} outlier posts")

    results = analyze_videos(outliers, args.platform, args.max_videos)

    # Save results
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nVideo analysis saved to: {args.output}")


if __name__ == '__main__':
    main()
