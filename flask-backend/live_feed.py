# flask-backend/live_feed.py

import feedparser
import requests
import time
from datetime import datetime

# Configuration
FLASK_API_URL = "http://127.0.0.1:5001/ml/predict"
FETCH_INTERVAL = 300  # 5 minutes (300 seconds)
REQUEST_DELAY = 5  # 5 seconds between requests

# Updated Disaster keywords strictly for India
DISASTER_KEYWORDS = [
    "Flood India",
    "Earthquake India",
    "Landslide India",
    "Cyclone India",
    "Fire accident India",
    "Building collapse India"
]

# In-memory set to track seen articles (prevents duplicates in same session)
seen_links = set()


def get_google_news_rss_url(query):
    """Constructs Google News RSS URL for a given query, targeting India."""
    base_url = "https://news.google.com/rss/search"
    # Added gl=IN and ceid=IN:en to force India-specific results
    params = f"?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
    return base_url + params


def fetch_news_feed(query):
    """Fetches and parses RSS feed for a given query."""
    url = get_google_news_rss_url(query)
    try:
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as e:
        print(f"[ERROR] Failed to fetch feed for '{query}': {e}")
        return []


def send_to_flask_api(text, title):
    """Sends article text to Flask API for prediction."""
    payload = {"text": text}
    
    try:
        response = requests.post(FLASK_API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[SUCCESS] Sent: {title}")
            return True
        else:
            print(f"[ERROR] Failed to send '{title}'. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Connection failed. Is Flask server running at {FLASK_API_URL}?")
        return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timeout for '{title}'")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error sending '{title}': {e}")
        return False


def process_articles():
    """Main processing loop - fetches news and sends to API."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching news feeds...")
    
    new_articles_count = 0
    
    for keyword in DISASTER_KEYWORDS:
        entries = fetch_news_feed(keyword)
        
        for entry in entries:
            link = entry.get('link', '')
            title = entry.get('title', 'No Title')
            summary = entry.get('summary', entry.get('description', ''))
            
            # Skip if we've already seen this article
            if link in seen_links:
                continue

            # Optional: Strict filtering (commented out to avoid false negatives like "Mumbai Floods")
            # if "India" not in title and "State" not in title:
            #     continue
            
            # Mark as seen
            seen_links.add(link)
            
            # Construct text payload (title + summary)
            text = f"{title}. {summary}"
            
            # Send to Flask API
            success = send_to_flask_api(text, title)
            
            if success:
                new_articles_count += 1
            
            # CRITICAL: Throttle requests to respect rate limits
            time.sleep(REQUEST_DELAY)
    
    if new_articles_count > 0:
        print(f"[INFO] Processed {new_articles_count} new articles")
    else:
        print(f"[INFO] No new articles found")


def main():
    """Main loop - runs continuously."""
    print("=" * 80)
    print("DISASTER NEWS LIVE FEED MONITOR (INDIA ONLY)")
    print("=" * 80)
    print(f"Flask API: {FLASK_API_URL}")
    print(f"Fetch Interval: {FETCH_INTERVAL} seconds ({FETCH_INTERVAL // 60} minutes)")
    print(f"Request Delay: {REQUEST_DELAY} seconds")
    print(f"Monitoring keywords: {', '.join(DISASTER_KEYWORDS)}")
    print("=" * 80)
    print("\nStarting monitoring... (Press Ctrl+C to stop)\n")
    
    try:
        while True:
            process_articles()
            print(f"\n[INFO] Waiting {FETCH_INTERVAL} seconds ({FETCH_INTERVAL // 60} minutes) before next fetch...\n")
            time.sleep(FETCH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down live feed monitor...")
        print(f"[INFO] Total unique articles seen: {len(seen_links)}")
        print("[INFO] Goodbye!")


if __name__ == "__main__":
    main()
