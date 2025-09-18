from pytrends.request import TrendReq
import pandas as pd
import time
import random
import os
import urllib3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from .trends_helpers import info, ok, warn, err, Colors
from .proxy_utils import get_current_proxy

# Disable SSL warnings for proxy requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TrendsClient:
    """Manages Google Trends API requests with proxy support and error handling"""
    
    def __init__(self, proxy_rotator=None):
        """
        Initialize TrendsClient
        Args:
            proxy_rotator: Optional ProxyRotator instance
        """
        self.proxy_rotator = proxy_rotator
        self.default_timeframe = "today 3-m"
        self.default_retries = 3
        self.default_backoff = 1.0
        self._pytrends = None
        self._initialize_client()
        
    def _initialize_client(self):
        """
        Initialize the TrendReq client
        """
        self._pytrends = TrendReq(
            hl="en-US",
            tz=360,
            timeout=(15,30),
            retries=self.default_retries,
            backoff_factor=self.default_backoff,
            requests_args={'verify': False}
        )
    
    def get_client(self, proxy: Optional[Dict[str, str]] = None) -> TrendReq:
        """
        Creates a configured TrendReq client
        Args:
            proxy: Optional proxy configuration dict
        Returns:
            Configured TrendReq instance
        """
        return TrendReq(
            hl="en-US",
            tz=360,
            timeout=(15,30),
            retries=self.default_retries,
            backoff_factor=self.default_backoff,
            proxies=proxy,
            requests_args={'verify': False}
        )
    
    def _handle_request(self, operation: str, func, *args, **kwargs) -> pd.DataFrame:
        """
        Generic request handler with retry logic
        Args:
            operation: Description of the operation
            func: Function to execute
            *args, **kwargs: Arguments for the function
        Returns:
            DataFrame with results
        Raises:
            Exception: If all attempts fail
        """
        max_attempts = kwargs.pop('max_attempts', 5)
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            info(f"Attempt {attempt}/{max_attempts}")
            
            try:
                # Get proxy if available
                proxy = get_current_proxy(self.proxy_rotator)
                
                # Initialize client
                client = self.get_client(proxy)
                
                # Random delay before request
                delay = random.uniform(2, 4)
                info(f"Waiting {delay:.1f}s before request")
                time.sleep(delay)
                
                # Build payload
                info(f"Building payload for: {args[0] if args else kwargs.get('keyword', 'unknown')}")
                client.build_payload([args[0] if args else kwargs.get('keyword')], 
                                  timeframe=self.default_timeframe)
                
                # Random delay after payload
                delay = random.uniform(1, 2)
                info(f"Waiting {delay:.1f}s after payload")
                time.sleep(delay)
                
                # Execute requested operation
                info(f"Fetching {operation}")
                df = func(client, *args, **kwargs)
                
                if df is None or df.empty:
                    raise ValueError(f"Received empty dataset for {operation}")
                
                ok(f"Successfully fetched {operation}")
                return df
                
            except Exception as e:
                last_error = e
                warn(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt < max_attempts:
                    delay = random.uniform(3, 5)
                    info(f"Waiting {delay:.1f}s before retry")
                    time.sleep(delay)
                else:
                    err(f"All {max_attempts} attempts failed")
        
        raise last_error
    
    def fetch_interest_over_time(self, keyword: str, max_attempts: int = 5) -> pd.DataFrame:
        """
        Fetches interest over time data
        Args:
            keyword: Search term
            max_attempts: Maximum number of retry attempts
        Returns:
            DataFrame with trend data
        """
        return self._handle_request(
            "interest over time",
            lambda client, kw: client.interest_over_time(),
            keyword,
            max_attempts=max_attempts
        )
    
    def fetch_interest_by_region(self, keyword: str, max_attempts: int = 3) -> pd.DataFrame:
        """
        Fetches regional interest data
        Args:
            keyword: Search term
            max_attempts: Maximum number of retry attempts
        Returns:
            DataFrame with regional data
        """
        return self._handle_request(
            "regional interest",
            lambda client, kw: client.interest_by_region(resolution="COUNTRY"),
            keyword,
            max_attempts=max_attempts
        ) 