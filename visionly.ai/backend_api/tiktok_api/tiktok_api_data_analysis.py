# tiktok_api_data_analysis.py
import os, json, re, io
from collections import Counter
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from pmdarima import auto_arima                    # simple quantitative model
from colorama import Fore, Style, init as c_init
from dotenv import load_dotenv
from supabase import create_client

c_init(autoreset=True)   # colour support

# Initialize Supabase client
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_API_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# ─────────────────────────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────────────────────────
def ts():                       # timestamp helper
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def banner(msg, colour=Fore.CYAN):
    line = "─" * 70
    print(colour + line + Style.RESET_ALL)
    print(colour + f"{msg}" + Style.RESET_ALL)
    print(colour + line + Style.RESET_ALL)

def upload_to_supabase(file_data, filename, bucket_name):
    """Upload file to Supabase bucket"""
    if not supabase:
        print(f"{Fore.YELLOW}⚠ Supabase credentials missing – skipping upload")
        return
    
    try:
        # If file_data is a string (CSV), convert to bytes
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')
        
        # Add tiktok_api prefix to filename if not already present
        if 'tiktok_api' not in filename:
            name, ext = os.path.splitext(filename)
            filename = f"tiktok_api_{name}_{ts()}{ext}"
        
        # Upload to Supabase
        supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": "text/csv" if filename.endswith('.csv') else "image/png"}
        )
        
        # Get public URL
        url = supabase.storage.from_(bucket_name).get_public_url(filename)
        print(f"{Fore.GREEN}✓{Style.RESET_ALL} File uploaded to Supabase: {Fore.CYAN}{url}{Style.RESET_ALL}")
        return url
            
    except Exception as e:
        print(f"{Fore.RED}✗{Style.RESET_ALL} Error uploading to Supabase: {str(e)}")
        return None

# ─────────────────────────────────────────────────────────────
#  PRE-PROCESS
# ─────────────────────────────────────────────────────────────
def preprocess(path: str) -> pd.DataFrame:
    df = pd.read_json(path)
    df["createTime"] = pd.to_datetime(df["createTimeISO"], errors="coerce")
    df = df.dropna(subset=["createTime"])
    df = df[df["playCount"] > 100]          # noise filter
    df["engagementRate"] = (
        (df["diggCount"] + df["commentCount"] + df["shareCount"]) / df["playCount"]
    ) * 100
    df["viralityIndex"] = df["shareCount"] / (df["diggCount"] + 1e-9)
    df["hashtags"] = df["text"].apply(lambda t: re.findall(r"#\w+", t))
    return df.reset_index(drop=True)

# ─────────────────────────────────────────────────────────────
#  ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────────────────────
def hashtag_stats(df):
    return pd.DataFrame(
        Counter(tag for tags in df["hashtags"] for tag in tags).most_common(30),
        columns=["Hashtag", "Count"]
    )

def sentiment_stats(df):
    sid = SentimentIntensityAnalyzer()
    df["sentimentScore"] = df["text"].apply(lambda t: sid.polarity_scores(t)["compound"])
    return df[["text", "sentimentScore"]].copy(), df["sentimentScore"].mean()

def engagement_stats(df):
    stats = {
        "total_posts": len(df),
        "total_plays": df["playCount"].sum(),
        "total_likes": df["diggCount"].sum(),
        "total_comments": df["commentCount"].sum(),
        "total_shares": df["shareCount"].sum(),
        "avg_engagement_rate": df["engagementRate"].mean(),
        "avg_virality": df["viralityIndex"].mean(),
        "date_range": {
            "start": df["createTime"].min().strftime("%Y-%m-%d"),
            "end": df["createTime"].max().strftime("%Y-%m-%d")
        }
    }
    return pd.DataFrame([stats])

# ─────────────────────────────────────────────────────────────
#  FILE GENERATORS (CSV + PNG per topic, with prefix+timestamp)
# ─────────────────────────────────────────────────────────────
def save_csv(df, folder, prefix):
    fname = f"tiktok_api_{prefix}_{ts()}.csv"
    path  = os.path.join(folder, fname)
    df.to_csv(path, index=False)
    print(Fore.GREEN + f"CSV  → {path}")
    
    # Upload to Supabase
    csv_data = df.to_csv(index=False)
    upload_to_supabase(csv_data, fname, "chat-csv")
    
    return path

def save_plot(fig, folder, prefix):
    fname = f"tiktok_api_{prefix}_{ts()}.png"
    path  = os.path.join(folder, fname)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(Fore.GREEN + f"PNG  → {path}")
    
    # Upload to Supabase
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    upload_to_supabase(buf.getvalue(), fname, "chat-images")
    
    return path

# ─────────────────────────────────────────────────────────────
#  MAIN ENTRY
# ─────────────────────────────────────────────────────────────
def analyze_data(json_path: str, analysed_root: str):
    banner(f"START  TikTok analysis for {os.path.basename(json_path)}", Fore.MAGENTA)

    # build sub-folders
    folders = {
        "hashtags": os.path.join(analysed_root, "hashtag_analysis"),
        "sentiment": os.path.join(analysed_root, "sentiment_analysis"),
        "engagement": os.path.join(analysed_root, "engagement_metrics"),
        "chatgpt": os.path.join(analysed_root, "chatgpt_logs")
    }
    for p in folders.values():
        os.makedirs(p, exist_ok=True)

    # PREP
    df = preprocess(json_path)
    
    print(f"\n{Fore.CYAN}Analyzing complete dataset from {df['createTime'].min().strftime('%Y-%m-%d')} to {df['createTime'].max().strftime('%Y-%m-%d')}")

    # ───────── OVERALL STATS
    stats_df = engagement_stats(df)
    save_csv(stats_df, folders["engagement"], "overall_metrics")
    
    # Print summary
    print(f"\n{Fore.CYAN}Overall Metrics:")
    print(f"Total Posts: {stats_df['total_posts'].iloc[0]:,}")
    print(f"Total Plays: {stats_df['total_plays'].iloc[0]:,}")
    print(f"Total Likes: {stats_df['total_likes'].iloc[0]:,}")
    print(f"Total Comments: {stats_df['total_comments'].iloc[0]:,}")
    print(f"Average Engagement Rate: {stats_df['avg_engagement_rate'].iloc[0]:.2f}%")

    # ───────── HASHTAGS
    print(f"\n{Fore.CYAN}Analyzing Hashtags...")
    tag_df = hashtag_stats(df)
    save_csv(tag_df, folders["hashtags"], "hashtag")
    
    fig = plt.figure(figsize=(12, 6))
    plt.bar(tag_df.head(15)["Hashtag"], tag_df.head(15)["Count"], color="#1f77b4")
    plt.title("Top 15 Co-occurring Hashtags")
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Frequency")
    save_plot(fig, folders["hashtags"], "hashtag")

    # ───────── SENTIMENT
    print(f"\n{Fore.CYAN}Analyzing Sentiment...")
    sent_df, mean_sent = sentiment_stats(df)
    save_csv(sent_df, folders["sentiment"], "sentiment")
    
    fig = plt.figure(figsize=(12, 6))
    plt.hist(sent_df["sentimentScore"], bins=20, color="#ff7f0e")
    plt.title("Content Sentiment Distribution")
    plt.xlabel("Sentiment Score (-1 to 1)")
    plt.ylabel("Number of Posts")
    save_plot(fig, folders["sentiment"], "sentiment")

    # ───────── ENGAGEMENT DISTRIBUTION
    print(f"\n{Fore.CYAN}Analyzing Engagement Distribution...")
    fig = plt.figure(figsize=(12, 6))
    plt.scatter(df["playCount"], df["diggCount"], alpha=0.5)
    plt.title("Views vs Likes Distribution")
    plt.xlabel("Views")
    plt.ylabel("Likes")
    save_plot(fig, folders["engagement"], "engagement_scatter")

    # ───────── SUMMARY JSON
    summary = {
        "overall_metrics": stats_df.iloc[0].to_dict(),
        "sentiment_metrics": {
            "average_sentiment": round(mean_sent, 3),
            "positive_posts": int(sum(sent_df["sentimentScore"] > 0.2)),
            "neutral_posts": int(sum((sent_df["sentimentScore"] >= -0.2) & (sent_df["sentimentScore"] <= 0.2))),
            "negative_posts": int(sum(sent_df["sentimentScore"] < -0.2))
        },
        "top_hashtags": tag_df.head(10).to_dict("records"),
        "top_performing_posts": df.nlargest(10, "engagementRate")[
            ["text", "playCount", "diggCount", "commentCount", "shareCount", "engagementRate"]
        ].to_dict("records"),
        "timestamp": datetime.utcnow().isoformat(timespec="seconds")
    }
    
    out_js = os.path.join(folders["chatgpt"], f"tiktok_api_summary_{ts()}.json")
    with open(out_js, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    print(f"\n{Fore.GREEN}Complete analysis summary → {out_js}")
    
    # Upload summary to Supabase
    upload_to_supabase(json.dumps(summary, indent=4), os.path.basename(out_js), "chat-csv")

    banner("ANALYSIS COMPLETE", Fore.MAGENTA)
    print(f"\n{Fore.GREEN}✓ Files have been uploaded to Supabase buckets:")
    print("- CSV files in 'chat-csv' bucket")
    print("- Images in 'chat-images' bucket")

# ------------------------------------------------------------
# Stand-alone test (optional)
# ------------------------------------------------------------
if __name__ == "__main__":
    BASE = os.path.dirname(__file__)
    DEMO = os.path.join(BASE, "data", "demo.json")          # put a small demo file
    analyze_data(DEMO, os.path.join(BASE, "analysed_data"))