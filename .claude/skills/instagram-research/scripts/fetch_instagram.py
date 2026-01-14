#!/usr/bin/env python3
"""
Fetch Instagram posts/reels from specified accounts using Apify Instagram Scraper.
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
    """Parse instagram-accounts.md and extract usernames."""
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


def fetch_profiles(client: 'ApifyClient', usernames: list[str]) -> dict[str, dict]:
    """
    Fetch Instagram profile data (follower counts, etc.) using the profile scraper.

    Args:
        client: ApifyClient instance
        usernames: List of Instagram usernames (without @)

    Returns:
        Dict mapping username to profile data
    """
    print(f"Fetching profile data for {len(usernames)} accounts...")

    run_input = {
        "usernames": usernames,
    }

    run = client.actor("apify/instagram-profile-scraper").call(run_input=run_input)

    profiles = {}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        username = item.get('username', '').lower()
        if username:
            profiles[username] = {
                'followersCount': item.get('followersCount', 0),
                'followingCount': item.get('followingCount', 0),
                'postsCount': item.get('postsCount', 0),
                'fullName': item.get('fullName', ''),
                'biography': item.get('biography', ''),
                'isVerified': item.get('isVerified', False),
            }

    print(f"Fetched profile data for {len(profiles)} accounts")
    return profiles


def fetch_instagram(
    usernames: list[str],
    results_type: str = "posts",
    results_limit: int = 50,
    days_back: int = 30,
    output_path: str = None
) -> list[dict]:
    """
    Fetch Instagram content from specified usernames using Apify Instagram Scraper.
    Also fetches profile data to get accurate follower counts.

    Args:
        usernames: List of Instagram usernames (without @)
        results_type: Type of content - "posts", "reels", or "stories"
        results_limit: Maximum items per account
        days_back: Filter to only include posts newer than this many days
        output_path: Optional path to save raw JSON output

    Returns:
        List of post/reel objects with follower counts merged in
    """
    token = os.environ.get('APIFY_TOKEN')
    if not token:
        print("Error: APIFY_TOKEN environment variable not set")
        sys.exit(1)

    client = ApifyClient(token)

    # First fetch profile data for follower counts
    profiles = fetch_profiles(client, usernames)

    # Build direct URLs for each username
    direct_urls = [f"https://www.instagram.com/{username}/" for username in usernames]

    # Calculate date filter
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    print(f"Fetching {results_type} from {len(usernames)} accounts...")
    print(f"Accounts: {', '.join(usernames)}")
    print(f"Results limit per account: {results_limit}")
    print(f"Posts newer than: {start_date}")

    run_input = {
        "directUrls": direct_urls,
        "resultsType": results_type,
        "resultsLimit": results_limit,
        "onlyPostsNewerThan": start_date,
    }

    # Run the Actor
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    # Fetch results and merge profile data
    items = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        # Merge follower count from profile data
        owner_username = (item.get('ownerUsername', '') or '').lower()
        if owner_username and owner_username in profiles:
            profile = profiles[owner_username]
            item['ownerFollowersCount'] = profile['followersCount']
            item['ownerFollowingCount'] = profile['followingCount']
            if not item.get('ownerFullName'):
                item['ownerFullName'] = profile['fullName']
        items.append(item)

    print(f"Fetched {len(items)} {results_type} total")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(items, f, indent=2, default=str)
        print(f"Saved raw data to: {output_path}")

    return items


def main():
    parser = argparse.ArgumentParser(description='Fetch Instagram posts/reels from accounts')
    parser.add_argument('--accounts-file', '-a',
                        default='.claude/context/instagram-accounts.md',
                        help='Path to accounts markdown file')
    parser.add_argument('--usernames', '-u', nargs='+',
                        help='Specific usernames to fetch (overrides accounts file)')
    parser.add_argument('--type', '-t', choices=['posts', 'reels', 'stories'],
                        default='posts',
                        help='Type of content to fetch (default: posts)')
    parser.add_argument('--limit', '-l', type=int, default=50,
                        help='Max items per account (default: 50)')
    parser.add_argument('--days', '-d', type=int, default=30,
                        help='Days back to search (default: 30)')
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

    items = fetch_instagram(
        usernames=usernames,
        results_type=args.type,
        results_limit=args.limit,
        days_back=args.days,
        output_path=args.output
    )

    # Output summary
    if items:
        print(f"\nFetch complete. {len(items)} items retrieved.")
        print("Use analyze_posts.py to identify outliers and generate report.")

    return items


if __name__ == '__main__':
    main()
