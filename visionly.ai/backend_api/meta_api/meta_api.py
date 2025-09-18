"""
Fetch Instagram / Meta hashtag posts via Apify, remove unwanted
fields, save cleaned JSON to /data, then trigger meta_api_data_analysis.py
"""
import os, json, requests, argparse
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init as c_init
from apify_client import ApifyClient
from typing import List
from .meta_api_data_analysis import analyze_meta_data

# ─── setup ──────────────────────────────────────────────────────────────────
c_init(autoreset=True)
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN not found in .env")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_DIR    = os.path.join(BASE_DIR, "data")
AN_DIR     = os.path.join(BASE_DIR, "analysed_data")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(AN_DIR,  exist_ok=True)

ACTOR_ID   = "reGe1ST3OBgYZSsZJ"                 # Meta-scraper actor

FIELDS_TO_REMOVE = {
    "inputUrl","id","dimensionsHeight","dimensionsWidth","locationName",
    "productType","type","shortCode","url","displayUrl","locationid",
    "ownerFullName","isSponsored","musicinfo","musicInfo","firstComment",
    "images","ownerUsername","latestComments","childPosts","ownerld",
    "ownerId"
}

# ─── helper printing ───────────────────────────────────────────────────────
def banner(msg, colour=Fore.CYAN):
    line = "═"*65
    print(colour + line + Style.RESET_ALL)
    print(colour + msg  + Style.RESET_ALL)
    print(colour + line + Style.RESET_ALL)

# ─── cleaning ──────────────────────────────────────────────────────────────
def clean(obj):
    if isinstance(obj, list):
        return [clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items() if k not in FIELDS_TO_REMOVE}
    return obj

def save_json(objs):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"meta_hashtag_{ts}.json"
    path  = os.path.join(RAW_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(objs, f, indent=4, ensure_ascii=False)
    print(Fore.GREEN + f"✓ Cleaned JSON saved → {path}")
    return path

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Meta/Instagram Hashtag Analysis")
    parser.add_argument("hashtags", nargs="*", help="Hashtags to analyze (without #)")
    parser.add_argument("-l", "--limit", type=int, default=30, help="Number of results to fetch (default: 30)")
    parser.add_argument("--raw-dir", help="Raw data directory", default=RAW_DIR)
    parser.add_argument("--analysis-dir", help="Analysis output directory", default=AN_DIR)
    return parser.parse_args()

# ─── main fetch ────────────────────────────────────────────────────────────
def fetch_and_analyse(hashtags: List[str] = None, results_limit: int = 30, raw_dir: str = RAW_DIR, analysis_dir: str = AN_DIR):
    """
    Fetch and analyze hashtag data
    Args:
        hashtags: List of hashtags to analyze (without #)
        results_limit: Number of results to fetch per hashtag
        raw_dir: Directory for raw data
        analysis_dir: Directory for analysis output
    """
    banner("META  HASHTAG  FETCH", Fore.MAGENTA)
    client = ApifyClient(API_TOKEN)

    # Use provided hashtags or default to ["matcha"]
    hashtags = hashtags if hashtags else ["matcha"]
    
    # Remove '#' if present in hashtags
    hashtags = [tag.lstrip('#') for tag in hashtags]

    run_input = {
        "hashtags"     : hashtags,
        "resultsType"  : "posts",
        "resultsLimit" : results_limit
    }

    print(Fore.CYAN + "▶ Launching Apify actor…")
    print(Fore.CYAN + f"▶ Analyzing hashtags: {', '.join(hashtags)}")
    print(Fore.CYAN + f"▶ Fetching {results_limit} results per hashtag")
    
    run = client.actor(ACTOR_ID).call(run_input=run_input)

    raw_items = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]
    print(Fore.GREEN + f"✓ {len(raw_items)} items fetched")

    cleaned_items = clean(raw_items)
    path = save_json(cleaned_items)

    # trigger analysis
    analyze_meta_data(path, analysis_dir)

    banner("META FETCH + ANALYSIS COMPLETE", Fore.GREEN)

def main():
    """Main entry point"""
    args = parse_arguments()
    fetch_and_analyse(
        hashtags=args.hashtags,
        results_limit=args.limit,
        raw_dir=args.raw_dir,
        analysis_dir=args.analysis_dir
    )

if __name__ == "__main__":
    main()