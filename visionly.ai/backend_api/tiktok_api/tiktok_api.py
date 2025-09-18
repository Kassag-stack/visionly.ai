# tiktok_api.py
import os, json, argparse
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient
from colorama import Fore, Style, init as colourama_init
from .tiktok_api_data_analysis import analyze_data  # analysis function
from typing import List, Dict, Any, Optional

colourama_init(autoreset=True)

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RAW_DIR       = os.path.join(BASE_DIR, "data")
ANALYSED_DIR  = os.path.join(BASE_DIR, "analysed_data")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(ANALYSED_DIR, exist_ok=True)

# ── API  ────────────────────────────────────────────────────────────────
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError(Fore.RED + "API_TOKEN missing in .env")
print(Fore.GREEN + "API token loaded.")

client = ApifyClient(API_TOKEN)

# ── Fields to strip from raw TikTok rows ────────────────────────────────
FIELDS_TO_REMOVE = {
    "musicMeta","mentions","isSponsored","videoMeta","isSlideshow","hashtags",
    "textLanguage","webVideoUrl","mediaUrls","isMuted","authorMeta","musicInfo",
    "locationName","locationId","timestamp","inputUrl","id","type","shortCode",
    "url","firstComment","latestComments","dimensionsHeight","dimensionsWidth",
    "displayUrl","images","childPosts","ownerFullName","ownerUsername","ownerId",
    "productType","music_info","original_sound_info","pinned_media_ids",
    "coauthorProducers","createTime","isAd","detailedMentions","effectStickers",
    "isPinned"
}

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="TikTok Hashtag Analysis")
    parser.add_argument("hashtag", help="Hashtag to analyze (without #)")
    parser.add_argument("-n", "--num-results", type=int, default=20,
                      help="Total number of results to fetch (default: 20)")
    parser.add_argument("--raw-dir", help="Raw data directory", default=RAW_DIR)
    parser.add_argument("--analysis-dir", help="Analysis output directory", default=ANALYSED_DIR)
    return parser.parse_args()

# ── Helpers ─────────────────────────────────────────────────────────────
def _clean(obj):
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if k not in FIELDS_TO_REMOVE}
    return obj

def save_json(rows, fname) -> str | None:
    try:
        path = os.path.join(RAW_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_clean(rows), f, indent=4, ensure_ascii=False)
        print(Fore.GREEN + f"Saved {len(rows):,} rows → {path}")
        return path
    except Exception as e:
        print(Fore.RED + f"JSON save error: {e}")
        return None

# ── Main Fetch & Analyse ───────────────────────────────────────────────
def fetch_tiktok(
    hashtags: List[str] = None,
    num_results: int = 20,
    raw_dir: str = RAW_DIR,
    analysis_dir: str = ANALYSED_DIR
) -> None:
    """
    Fetch and analyze TikTok data for given hashtags
    Args:
        hashtags: List of hashtags to analyze (without #)
        num_results: Total number of results to fetch
        raw_dir: Directory for raw data
        analysis_dir: Directory for analysis output
    """
    try:
        print(Fore.CYAN + "▶ Launching Apify actor…")
        
        # Ensure we have a single string hashtag
        hashtag = hashtags[0] if hashtags else "matcha"
        hashtag = hashtag.lstrip('#')  # Remove '#' if present
        
        print(Fore.CYAN + f'▶ Analyzing hashtags: "{hashtag}"')
        print(Fore.CYAN + f"▶ Fetching {num_results} results")
        
        run_input = {
            "hashtags": [hashtag],  # Pass as a single-item list
            "resultsPerPage": num_results,
            "profileSorting": "latest",
            "maxProfilesPerQuery": 1,
            "excludePinnedPosts": True,
            "shouldDownloadVideos": False,
            "proxyCountryCode": "None"
        }
        
        run = client.actor("GdWCkxBtKWOsKjdch").call(run_input=run_input)
        rows = [it for it in client.dataset(run["defaultDatasetId"]).iterate_items()]
        print(Fore.YELLOW + f"✔  {len(rows):,} items fetched.")

        filename  = f"tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_path = save_json(rows, filename)

        if json_path:
            print(Fore.CYAN + "▶ Launching analysis …")
            analyze_data(json_path, analysis_dir)
        else:
            print(Fore.RED + "✖ Could not save JSON; analysis skipped.")
    except Exception as e:
        print(Fore.RED + f"Fetch failed: {e}")

def main():
    """Main entry point"""
    args = parse_arguments()
    fetch_tiktok(
        hashtags=[args.hashtag],
        num_results=args.num_results,
        raw_dir=args.raw_dir,
        analysis_dir=args.analysis_dir
    )

# ── Entrypoint ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()