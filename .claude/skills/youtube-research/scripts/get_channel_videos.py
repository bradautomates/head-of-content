#!/usr/bin/env python3
"""
Fetch videos from a YouTube channel using TubeLab API.
Outputs JSON for Claude to analyze and extract niche keywords.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def load_env_file():
    """Load .env file from project root."""
    # Walk up from script location to find .env
    current = Path(__file__).resolve().parent
    for _ in range(10):  # Max 10 levels up
        env_path = current / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")  # Remove quotes
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


def get_channel_videos(channel_id: str, api_key: str) -> dict:
    """
    Fetch videos from a YouTube channel using TubeLab API.

    Args:
        channel_id: YouTube channel ID (24 characters)
        api_key: TubeLab API key

    Returns:
        Channel data including videos array
    """
    url = f"https://public-api.tubelab.net/v1/channel/videos/{channel_id}"

    req = Request(url)
    req.add_header("Authorization", f"Api-Key {api_key}")
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("item", {})

    except HTTPError as e:
        print(f"API error: {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("Invalid API key. Check your TUBELAB_API_KEY.", file=sys.stderr)
        elif e.code == 400:
            print(f"Invalid channel ID format: {channel_id}", file=sys.stderr)
        elif e.code == 429:
            print("Rate limit exceeded. Wait and try again.", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch videos from a YouTube channel using TubeLab API"
    )
    parser.add_argument(
        "channel_id",
        help="YouTube channel ID (24 characters, e.g., UCxxxxxxxxxxxxxxxxxx)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="json",
        help="Output format: json (full data) or summary (for Claude analysis)"
    )

    args = parser.parse_args()

    # Validate channel ID format
    if len(args.channel_id) != 24:
        print(f"Warning: Channel ID should be 24 characters, got {len(args.channel_id)}", file=sys.stderr)

    api_key = get_api_key()

    channel_data = get_channel_videos(args.channel_id, api_key)

    if not channel_data:
        print("No channel data returned", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(channel_data, indent=2))
    else:
        # Summary format for Claude analysis
        snippet = channel_data.get("snippet", {})
        videos = channel_data.get("videos", [])

        output = {
            "title": snippet.get("title", "Unknown"),
            "description": snippet.get("description", ""),
            "handle": snippet.get("handle", ""),
            "videos": [
                {
                    "title": v.get("title", ""),
                    "viewCount": v.get("viewCount", 0),
                    "publishedAt": v.get("publishedAtEstimate", ""),
                }
                for v in videos
            ]
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
