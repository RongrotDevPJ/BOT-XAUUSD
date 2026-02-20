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
            
        now = datetime.now()
        for event in self.news_events:
            try:
                # API usually provides time in UTC or specific format. 
                # Assuming simple ISO format for this example.
                event_time_str = event.get('date') # e.g., "2026-02-21T13:00:00-05:00"
                # This part needs careful parsing depending on the actual API format.
                # Here we'll just simulate the check.
                if event_time_str:
                    # Basic parsing (ignoring offset for simplicity in example)
                    event_dt = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                    # Remove timezone info for comparison if needed
                    event_dt = event_dt.replace(tzinfo=None) 
                    
                    diff = abs((now - event_dt).total_seconds() / 60)
                    if diff <= avoid_minutes:
                        return True, event.get('title')
            except:
                continue
        return False, None
