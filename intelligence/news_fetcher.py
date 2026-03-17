"""
AURUM News Fetcher
==================
Fetches real-time news from multiple sources for NLP analysis.

Sources:
  1. RSS Feeds (Reuters, CNBC, MarketWatch) - Free, no API key
  2. NewsAPI - Free tier (100 requests/day)
  3. Finnhub - Free tier (60 calls/min)
  4. Alpha Vantage - Free tier

For production, consider:
  - Bloomberg Terminal API
  - Refinitiv/Reuters Eikon
  - Dow Jones Newswires
"""

import time
import hashlib
import ssl
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import json
import re

# Create SSL context that doesn't verify certificates (for RSS feeds)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


@dataclass
class NewsHeadline:
    """Single news headline with metadata."""
    text: str
    source: str
    url: str
    timestamp: float  # Unix timestamp
    category: str = "general"
    sentiment_hint: Optional[str] = None  # From source if available

    @property
    def age_hours(self) -> float:
        """Hours since publication."""
        return (time.time() - self.timestamp) / 3600

    @property
    def headline_id(self) -> str:
        """Unique ID for deduplication."""
        return hashlib.md5(f"{self.text[:50]}{self.source}".encode()).hexdigest()[:12]


# ============================================================
# RSS Feed Sources (Free, No API Key Required)
# ============================================================

RSS_FEEDS = {
    # Google News - Comprehensive search covering all key topics
    'google_news_macro': 'https://news.google.com/rss/search?q=gold+OR+federal+reserve+OR+inflation+OR+war+OR+sanctions&hl=en-US&gl=US&ceid=US:en',

    # Yahoo Finance - Market news
    'yahoo_finance': 'https://finance.yahoo.com/news/rssindex',

    # BBC World - Geopolitical coverage
    'bbc_world': 'https://feeds.bbci.co.uk/news/world/rss.xml',

    # Reuters - Business news
    'reuters_business': 'https://news.google.com/rss/search?q=site:reuters.com+economy+OR+markets&hl=en-US&gl=US&ceid=US:en',

    # New York Times - Premium journalism
    'nyt_world': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'nyt_business': 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
    'nyt_economy': 'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
}

# Gold/Macro relevant keywords for filtering
RELEVANCE_KEYWORDS = [
    # Precious metals
    'gold', 'silver', 'bullion', 'precious metal', 'xau', 'gld', 'slv',
    'gold price', 'gold futures', 'comex', 'lbma',

    # Central banks
    'fed', 'federal reserve', 'fomc', 'powell', 'rate', 'interest rate',
    'ecb', 'lagarde', 'boj', 'pboc', 'central bank', 'monetary policy',
    'rate cut', 'rate hike', 'quantitative', 'tightening', 'easing',

    # Macro
    'inflation', 'cpi', 'pce', 'gdp', 'recession', 'employment', 'jobs',
    'treasury', 'yield', 'bond', 'dollar', 'dxy', 'currency',

    # Geopolitical
    'war', 'military', 'conflict', 'sanction', 'russia', 'ukraine', 'china',
    'taiwan', 'iran', 'israel', 'middle east', 'nato', 'nuclear',
    'invasion', 'attack', 'missile', 'troops',

    # Market stress
    'crisis', 'crash', 'selloff', 'volatility', 'vix', 'fear', 'panic',
    'bank failure', 'default', 'contagion', 'liquidity',

    # Safe haven flows
    'safe haven', 'risk off', 'flight to safety', 'haven demand',
]


def fetch_rss_feed(url: str, source_name: str, max_age_hours: float = 48) -> List[NewsHeadline]:
    """Fetch and parse a single RSS feed."""
    headlines = []

    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as response:
            content = response.read()
            root = ET.fromstring(content)

            # Handle both RSS 2.0 and Atom formats
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for item in items:
                try:
                    # RSS 2.0 format
                    title = item.find('title')
                    pub_date = item.find('pubDate')
                    link = item.find('link')

                    # Atom format fallback
                    if title is None:
                        title = item.find('{http://www.w3.org/2005/Atom}title')
                    if pub_date is None:
                        pub_date = item.find('{http://www.w3.org/2005/Atom}published')
                    if link is None:
                        link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                        link_url = link_elem.get('href') if link_elem is not None else ""
                    else:
                        link_url = link.text if link.text else ""

                    if title is None or title.text is None:
                        continue

                    # Parse timestamp
                    timestamp = time.time()  # Default to now
                    if pub_date is not None and pub_date.text:
                        timestamp = parse_rss_date(pub_date.text)

                    # Skip old headlines
                    age_hours = (time.time() - timestamp) / 3600
                    if age_hours > max_age_hours:
                        continue

                    headlines.append(NewsHeadline(
                        text=clean_headline(title.text),
                        source=source_name,
                        url=link_url,
                        timestamp=timestamp,
                        category='rss',
                    ))

                except Exception as e:
                    continue

    except Exception as e:
        print(f"  Warning: Failed to fetch {source_name}: {e}")

    return headlines


def parse_rss_date(date_str: str) -> float:
    """Parse various RSS date formats to Unix timestamp."""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
    ]

    # Clean up timezone
    date_str = date_str.replace('GMT', '+0000').replace('UTC', '+0000')

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return time.time()


def clean_headline(text: str) -> str:
    """Clean headline text."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Decode HTML entities
    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()


def is_relevant(headline: str) -> bool:
    """Check if headline is relevant to gold/macro."""
    headline_lower = headline.lower()
    return any(kw in headline_lower for kw in RELEVANCE_KEYWORDS)


# ============================================================
# NewsAPI Integration (Requires API Key)
# ============================================================

def fetch_newsapi(api_key: str, max_age_hours: float = 48) -> List[NewsHeadline]:
    """
    Fetch from NewsAPI.org
    Free tier: 100 requests/day, headlines only, 24h delay on free
    """
    if not api_key:
        return []

    headlines = []

    # Gold/commodities query
    queries = [
        'gold price OR gold futures OR bullion',
        'federal reserve OR fed rate OR fomc',
        'geopolitical risk OR war OR sanctions',
    ]

    for query in queries:
        try:
            url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(query)}&language=en&sortBy=publishedAt&pageSize=20&apiKey={api_key}"

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())

                for article in data.get('articles', []):
                    try:
                        title = article.get('title', '')
                        if not title:
                            continue

                        pub_date = article.get('publishedAt', '')
                        timestamp = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).timestamp() if pub_date else time.time()

                        age_hours = (time.time() - timestamp) / 3600
                        if age_hours > max_age_hours:
                            continue

                        headlines.append(NewsHeadline(
                            text=clean_headline(title),
                            source=article.get('source', {}).get('name', 'NewsAPI'),
                            url=article.get('url', ''),
                            timestamp=timestamp,
                            category='newsapi',
                        ))
                    except:
                        continue

        except Exception as e:
            print(f"  Warning: NewsAPI error: {e}")

    return headlines


# ============================================================
# Finnhub Integration (Requires API Key)
# ============================================================

def fetch_finnhub(api_key: str, max_age_hours: float = 48) -> List[NewsHeadline]:
    """
    Fetch from Finnhub.io
    Free tier: 60 calls/min
    Has sentiment scores!
    """
    if not api_key:
        return []

    headlines = []

    # Market news categories
    categories = ['general', 'forex', 'crypto', 'merger']

    for category in categories:
        try:
            url = f"https://finnhub.io/api/v1/news?category={category}&token={api_key}"

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                articles = json.loads(response.read())

                for article in articles:
                    try:
                        title = article.get('headline', '')
                        if not title or not is_relevant(title):
                            continue

                        timestamp = article.get('datetime', time.time())

                        age_hours = (time.time() - timestamp) / 3600
                        if age_hours > max_age_hours:
                            continue

                        headlines.append(NewsHeadline(
                            text=clean_headline(title),
                            source=article.get('source', 'Finnhub'),
                            url=article.get('url', ''),
                            timestamp=timestamp,
                            category='finnhub',
                            sentiment_hint=str(article.get('sentiment', '')),
                        ))
                    except:
                        continue

        except Exception as e:
            print(f"  Warning: Finnhub error: {e}")

    return headlines


# ============================================================
# Combined Fetcher
# ============================================================

@dataclass
class NewsFetchResult:
    """Result of fetching news from all sources."""
    headlines: List[NewsHeadline]
    total_fetched: int
    relevant_count: int
    sources_succeeded: List[str]
    sources_failed: List[str]
    fetch_timestamp: float

    @property
    def headlines_by_recency(self) -> List[NewsHeadline]:
        """Headlines sorted by timestamp (newest first)."""
        return sorted(self.headlines, key=lambda h: h.timestamp, reverse=True)

    @property
    def headlines_last_hour(self) -> List[NewsHeadline]:
        """Headlines from last hour."""
        cutoff = time.time() - 3600
        return [h for h in self.headlines if h.timestamp >= cutoff]

    @property
    def headlines_last_6h(self) -> List[NewsHeadline]:
        """Headlines from last 6 hours."""
        cutoff = time.time() - 6 * 3600
        return [h for h in self.headlines if h.timestamp >= cutoff]


def fetch_all_news(
    newsapi_key: str = None,
    finnhub_key: str = None,
    max_age_hours: float = 48,
    filter_relevant: bool = True,
) -> NewsFetchResult:
    """
    Fetch news from all available sources.

    Args:
        newsapi_key: Optional NewsAPI.org API key
        finnhub_key: Optional Finnhub.io API key
        max_age_hours: Maximum headline age to include
        filter_relevant: If True, only return gold/macro relevant headlines

    Returns:
        NewsFetchResult with all headlines and metadata
    """
    all_headlines = []
    sources_succeeded = []
    sources_failed = []

    print("  Fetching news from RSS feeds...")

    # Fetch from RSS feeds (always available)
    for source_name, url in RSS_FEEDS.items():
        try:
            headlines = fetch_rss_feed(url, source_name, max_age_hours)
            if headlines:
                all_headlines.extend(headlines)
                sources_succeeded.append(source_name)
            else:
                sources_failed.append(source_name)
        except Exception as e:
            sources_failed.append(source_name)

    # Fetch from NewsAPI if key provided
    if newsapi_key:
        print("  Fetching from NewsAPI...")
        try:
            headlines = fetch_newsapi(newsapi_key, max_age_hours)
            all_headlines.extend(headlines)
            sources_succeeded.append('newsapi')
        except:
            sources_failed.append('newsapi')

    # Fetch from Finnhub if key provided
    if finnhub_key:
        print("  Fetching from Finnhub...")
        try:
            headlines = fetch_finnhub(finnhub_key, max_age_hours)
            all_headlines.extend(headlines)
            sources_succeeded.append('finnhub')
        except:
            sources_failed.append('finnhub')

    total_fetched = len(all_headlines)

    # Filter for relevance
    if filter_relevant:
        all_headlines = [h for h in all_headlines if is_relevant(h.text)]

    # Deduplicate by headline_id
    seen_ids = set()
    unique_headlines = []
    for h in all_headlines:
        if h.headline_id not in seen_ids:
            seen_ids.add(h.headline_id)
            unique_headlines.append(h)

    return NewsFetchResult(
        headlines=unique_headlines,
        total_fetched=total_fetched,
        relevant_count=len(unique_headlines),
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
        fetch_timestamp=time.time(),
    )


# ============================================================
# Quick Test
# ============================================================

if __name__ == "__main__":
    print("Fetching news...")
    result = fetch_all_news(max_age_hours=24, filter_relevant=True)

    print(f"\nFetched {result.total_fetched} total headlines")
    print(f"Relevant: {result.relevant_count}")
    print(f"Sources OK: {result.sources_succeeded}")
    print(f"Sources Failed: {result.sources_failed}")

    print("\n=== Recent Headlines (Last 6h) ===")
    for h in result.headlines_last_6h[:10]:
        print(f"[{h.source}] {h.text[:80]}...")
        print(f"   Age: {h.age_hours:.1f}h | {h.url[:50]}")
        print()
