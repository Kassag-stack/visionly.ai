from fastapi import FastAPI, Request
import uvicorn
import json
import sys
import os
from pathlib import Path
import tempfile

# Add parent directory to Python path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend_api_backup.combined_insight.insight_merge_and_prompt import ShopifyInsightGenerator
import backend_api_backup.combined_insight.insight_merge_and_prompt as insight_module

app = FastAPI()

def get_visualization_files():
    """Get the visualization files structure"""
    return {
        "TikTok": {
            "engagement": str(Path(parent_dir) / "backend_api_backup/tiktok_api/analysed_data/engagement_trends/tiktok_api_engagement_forecast_20250621_130732.png"),
            "hashtag": str(Path(parent_dir) / "backend_api_backup/tiktok_api/analysed_data/hashtag_analysis/tiktok_api_hashtag_20250621_183532.png"),
            "sentiment": str(Path(parent_dir) / "backend_api_backup/tiktok_api/analysed_data/sentiment_analysis/tiktok_api_sentiment_20250621_183533.png")
        },
        "Meta": {
            "engagement": str(Path(parent_dir) / "backend_api_backup/meta_api/analysed_data/engagement_metrics/meta_api_engagement_scatter_20250621_183609.png"),
            "hashtag": str(Path(parent_dir) / "backend_api_backup/meta_api/analysed_data/hashtag_analysis/meta_api_hashtags_20250621_183608.png"),
            "likes": str(Path(parent_dir) / "backend_api_backup/meta_api/analysed_data/likes_trends/meta_api_likes_hourly_20250621_130027.png"),
            "sentiment": str(Path(parent_dir) / "backend_api_backup/meta_api/analysed_data/sentiment_analysis/meta_api_sentiment_20250621_183609.png")
        },
        "News": {
            "sentiment": str(Path(parent_dir) / "backend_api_backup/news_api/news_analysis_data/images/news_api_snowboard_market_sentiment_visualization_20250621_165122.png"),
            "wordcloud": str(Path(parent_dir) / "backend_api_backup/news_api/news_analysis_data/images/news_api_snowboard_market_wordcloud_20250621_165122.png")
        },
        "Finance": {
            "stats": str(Path(parent_dir) / "backend_api_backup/finance_api/analysed_data/finance_logs/images/finance_api_USD_JPY_20250621_135225_stats.png"),
            "timeseries": str(Path(parent_dir) / "backend_api_backup/finance_api/analysed_data/finance_logs/images/finance_api_USD_JPY_20250621_135225_timeseries.png")
        }
    }

@app.post("/api/chat/completions")
async def chat_completions(request: Request):
    try:
        # Get the received data
        data = await request.json()
        print("Received request data:", json.dumps(data, indent=2))
        
        # Create a temporary file to store the received data
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(data['message'], temp_file)
            temp_path = temp_file.name
        
        try:
            # Temporarily override the SHOPIFY_DATA_PATH in the module
            original_path = insight_module.SHOPIFY_DATA_PATH
            insight_module.SHOPIFY_DATA_PATH = Path(temp_path)
            
            # Initialize the insight generator and run analysis
            generator = ShopifyInsightGenerator()
            insights = generator.run_analysis()
            
            if insights:
                return {
                    "status": "success",
                    "insights": insights,
                    "generated_visualization_files": get_visualization_files()
                }
            else:
                return {
                    "status": "error",
                    "message": "No insights were generated. Please check the input data and try again.",
                    "generated_visualization_files": get_visualization_files()
                }
            
        finally:
            # Restore the original path and clean up
            insight_module.SHOPIFY_DATA_PATH = original_path
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "details": {
                "traceback": traceback.format_exc()
            },
            "generated_visualization_files": get_visualization_files()
        }

if __name__ == "__main__":
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)

