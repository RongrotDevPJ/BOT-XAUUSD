import requests
from datetime import datetime, timedelta
import logging

class NewsManager:
    """Manages economic calendar data to avoid trading during high-impact news."""
    
    def __init__(self):
        self.news_events = []
        self.last_update = datetime.min
        
    def fetch_news(self):
        """Fetches high-impact news from a free API (e.g., FinancialModelingPrep or similar)."""
        # Note: Using a public free API for demonstration. 
        # In a real scenario, you might use a more robust source.
        try:
            # Simple check to avoid spamming the API (update every 4 hours)
            if datetime.now() - self.last_update < timedelta(hours=4):
                return
            
            # Using a mock-like or simplified URL for example. 
            # In production, use a reliable source like Investing.com or ForexFactory API if available.
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                all_news = response.json()
                # Filter for High Impact USD news (XAUUSD is sensitive to USD)
                self.news_events = [
                    n for n in all_news 
                    if n.get('impact') == 'High' and n.get('country') == 'USD'
                ]
                self.last_update = datetime.now()
                logging.info(f"📰 News Calendar Updated: Found {len(self.news_events)} high-impact USD events.")
        except Exception as e:
            logging.error(f"❌ Error fetching news: {e}")

    def is_news_time(self, avoid_minutes=30):
        """Checks if current time is within the 'avoid' window of any high-impact news."""
        if not self.news_events:
            self.fetch_news()
            
        # Use UTC for all comparisons to prevent timezone issues
        now_utc = datetime.utcnow()
        
        for event in self.news_events:
            try:
                event_time_str = event.get('date') # e.g., "2026-02-21T13:00:00-05:00"
                if event_time_str:
                    # Parse ISO format with offset support
                    # Replace Z with +00:00 for fromisoformat compatibility in Python 3.7+
                    event_dt = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                    
                    # Convert event time to UTC (naive) for comparison
                    if event_dt.tzinfo is not None:
                        event_dt_utc = event_dt.astimezone(timedelta(0)).replace(tzinfo=None)
                    else:
                        event_dt_utc = event_dt
                    
                    diff = abs((now_utc - event_dt_utc).total_seconds() / 60)
                    if diff <= avoid_minutes:
                        return True, event.get('title')
            except Exception as e:
                logging.debug(f"Error parsing news time {event.get('date')}: {e}")
                continue
        return False, None

