import os, time, random
from requests.exceptions import RequestException
from colorama import Fore
from typing import Optional, Dict, List
from .trends_helpers import info, warn, Colors

# ─── Proxy Management and Rotation ─────────────────────────────
class ProxyRotator:
    """
    Manages rotating proxies with cooldown logic to avoid rate limits.
    Supports fallback to direct connection if no proxies are available.
    
    Usage:
        rotator = ProxyRotator(list_of_proxies)
        proxy = rotator.get_next_proxy()
    """
    def __init__(self, proxies: Optional[List[str]] = None, cooldown: int = 30):
        """
        Initialize the rotator.
        Args:
            proxies: Optional list of proxy URLs
            cooldown: Seconds to wait before reusing a proxy (default: 30)
        """
        self.proxies = proxies or []
        self.current_index = 0
        self.last_used = {}
        self.cooldown = cooldown
        self.direct_connection_last_used = 0
        
        if self.proxies:
            info(f"Initialized ProxyRotator with {len(proxies)} proxies")
            for i, proxy in enumerate(proxies, 1):
                info(f"Proxy {i}: {proxy}")
        else:
            warn("No proxies provided - will use direct connections")
    
    def get_next_proxy(self) -> Optional[str]:
        """
        Returns the next available proxy or None for direct connection.
        Handles cooldown periods and empty proxy lists gracefully.
        
        Returns:
            Proxy URL string or None for direct connection
        """
        current_time = time.time()
        
        # If no proxies available, handle direct connection with cooldown
        if not self.proxies:
            time_since_direct = current_time - self.direct_connection_last_used
            if time_since_direct < self.cooldown:
                wait_time = self.cooldown - time_since_direct
                info(f"Direct connection in cooldown, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            self.direct_connection_last_used = time.time()
            info("Using direct connection (no proxies available)")
            return None
        
        # Find available proxies not in cooldown
        available_proxies = []
        for i, proxy in enumerate(self.proxies):
            last_used = self.last_used.get(proxy, 0)
            time_since_use = current_time - last_used
            
            if time_since_use >= self.cooldown:
                available_proxies.append((i, proxy))
            else:
                remaining = self.cooldown - time_since_use
                info(f"Proxy {i+1} in cooldown ({remaining:.1f}s remaining)")
        
        # If no proxies available, wait for the one with shortest remaining cooldown
        if not available_proxies:
            if not self.last_used:
                # No proxy has been used yet
                selected_index = 0
                selected_proxy = self.proxies[0]
            else:
                # Find proxy with shortest remaining cooldown
                min_wait = min(
                    self.cooldown - (current_time - last_used)
                    for last_used in self.last_used.values()
                )
                info(f"All proxies in cooldown, waiting {min_wait:.1f}s")
                time.sleep(min_wait)
                return self.get_next_proxy()
        else:
            # Randomly select from available proxies
            selected_index, selected_proxy = random.choice(available_proxies)
        
        # Update last used time
        self.last_used[selected_proxy] = time.time()
        info(f"Selected proxy {selected_index + 1}/{len(self.proxies)}")
        
        # Return proxy string
        return selected_proxy

# ─── Proxy Testing ─────────────────────────────────────────────
def test_proxy(proxy_url: str) -> bool:
    """
    Test if a proxy is working by making a request to a known endpoint.
    Returns True if successful, False otherwise.
    """
    import requests
    try:
        print(f"Testing proxy: {proxy_url}")
        proxies = {"http": proxy_url, "https": proxy_url}
        response = requests.get("https://ipv4.webshare.io/", proxies=proxies, timeout=10)
        if response.status_code == 200:
            print(f"Proxy working: {proxy_url}")
            return True
        else:
            print(f"Proxy failed with status {response.status_code}: {proxy_url}")
            return False
    except RequestException as e:
        print(f"Proxy error: {str(e)} - {proxy_url}")
        return False

# ─── Proxy List from Environment ───────────────────────────────
def get_proxies_from_env():
    """
    Reads proxy URLs from environment variables PROXY_1, PROXY_2, ...
    Returns a list of proxies.
    """
    proxies = []
    for i in range(1, 8):
        proxy = os.getenv(f"PROXY_{i}")
        if proxy:
            proxies.append(proxy)
    return proxies

# ─── Proxy Getter for pytrends ─────────────────────────────────
def get_current_proxy(proxy_rotator: Optional[ProxyRotator] = None) -> Optional[List[str]]:
    """
    Get next proxy from rotator or None for direct connection
    Args:
        proxy_rotator: Optional ProxyRotator instance
    Returns:
        List containing single proxy string or None
    """
    if proxy_rotator is None:
        info("No proxy rotator provided - using direct connection")
        return None
        
    proxy_string = proxy_rotator.get_next_proxy()
    if proxy_string is None:
        return None
    
    # Return as a list containing the proxy string (what pytrends expects)
    return [proxy_string] 