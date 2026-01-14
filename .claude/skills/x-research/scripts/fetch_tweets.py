#!/usr/bin/env python3
"""
Fetch tweets from specified X/Twitter accounts using Apify Tweet Scraper V2.
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
    """Parse x-accounts.md and extract handles."""
    handles = []
    with open(accounts_path, 'r') as f:
        in_table = False
        for line in f:
            line = line.strip()
            if line.startswith('| Handle'):
                in_table = True
                continue
            if line.startswith('|---'):
                continue
            if in_table and line.startswith('|'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    handle = parts[1]
                    if handle.startswith('@') and not handle.startswith('@example'):
                        handles.append(handle.lstrip('@'))
    return handles


def fetch_tweets(
    handles: list[str],
    days_back: int = 30,
    max_items_per_handle: int = 100,
    output_path: str = None
) -> list[dict]:
    """
    Fetch tweets from specified handles using Apify Tweet Scraper V2.

    Args:
        handles: List of Twitter handles (without @)
        days_back: How many days back to search
        max_items_per_handle: Maximum tweets per handle
        output_path: Optional path to save raw JSON output

    Returns:
        List of tweet objects
    """
    token = os.environ.get('APIFY_TOKEN')
    if not token:
        print("Error: APIFY_TOKEN environment variable not set")
        sys.exit(1)

    client = ApifyClient(token)

    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    print(f"Fetching tweets from {len(handles)} accounts...")
    print(f"Start date: {start_date}")
    print(f"Max items: {max_items_per_handle * len(handles)}")

    run_input = {
        "twitterHandles": handles,
        "maxItems": max_items_per_handle * len(handles),
        "start": start_date,
        "sort": "Top",
        "tweetLanguage": "en",
        "includeSearchTerms": False,
        "onlyImage": False,
        "onlyQuote": False,
        "onlyTwitterBlue": False,
        "onlyVerifiedUsers": False,
        "onlyVideo": False,
    }

    # Run the Actor
    run = client.actor("apidojo/tweet-scraper").call(run_input=run_input)

    # Fetch results
    tweets = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        tweets.append(item)

    print(f"Fetched {len(tweets)} tweets total")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(tweets, f, indent=2, default=str)
        print(f"Saved raw data to: {output_path}")

    return tweets


def main():
    parser = argparse.ArgumentParser(description='Fetch tweets from X/Twitter accounts')
    parser.add_argument('--accounts-file', '-a',
                        default='.claude/context/x-accounts.md',
                        help='Path to accounts markdown file')
    parser.add_argument('--handles', '-H', nargs='+',
                        help='Specific handles to fetch (overrides accounts file)')
    parser.add_argument('--days', '-d', type=int, default=30,
                        help='Days back to search (default: 30)')
    parser.add_argument('--max-items', '-m', type=int, default=100,
                        help='Max items per handle (default: 100)')
    parser.add_argument('--output', '-o',
                        help='Output path for raw JSON')

    args = parser.parse_args()

    if args.handles:
        handles = [h.lstrip('@') for h in args.handles]
    else:
        if not os.path.exists(args.accounts_file):
            print(f"Error: Accounts file not found: {args.accounts_file}")
            sys.exit(1)
        handles = parse_accounts_file(args.accounts_file)

    if not handles:
        print("Error: No valid handles found")
        sys.exit(1)

    print(f"Handles to fetch: {', '.join(handles)}")

    tweets = fetch_tweets(
        handles=handles,
        days_back=args.days,
        max_items_per_handle=args.max_items,
        output_path=args.output
    )

    # Output summary
    if tweets:
        print(f"\nFetch complete. {len(tweets)} tweets retrieved.")
        print("Use analyze_tweets.py to identify outliers and generate report.")

    return tweets


if __name__ == '__main__':
    main()
