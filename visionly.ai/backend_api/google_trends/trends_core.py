"""
Core functionality for Google Trends analysis
"""
import os, io, time, random, warnings, json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import pandas as pd
import matplotlib.pyplot as plt
from pytrends.request import TrendReq
from requests.exceptions import RequestException
from colorama import Fore, Style, init as c_init
from dotenv import load_dotenv
from supabase import create_client
import requests

from .trends_helpers import (
    banner, info, warn, err, ok,
    Colors, timestamp, sanitize_filename, ensure_dirs, get_output_paths
)
from .proxy_utils import ProxyRotator, get_current_proxy
from .supabase_utils import upload_supabase

c_init(autoreset=True)

warnings.filterwarnings("ignore")

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
SUPA = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# Get proxies from environment variables
PROXIES = []
for i in range(1, 8):  # Assuming we have PROXY_1 through PROXY_7
    proxy = os.getenv(f"PROXY_{i}")
    if proxy:
        PROXIES.append(proxy)

if not PROXIES:
    warn("No proxies found in environment variables!")

def upload_supabase(data: bytes|str, fname: str, bucket: str):
    if not SUPA:
        warn("Supabase creds missing – skipping upload.")
        return
    if isinstance(data, str):
        data = data.encode("utf-8")
    SUPA.storage.from_(bucket).upload(
        path=fname,
        file=data,
        file_options={"content-type": "text/csv" if fname.endswith(".csv") else "image/png"}
    )
    url = SUPA.storage.from_(bucket).get_public_url(fname)
    ok(f"Supabase upload → {url}")

def test_proxy(proxy_url: str) -> bool:
    try:
        info(f"Testing proxy: {proxy_url}")
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        response = requests.get(
            "https://ipv4.webshare.io/",
            proxies=proxies,
            timeout=10
        )
        if response.status_code == 200:
            ok(f"Proxy working: {proxy_url}")
            return True
        else:
            warn(f"Proxy failed with status {response.status_code}: {proxy_url}")
            return False
    except RequestException as e:
        warn(f"Proxy error: {str(e)} - {proxy_url}")
        return False

# Test and filter working proxies
WORKING_PROXIES = [proxy for proxy in PROXIES if test_proxy(proxy)]
if not WORKING_PROXIES:
    warn("No working proxies found! Using direct connection.")
    WORKING_PROXIES = PROXIES  # Fallback to all proxies if none work
else:
    ok(f"Found {len(WORKING_PROXIES)} working proxies")

class ProxyRotator:
    def __init__(self, proxies):
        self.proxies = proxies
        self.current_index = 0
        self.last_used = {}  # Track when each proxy was last used
        self.cooldown = 30  # Cooldown period in seconds
        info(f"Initialized ProxyRotator with {len(proxies)} proxies")

    def get_next_proxy(self):
        current_time = time.time()
        available_proxies = []
        
        # Find proxies that are out of cooldown
        for i, proxy in enumerate(self.proxies):
            last_used = self.last_used.get(proxy, 0)
            time_since_use = current_time - last_used
            if time_since_use >= self.cooldown:
                available_proxies.append((i, proxy))
            else:
                info(f"Proxy {proxy} in cooldown, {self.cooldown - time_since_use:.1f}s remaining")
        
        if not available_proxies:
            # If all proxies are in cooldown, wait for the one with shortest remaining cooldown
            min_wait = min(self.cooldown - (current_time - last_used) 
                         for last_used in self.last_used.values())
            info(f"All proxies in cooldown, waiting {min_wait:.1f}s")
            time.sleep(min_wait)
            return self.get_next_proxy()
        
        # Select a random proxy from available ones
        selected_index, selected_proxy = random.choice(available_proxies)
        self.last_used[selected_proxy] = current_time
        info(f"Selected proxy {selected_index + 1}/{len(self.proxies)}: {selected_proxy}")
        return selected_proxy

proxy_rotator = ProxyRotator(WORKING_PROXIES)

def get_current_proxy() -> Optional[List[str]]:
    """Get next proxy from rotator or None for direct connection"""
    proxy = proxy_rotator.get_next_proxy()
    if proxy:
        info(f"Using proxy: {proxy}")
        # Return as a list containing the proxy string (what pytrends expects)
        return [proxy]
    warn("No proxy available, using direct connection")
    return None

def fetch_trends(keyword: str,
                 attempts: int = None,
                 sleep_sec: int = 60) -> pd.DataFrame:
    attempts = attempts or (len(WORKING_PROXIES) + 2)
    last_err = None
    for i in range(1, attempts + 1):
        info(f"Attempt {i}/{attempts}")
        try:
            proxy = get_current_proxy()
            info(f"Initializing TrendReq with proxy: {proxy}")
            pt = TrendReq(
                hl="en-US",
                tz=360,
                timeout=(15,30),
                retries=3,
                backoff_factor=1.0,
                proxies=proxy,  # pytrends will handle the proxy list
                requests_args={'verify': False},
            )
            delay = random.uniform(2, 4)
            info(f"Waiting {delay:.1f}s before request")
            time.sleep(delay)
            
            info(f"Building payload for keyword: {keyword}")
            pt.build_payload([keyword], timeframe="today 3-m")
            
            delay = random.uniform(1, 2)
            info(f"Waiting {delay:.1f}s after payload")
            time.sleep(delay)
            
            info("Fetching interest over time data")
            df = pt.interest_over_time()
            if df.empty:
                raise ValueError("Empty dataframe")
            ok("Trend data fetched successfully")
            return df
        except Exception as e:
            warn(f"Fetch failed: {str(e)}")
            last_err = e
            delay = random.uniform(3, 5)
            info(f"Waiting {delay:.1f}s before retry")
            time.sleep(delay)
    raise last_err

def get_trendreq(proxy):
    return TrendReq(
        hl="en-US",
        tz=360,
        timeout=(15,30),
        retries=3,
        backoff_factor=1.0,
        requests_args={'verify': False},
        proxies=proxy
    )

def save_and_upload(df, path, fname, bucket):
    df.to_csv(path)
    ok(f"CSV → {path}")
    upload_supabase(df.to_csv(), fname, bucket)

def save_fig_and_upload(fig, path, fname, bucket):
    fig.savefig(path, dpi=300, bbox_inches='tight')
    ok(f"PNG → {path}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    upload_supabase(buf.getvalue(), fname, bucket)
    plt.close(fig)

def analyze_keyword(keyword: str, base_dir: str) -> pd.DataFrame:
    banner(f"GOOGLE TRENDS · {keyword.upper()}", Fore.MAGENTA)

    # Create main output directory
    os.makedirs(base_dir, exist_ok=True)
    
    # Create SUMMARY directory structure
    summary_dir = os.path.join(base_dir, "SUMMARY")
    summary_csv_dir = os.path.join(summary_dir, "csv")
    summary_images_dir = os.path.join(summary_dir, "images")
    os.makedirs(summary_csv_dir, exist_ok=True)
    os.makedirs(summary_images_dir, exist_ok=True)

    df_raw = fetch_trends(keyword.lower())
    df = df_raw.drop(columns=[c for c in df_raw.columns if c == "isPartial"])
    col = df.columns[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Summary CSV
    csv_name = f"summary_trends_{keyword.lower().replace(' ', '_')}_{ts}.csv"
    csv_path = os.path.join(summary_csv_dir, csv_name)
    df.to_csv(csv_path); ok(f"CSV → {csv_path}")
    upload_supabase(df.to_csv(index=True), csv_name, "chat-csv")

    banner("SUMMARY", Fore.BLUE)
    print(json.dumps({
        "rows": len(df),
        "range": f"{df.index[0].date()} → {df.index[-1].date()}",
        "avg": round(df[col].mean(), 1),
        "peak": int(df[col].max()),
        "peak_date": str(df[col].idxmax().date()),
        "min": int(df[col].min())
    }, indent=2))

    # Summary Plot
    fig, ax = plt.subplots(figsize=(12,6))
    ax.plot(df.index, df[col], marker="o", linewidth=2, color="green")
    ax.set_title(f"{keyword.title()} · Google search interest (90 days)")
    ax.set_ylabel("Score (0–100)")
    fig.autofmt_xdate()
    fig.tight_layout()
    png_name = f"summary_trends_plot_{keyword.lower().replace(' ', '_')}_{ts}.png"
    png_path = os.path.join(summary_images_dir, png_name)
    fig.savefig(png_path, dpi=300); ok(f"PNG → {png_path}")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    upload_supabase(buf.getvalue(), png_name, "chat-images")
    plt.close(fig)

    return df

def extra_insights(keyword: str, base_dir: str = None):
    """
    Performs extra insights analysis (regional interest) and saves/plots results.
    - keyword: search term
    - base_dir: Base directory for output files. If None, uses google_trends_data in current directory.
    """
    # Set default base_dir to google_trends_data if not provided
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google_trends_data")
    
    banner(f"EXTRA INSIGHTS · {keyword.upper()}", Fore.MAGENTA)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Directory setup
    extra_csv_dir = os.path.join(base_dir, "EXTRA_INSIGHTS", "csv")
    regional_csv_dir = os.path.join(base_dir, "REGIONAL_INTEREST", "csv")
    extra_img_dir = os.path.join(base_dir, "EXTRA_INSIGHTS", "images")
    regional_img_dir = os.path.join(base_dir, "REGIONAL_INTEREST", "images")
    ensure_dirs(extra_csv_dir, extra_img_dir, regional_csv_dir, regional_img_dir)
    
    # ─── REGIONAL INTEREST ANALYSIS ───────────────────────────────
    banner("REGIONAL INTEREST")
    
    # Get a proxy for this analysis
    proxy = get_current_proxy(proxy_rotator)  # Using imported function
    info(f"Initializing TrendReq with proxy: {proxy}")
    pt = get_trendreq(proxy)
    
    for attempt in range(3):
        try:
            info("Fetching regional interest data...")
            pt.build_payload([keyword], timeframe="today 3-m")
            region = pt.interest_by_region(resolution="COUNTRY")
            if region is not None and not region.empty:
                print("\nTop Countries by Interest:")
                print(region.sort_values(by=keyword, ascending=False).head(10).to_string())
                fname = f"regional_interest_countries_{keyword.lower()}_{ts}.csv"
                path = os.path.join(regional_csv_dir, fname)
                save_and_upload(region, path, fname, "chat-csv")
                # Plot
                fig, ax = plt.subplots(figsize=(12, 6))
                top_10 = region.sort_values(by=keyword, ascending=False).head(10)
                top_10.plot(kind='bar', ax=ax)
                ax.set_title(f"Top Countries Interested in {keyword.title()}")
                ax.set_ylabel("Interest Score (0-100)")
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                img_fname = f"regional_interest_countries_plot_{keyword.lower()}_{ts}.png"
                img_path = os.path.join(regional_img_dir, img_fname)
                save_fig_and_upload(fig, img_path, img_fname, "chat-images")
                break
            else:
                warn("No regional interest data available")
                print("No regional interest data available.")
                break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                warn(f"Rate limit hit (attempt {attempt+1}/3), retrying...")
                time.sleep(random.uniform(10, 15))
                proxy = get_current_proxy()
                info(f"Retrying with new proxy: {proxy}")
                pt = get_trendreq(proxy)
                pt.build_payload([keyword], timeframe="today 3-m")
            else:
                warn(f"Regional interest error: {str(e)}")
                print(f"Regional interest error: {str(e)}")
                break
