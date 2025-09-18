# meta_api_data_analysis.py  – robust multi-model (ARIMA / fallback) forecasting
import os, json, re, warnings, io
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from pmdarima import auto_arima
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from colorama import Fore, Style, init as c_init
from dotenv import load_dotenv
from supabase import create_client

c_init(autoreset=True)
warnings.filterwarnings("ignore")          # silence sklearn & glyph spam

# Initialize Supabase client
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_API_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# ────── helpers ────────────────────────────────────────────────────────────
def ts() -> str: return datetime.now().strftime("%Y%m%d_%H%M%S")
def banner(msg, col=Fore.CYAN):
    bar = "═" * 72
    print(col + bar + Style.RESET_ALL)
    print(col + msg  + Style.RESET_ALL)
    print(col + bar + Style.RESET_ALL)

def upload_to_supabase(file_data, filename, bucket_name):
    """Upload file to Supabase bucket"""
    if not supabase:
        print(f"{Fore.YELLOW}⚠ Supabase credentials missing – skipping upload")
        return
    
    try:
        # If file_data is a string (CSV), convert to bytes
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')
        
        # Add meta_api prefix to filename if not already present
        if 'meta_api' not in filename:
            name, ext = os.path.splitext(filename)
            filename = f"meta_api_{name}_{ts()}{ext}"
        
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

def save_csv(df, folder, tag):
    fname = f"meta_api_{tag}_{ts()}.csv"
    path = os.path.join(folder, fname)
    df.to_csv(path, index=False)
    print(Fore.GREEN + f"CSV  → {path}")
    
    # Upload to Supabase
    csv_data = df.to_csv(index=False)
    upload_to_supabase(csv_data, fname, "chat-csv")
    
    return path

def save_fig(fig, folder, tag):
    fname = f"meta_api_{tag}_{ts()}.png"
    path = os.path.join(folder, fname)
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

# ────── preprocess ────────────────────────────────────────────────────────
def preprocess(path: str) -> pd.DataFrame:
    df = pd.read_json(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df[df["likesCount"] > 0]
    df["hour"] = df["timestamp"].dt.floor("h")
    df["caption"] = df["caption"].fillna("")
    return df.reset_index(drop=True)

# ────── metrics ───────────────────────────────────────────────────────────
def hashtags(df):
    c = Counter(
        ht
        for row in df["hashtags"]
        for ht in (row if isinstance(row, list) else [])
    )
    return pd.DataFrame(c.most_common(30), columns=["Hashtag", "Count"])

def sentiments(df):
    sid = SentimentIntensityAnalyzer()
    df["sentiment"] = df["caption"].apply(lambda t: sid.polarity_scores(t)["compound"])
    return df[["caption", "sentiment"]], df["sentiment"].mean()

def hourly_likes(df):
    hourly = df.groupby("hour").agg(totalLikes=("likesCount","sum")).reset_index()
    rng = pd.date_range(hourly["hour"].min(), hourly["hour"].max(), freq="h")
    hourly = (hourly.set_index("hour")
                     .reindex(rng, fill_value=0)
                     .rename_axis("hour").reset_index())
    return hourly

# ────── forecasting logic ─────────────────────────────────────────────────
def forecast_series(series: pd.Series, periods=12):
    """
    Try auto_arima ; then ARIMA(1,0,0) ; then Holt-Winters.
    Always return an ndarray of length = periods.
    """
    try:
        m = auto_arima(series, seasonal=False, suppress_warnings=True)
        print(Fore.GREEN + "auto_arima chosen.")
        return m.predict(n_periods=periods)
    except Exception as e1:
        print(Fore.YELLOW + f"auto_arima failed ({e1}). Trying ARIMA(1,0,0)…")
        try:
            m = ARIMA(series, order=(1,0,0)).fit()
            print(Fore.GREEN + "ARIMA(1,0,0) chosen.")
            return m.forecast(periods)
        except Exception as e2:
            print(Fore.YELLOW + f"ARIMA(1,0,0) failed ({e2}). Using Holt-Winters…")
            try:
                m = ExponentialSmoothing(series, trend="add").fit()
                print(Fore.GREEN + "Holt-Winters chosen.")
                return m.forecast(periods)
            except Exception as e3:
                print(Fore.RED + f"All models failed ({e3}). Returning zeros.")
                return np.zeros(periods)

def forecast_and_plot(hourly, folder):
    fc_vals = forecast_series(hourly["totalLikes"], 12)
    future = pd.date_range(hourly["hour"].iloc[-1] + pd.Timedelta(hours=1), periods=12, freq="h")
    fc_df = pd.DataFrame({"hour": future, "forecastLikes": fc_vals})
    save_csv(fc_df, folder, "likes_forecast")

    fig = plt.figure(figsize=(10,4))
    plt.plot(hourly["hour"], hourly["totalLikes"], marker="o", label="Actual", color="#2ca02c")
    plt.plot(fc_df["hour"], fc_df["forecastLikes"], marker="x", linestyle="--",
             label="Forecast", color="#d62728")
    plt.xticks(rotation=45); plt.title("Hourly Likes – 12-hour forecast"); plt.legend()
    save_fig(fig, folder, "likes_forecast")

# ────── main ──────────────────────────────────────────────────────────────
def analyze_meta_data(json_path: str, root_out: str):
    banner("META HASHTAG ANALYSIS", Fore.MAGENTA)

    sub = {k: os.path.join(root_out, k) for k in
           ("hashtag_analysis", "sentiment_analysis",
            "engagement_metrics", "chatgpt_logs")}
    for p in sub.values(): os.makedirs(p, exist_ok=True)

    df = preprocess(json_path)
    
    print(f"\n{Fore.CYAN}Analyzing complete dataset from {df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}")

    # Overall metrics
    total_posts = len(df)
    total_likes = df["likesCount"].sum()
    total_comments = df["commentsCount"].sum()
    avg_likes = df["likesCount"].mean()
    avg_comments = df["commentsCount"].mean()
    
    print(f"\n{Fore.CYAN}Overall Metrics:")
    print(f"Total Posts: {total_posts}")
    print(f"Total Likes: {total_likes:,}")
    print(f"Total Comments: {total_comments:,}")
    print(f"Average Likes per Post: {avg_likes:.1f}")
    print(f"Average Comments per Post: {avg_comments:.1f}")

    # Hashtag Analysis
    print(f"\n{Fore.CYAN}Analyzing Hashtags...")
    hdf = hashtags(df)
    save_csv(hdf, sub["hashtag_analysis"], "hashtags")
    
    # Create hashtag visualization
    fig = plt.figure(figsize=(12, 6))
    plt.bar(hdf.head(15)["Hashtag"], hdf.head(15)["Count"], color="#1f77b4")
    plt.title("Top 15 Co-occurring Hashtags")
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Frequency")
    save_fig(fig, sub["hashtag_analysis"], "hashtags")

    # Sentiment Analysis
    print(f"\n{Fore.CYAN}Analyzing Sentiments...")
    s_df, mean_sent = sentiments(df)
    save_csv(s_df, sub["sentiment_analysis"], "sentiment")
    
    # Create sentiment visualization
    fig = plt.figure(figsize=(12, 6))
    plt.hist(s_df["sentiment"], bins=20, color="#ff7f0e")
    plt.title("Content Sentiment Distribution")
    plt.xlabel("Sentiment Score (-1 to 1)")
    plt.ylabel("Number of Posts")
    save_fig(fig, sub["sentiment_analysis"], "sentiment")

    # Engagement Analysis
    print(f"\n{Fore.CYAN}Analyzing Engagement...")
    df["engagement_rate"] = (df["likesCount"] + df["commentsCount"]) / 2
    
    # Save top performing posts
    top_posts = df.nlargest(10, "engagement_rate")[
        ["caption", "likesCount", "commentsCount", "engagement_rate"]
    ]
    save_csv(top_posts, sub["engagement_metrics"], "top_posts")
    
    # Create engagement visualization
    fig = plt.figure(figsize=(12, 6))
    plt.scatter(df["likesCount"], df["commentsCount"], alpha=0.5)
    plt.title("Likes vs Comments Distribution")
    plt.xlabel("Number of Likes")
    plt.ylabel("Number of Comments")
    save_fig(fig, sub["engagement_metrics"], "engagement_scatter")

    # Generate comprehensive summary
    summary = {
        "overall_metrics": {
            "total_posts": total_posts,
            "total_likes": int(total_likes),
            "total_comments": int(total_comments),
            "average_likes": round(avg_likes, 2),
            "average_comments": round(avg_comments, 2),
            "date_range": {
                "start": df["timestamp"].min().strftime("%Y-%m-%d"),
                "end": df["timestamp"].max().strftime("%Y-%m-%d")
            }
        },
        "sentiment_metrics": {
            "average_sentiment": round(mean_sent, 3),
            "positive_posts": int(sum(s_df["sentiment"] > 0.2)),
            "neutral_posts": int(sum((s_df["sentiment"] >= -0.2) & (s_df["sentiment"] <= 0.2))),
            "negative_posts": int(sum(s_df["sentiment"] < -0.2))
        },
        "top_hashtags": hdf.head(10).to_dict("records"),
        "top_performing_posts": top_posts.to_dict("records"),
        "timestamp": datetime.utcnow().isoformat(timespec="seconds")
    }
    
    # Save summary
    out_js = os.path.join(sub["chatgpt_logs"], f"meta_api_summary_{ts()}.json")
    with open(out_js, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    print(f"\n{Fore.GREEN}Complete analysis summary → {out_js}")
    
    # Upload summary to Supabase
    upload_to_supabase(json.dumps(summary, indent=4), os.path.basename(out_js), "chat-csv")

    banner("ANALYSIS COMPLETE", Fore.MAGENTA)
    print(f"\n{Fore.GREEN}✓ Files have been uploaded to Supabase buckets:")
    print("- CSV files in 'chat-csv' bucket")
    print("- Images in 'chat-images' bucket")

# stand-alone quick test
if __name__ == "__main__":
    base = os.path.dirname(__file__)
    demo = os.path.join(base, "data", "demo_meta.json")
    analyze_meta_data(demo, os.path.join(base, "analysed_data"))