#!/usr/bin/env python3
"""
Fetch TikTok videos from specified accounts using Apify TikTok Scraper.
Requires APIFY_TOKEN environment variable (or in .env file).
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment variables

try:
    from apify_client import ApifyClient
except ImportError:
    print("Error: apify-client not installed. Run: pip install apify-client")
    sys.exit(1)


def parse_accounts_file(accounts_path: str) -> list[str]:
    """Parse tiktok-accounts.md and extract usernames."""
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


def fetch_tiktok(
    usernames: list[str],
    results_limit: int = 50,
    days_back: int = 30,
    sorting: str = "latest",
    output_path: str = None
) -> list[dict]:
    """
    Fetch TikTok videos from specified usernames using Apify TikTok Scraper.

    Args:
        usernames: List of TikTok usernames (without @)
        results_limit: Maximum videos per account
        days_back: Filter to only include posts newer than this many days
        sorting: Sort order - "latest", "popular", or "oldest"
        output_path: Optional path to save raw JSON output

    Returns:
        List of video objects
    """
    token = os.environ.get('APIFY_TOKEN')
    if not token:
        print("Error: APIFY_TOKEN environment variable not set")
        sys.exit(1)

    client = ApifyClient(token)

    # Calculate date filter
    oldest_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    print(f"Fetching videos from {len(usernames)} accounts...")
    print(f"Accounts: {', '.join(usernames)}")
    print(f"Results limit per account: {results_limit}")
    print(f"Videos newer than: {oldest_date}")
    print(f"Sorting: {sorting}")

    run_input = {
        "profiles": usernames,
        "resultsPerPage": results_limit,
        "profileScrapeSections": ["videos"],
        "profileSorting": sorting,
        "oldestPostDateUnified": oldest_date,
        "excludePinnedPosts": False,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }

    # Run the Actor (clockworks/tiktok-scraper)
    run = client.actor("GdWCkxBtKWOsKjdch").call(run_input=run_input)

    # Fetch results
    items = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # Normalize field names for consistency with analysis script
        normalized = {
            'id': item.get('id'),
            'text': item.get('text', ''),
            'createTime': item.get('createTime'),
            'createTimeISO': item.get('createTimeISO'),
            'webVideoUrl': item.get('webVideoUrl'),
            # Engagement metrics
            'diggCount': item.get('diggCount', 0),  # likes/hearts
            'shareCount': item.get('shareCount', 0),
            'playCount': item.get('playCount', 0),
            'commentCount': item.get('commentCount', 0),
            'collectCount': item.get('collectCount', 0),  # saves/bookmarks
            # Author metadata
            'authorUsername': item.get('authorMeta', {}).get('name', ''),
            'authorNickname': item.get('authorMeta', {}).get('nickName', ''),
            'authorFollowers': item.get('authorMeta', {}).get('fans', 0),
            'authorFollowing': item.get('authorMeta', {}).get('following', 0),
            'authorHearts': item.get('authorMeta', {}).get('heart', 0),
            'authorVerified': item.get('authorMeta', {}).get('verified', False),
            # Video metadata
            'videoDuration': item.get('videoMeta', {}).get('duration', 0),
            'videoHeight': item.get('videoMeta', {}).get('height'),
            'videoWidth': item.get('videoMeta', {}).get('width'),
            'coverUrl': item.get('videoMeta', {}).get('coverUrl'),
            # Content metadata
            'hashtags': item.get('hashtags', []),
            'mentions': item.get('mentions', []),
            'isPinned': item.get('isPinned', False),
            'isAd': item.get('isAd', False),
            # Music metadata
            'musicName': item.get('musicMeta', {}).get('musicName'),
            'musicAuthor': item.get('musicMeta', {}).get('musicAuthor'),
            'musicOriginal': item.get('musicMeta', {}).get('musicOriginal', False),
            # Raw item for reference
            '_raw': item
        }
        items.append(normalized)

    print(f"Fetched {len(items)} videos total")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(items, f, indent=2, default=str)
        print(f"Saved raw data to: {output_path}")

    return items


def main():
    parser = argparse.ArgumentParser(description='Fetch TikTok videos from accounts')
    parser.add_argument('--accounts-file', '-a',
                        default='.claude/context/tiktok-accounts.md',
                        help='Path to accounts markdown file')
    parser.add_argument('--usernames', '-u', nargs='+',
                        help='Specific usernames to fetch (overrides accounts file)')
    parser.add_argument('--limit', '-l', type=int, default=50,
                        help='Max videos per account (default: 50)')
    parser.add_argument('--days', '-d', type=int, default=30,
                        help='Days back to search (default: 30)')
    parser.add_argument('--sorting', '-s', choices=['latest', 'popular', 'oldest'],
                        default='latest',
                        help='Sort order (default: latest)')
    parser.add_argument('--output', '-o',
                        help='Output path for raw JSON')

    args = parser.parse_args()

    if args.usernames:
        usernames = [u.lstrip('@') for u in args.usernames]
    else:
        if not os.path.exists(args.accounts_file):
            print(f"Error: Accounts file not found: {args.accounts_file}")
            sys.exit(1)
        usernames = parse_accounts_file(args.accounts_file)

    if not usernames:
        print("Error: No valid usernames found")
        sys.exit(1)

    print(f"Usernames to fetch: {', '.join(usernames)}")

    items = fetch_tiktok(
        usernames=usernames,
        results_limit=args.limit,
        days_back=args.days,
        sorting=args.sorting,
        output_path=args.output
    )

    # Output summary
    if items:
        print(f"\nFetch complete. {len(items)} videos retrieved.")
        print("Use analyze_posts.py to identify outliers and generate report.")

    return items


if __name__ == '__main__':
    main()
