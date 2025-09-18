from datetime import datetime
import os
import io
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import random
from typing import Optional, Dict, Any

from .trends_helpers import (
    banner, info, warn, err, ok,
    Colors, timestamp, get_output_paths, ensure_dirs
)
from .trends_fetch import TrendsClient
from .supabase_utils import upload_supabase

class TrendsAnalyzer:
    """Handles analysis and visualization of Google Trends data"""
    
    def __init__(self, base_dir: str, proxy_rotator=None):
        self.base_dir = base_dir
        self.client = TrendsClient(proxy_rotator)
        
    def save_and_upload(self, df: pd.DataFrame, path: str, fname: str, bucket: str) -> None:
        """
        Save DataFrame to CSV and upload to Supabase
        Args:
            df: DataFrame to save
            path: Local file path
            fname: Filename for Supabase
            bucket: Supabase bucket name
        """
        df.to_csv(path)
        ok(f"CSV → {path}")
        upload_supabase(df.to_csv(), fname, "chat-csv")
    
    def save_plot_and_upload(self, fig: plt.Figure, path: str, fname: str, bucket: str) -> None:
        """
        Save matplotlib figure and upload to Supabase
        Args:
            fig: Figure to save
            path: Local file path
            fname: Filename for Supabase
            bucket: Supabase bucket name
        """
        fig.savefig(path, dpi=300, bbox_inches='tight')
        ok(f"PNG → {path}")
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        buf.seek(0)
        upload_supabase(buf.getvalue(), fname, "chat-images")
        plt.close(fig)
    
    def save_json_summary(self, keyword: str, summary_data: Dict, regional_data: Optional[pd.DataFrame], ts: str) -> None:
        """
        Save summary and regional data as JSON
        Args:
            keyword: Search term analyzed
            summary_data: Dictionary containing summary statistics
            regional_data: DataFrame with regional interest data
            ts: Timestamp string
        """
        # Convert trend data timestamps to strings
        if "trend_data" in summary_data:
            trend_data = {}
            for timestamp, value in summary_data["trend_data"].items():
                trend_data[timestamp.strftime("%Y-%m-%d %H:%M:%S")] = value
            summary_data["trend_data"] = trend_data
        
        json_data = {
            "keyword": keyword,
            "timestamp": ts,
            "summary": summary_data,
            "regional_interest": None if regional_data is None else regional_data.to_dict(orient="records")
        }
        
        # Create chatgpt_json directory if it doesn't exist
        json_dir = os.path.join(self.base_dir, "chatgpt_json")
        os.makedirs(json_dir, exist_ok=True)
        
        # Save JSON file
        json_name = f"summary_trends_{keyword.lower()}_{ts}.json"
        json_path = os.path.join(json_dir, json_name)
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        ok(f"JSON → {json_path}")
        
        # Upload to Supabase
        upload_supabase(json.dumps(json_data, indent=2), json_name, "chat-csv")
    
    def analyze_keyword(self, keyword: str) -> pd.DataFrame:
        """
        Analyze Google Trends data for a keyword
        Args:
            keyword: Search term to analyze
        Returns:
            DataFrame with trend data
        """
        banner(f"GOOGLE TRENDS · {keyword.upper()}", Colors.HEADER)
        
        # Get standardized output paths
        ts = timestamp()
        paths = get_output_paths(self.base_dir, keyword, ts)
        
        # Fetch trend data
        df_raw = self.client.fetch_interest_over_time(keyword.lower())
        df = df_raw.drop(columns=[c for c in df_raw.columns if c == "isPartial"])
        col = df.columns[0]
        
        # Save trend data
        csv_name = f"summary_trends_{keyword.lower().replace(' ', '_')}_{ts}.csv"
        csv_path = os.path.join(paths["summary"]["csv"], csv_name)
        self.save_and_upload(df, csv_path, csv_name, "chat-csv")
        
        # Print summary statistics
        banner("SUMMARY", Colors.INFO)
        summary = {
            "rows": len(df),
            "range": f"{df.index[0].date()} → {df.index[-1].date()}",
            "avg": round(df[col].mean(), 1),
            "peak": int(df[col].max()),
            "peak_date": str(df[col].idxmax().date()),
            "min": int(df[col].min()),
            "trend_data": df[col].to_dict()
        }
        print(pd.Series(summary).to_string())
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(12,6))
        ax.plot(df.index, df[col], marker="o", linewidth=2, color="green")
        ax.set_title(f"{keyword.title()} · Google search interest (90 days)")
        ax.set_ylabel("Score (0–100)")
        fig.autofmt_xdate()
        fig.tight_layout()
        
        # Save plot
        png_name = f"summary_trends_plot_{keyword.lower().replace(' ', '_')}_{ts}.png"
        png_path = os.path.join(paths["summary"]["images"], png_name)
        self.save_plot_and_upload(fig, png_path, png_name, "chat-images")
        
        # Get regional data and save combined JSON
        regional_df = self.analyze_regional_interest(keyword)
        self.save_json_summary(keyword, summary, regional_df, ts)
        
        return df
    
    def analyze_regional_interest(self, keyword: str) -> Optional[pd.DataFrame]:
        """
        Analyze regional interest data for a keyword
        Args:
            keyword: Search term to analyze
        Returns:
            DataFrame with regional data if successful, None otherwise
        """
        banner("REGIONAL INTEREST", Colors.INFO)
        
        try:
            # Get regional data
            region_df = self.client.fetch_interest_by_region(keyword)
            
            if region_df is None or region_df.empty:
                warn("No regional interest data available")
                return None
            
            # Get output paths
            ts = timestamp()
            paths = get_output_paths(self.base_dir, keyword, ts)
            
            # Display top countries
            print("\nTop Countries by Interest:")
            print(region_df.sort_values(by=keyword, ascending=False).head(10).to_string())
            
            # Save data
            fname = f"regional_interest_countries_{keyword.lower()}_{ts}.csv"
            path = os.path.join(paths["regional"]["csv"], fname)
            self.save_and_upload(region_df, path, fname, "chat-csv")
            
            # Create visualization
            fig, ax = plt.subplots(figsize=(12, 6))
            top_10 = region_df.sort_values(by=keyword, ascending=False).head(10)
            top_10.plot(kind='bar', ax=ax)
            ax.set_title(f"Top Countries Interested in {keyword.title()}")
            ax.set_ylabel("Interest Score (0-100)")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save plot
            img_fname = f"regional_interest_countries_plot_{keyword.lower()}_{ts}.png"
            img_path = os.path.join(paths["regional"]["images"], img_fname)
            self.save_plot_and_upload(fig, img_path, img_fname, "chat-images")
            
            return region_df
            
        except Exception as e:
            err(f"Regional interest analysis failed: {str(e)}")
            return None

    def extra_insights(self, keyword: str) -> Dict[str, Any]:
        """
        Performs extra insights analysis (regional interest) and saves/plots results.
        Args:
            keyword: Search term to analyze
        Returns:
            Dictionary containing extra insights data
        """
        banner(f"EXTRA INSIGHTS · {keyword.upper()}", Colors.HEADER)
        ts = timestamp()
        
        # Directory setup
        extra_csv_dir = os.path.join(self.base_dir, "EXTRA_INSIGHTS", "csv")
        extra_img_dir = os.path.join(self.base_dir, "EXTRA_INSIGHTS", "images")
        ensure_dirs(extra_csv_dir, extra_img_dir)
        
        try:
            # Get regional interest data
            region_df = self.client.fetch_interest_by_region(keyword)
            
            if region_df is None or region_df.empty:
                warn("No extra insights data available")
                return {"error": "No data available"}
            
            # Save regional data
            fname = f"extra_insights_{keyword.lower()}_{ts}.csv"
            path = os.path.join(extra_csv_dir, fname)
            self.save_and_upload(region_df, path, fname, "chat-csv")
            
            # Create visualization
            fig, ax = plt.subplots(figsize=(12, 6))
            top_10 = region_df.sort_values(by=keyword, ascending=False).head(10)
            top_10.plot(kind='bar', ax=ax)
            ax.set_title(f"Extra Insights: Top Countries Interested in {keyword.title()}")
            ax.set_ylabel("Interest Score (0-100)")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save plot
            img_fname = f"extra_insights_plot_{keyword.lower()}_{ts}.png"
            img_path = os.path.join(extra_img_dir, img_fname)
            self.save_plot_and_upload(fig, img_path, img_fname, "chat-images")
            
            # Prepare insights data
            insights = {
                "keyword": keyword,
                "timestamp": ts,
                "top_countries": region_df.sort_values(by=keyword, ascending=False).head(10).to_dict(),
                "total_countries": len(region_df),
                "average_interest": round(region_df[keyword].mean(), 2),
                "median_interest": round(region_df[keyword].median(), 2)
            }
            
            # Save insights as JSON
            json_name = f"extra_insights_{keyword.lower()}_{ts}.json"
            json_path = os.path.join(self.base_dir, "chatgpt_json", json_name)
            with open(json_path, 'w') as f:
                json.dump(insights, f, indent=2)
            ok(f"Extra insights JSON → {json_path}")
            
            return insights
            
        except Exception as e:
            err(f"Extra insights analysis failed: {str(e)}")
            return {"error": str(e)} 