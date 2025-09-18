"""
Statistical Analysis Module for Combined API Insights
Processes and combines data from multiple sources using statistical modeling
"""

import json
import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from scipy import stats
from collections import defaultdict

class StatisticalInsightGenerator:
    def __init__(self, data_directory: str = "."):
        """Initialize the statistical insight generator
        
        Args:
            data_directory: Directory containing the JSON files to analyze
        """
        self.data_directory = Path(data_directory)
        self.combined_data = defaultdict(list)
        # Get current timestamp in the format used by the files (YYYYMMDD)
        self.current_run_date = datetime.now().strftime("%Y%m%d")
        # Store the most recent timestamp found in files
        self.most_recent_timestamp = None
        
    def _get_timestamp_from_filename(self, filename: str) -> str:
        """Extract timestamp from filename
        
        Args:
            filename: Name of the file
            
        Returns:
            Timestamp string in format YYYYMMDD_HHMMSS or None if not found
        """
        # Files have format like: *_20250621_144720.json
        parts = filename.split('_')
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():  # YYYYMMDD format
                if i + 1 < len(parts) and len(parts[i+1]) == 6 and parts[i+1].isdigit():  # HHMMSS format
                    return f"{part}_{parts[i+1]}"
        return None
        
    def _is_from_current_run(self, filepath: Path) -> bool:
        """Check if a file is from the current run by comparing timestamps
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file is from current run, False otherwise
        """
        timestamp = self._get_timestamp_from_filename(filepath.name)
        if not timestamp:
            return False
            
        # If this is the first file we're checking, set it as the most recent
        if not self.most_recent_timestamp:
            self.most_recent_timestamp = timestamp
            return True
            
        # If this file has the same timestamp as our most recent, include it
        if timestamp == self.most_recent_timestamp:
            return True
            
        # If this file is more recent than our current most recent, update and include it
        if timestamp > self.most_recent_timestamp:
            self.most_recent_timestamp = timestamp
            return True
            
        return False
    
    def load_json_files(self, pattern: str = "combined_api_results_*.json") -> None:
        """Load all JSON files matching the pattern from the current run
        
        Args:
            pattern: Glob pattern for JSON files to load
        """
        # First pass: find the most recent timestamp
        for file_path in self.data_directory.glob(pattern):
            self._is_from_current_run(file_path)
            
        # Second pass: load only files from the most recent run
        for file_path in self.data_directory.glob(pattern):
            if self._is_from_current_run(file_path):
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        for source, values in data.items():
                            if isinstance(values, dict):
                                self.combined_data[source].append(values)
                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")
                    continue
    
    def analyze_finance_data(self) -> Dict[str, Any]:
        """Analyze financial data using statistical methods"""
        if not self.combined_data.get('finance'):
            return {}
            
        finance_data = self.combined_data['finance']
        
        # Extract exchange rates and calculate statistics
        exchange_rates = [
            d.get('exchange_USD_JPY', {}).get('exchange_rate')
            for d in finance_data
            if d.get('exchange_USD_JPY')
        ]
        
        if exchange_rates:
            exchange_stats = {
                'mean_rate': np.mean(exchange_rates),
                'std_rate': np.std(exchange_rates),
                'trend': 'increasing' if exchange_rates[-1] > exchange_rates[0] else 'decreasing',
                'volatility': np.std(exchange_rates) / np.mean(exchange_rates)
            }
        else:
            exchange_stats = {}
            
        return {
            'exchange_rate_analysis': exchange_stats
        }
    
    def analyze_social_metrics(self) -> Dict[str, Any]:
        """Analyze social media metrics across platforms"""
        social_stats = {}
        
        # Analyze Meta data
        if self.combined_data.get('meta'):
            meta_data = self.combined_data['meta']
            engagement_rates = []
            sentiment_scores = []
            
            for data in meta_data:
                if isinstance(data, dict):
                    metrics = data.get('overall_metrics', {})
                    sentiment = data.get('sentiment_metrics', {})
                    
                    if metrics:
                        engagement = (
                            metrics.get('average_likes', 0) + 
                            metrics.get('average_comments', 0)
                        ) / 2
                        engagement_rates.append(engagement)
                    
                    if sentiment:
                        sentiment_scores.append(sentiment.get('average_sentiment', 0))
            
            if engagement_rates and sentiment_scores:
                social_stats['meta'] = {
                    'avg_engagement': np.mean(engagement_rates),
                    'engagement_trend': stats.linregress(range(len(engagement_rates)), engagement_rates).slope,
                    'avg_sentiment': np.mean(sentiment_scores),
                    'sentiment_consistency': 1 - (np.std(sentiment_scores) / (max(sentiment_scores) - min(sentiment_scores)))
                }
        
        # Similar analysis for TikTok data
        if self.combined_data.get('tiktok'):
            # Add TikTok analysis here
            pass
            
        return social_stats
    
    def analyze_trends_data(self) -> Dict[str, Any]:
        """Analyze Google Trends data"""
        if not self.combined_data.get('google_trends'):
            return {}
            
        trends_data = self.combined_data['google_trends']
        trend_scores = []
        
        for data in trends_data:
            if isinstance(data, dict):
                # Extract trend scores and interest over time
                scores = data.get('interest_over_time', [])
                if scores:
                    trend_scores.extend(scores)
        
        if trend_scores:
            return {
                'trend_analysis': {
                    'mean_interest': np.mean(trend_scores),
                    'interest_volatility': np.std(trend_scores),
                    'trend_direction': 'increasing' if np.polyfit(range(len(trend_scores)), trend_scores, 1)[0] > 0 else 'decreasing'
                }
            }
        return {}
    
    def generate_combined_insights(self) -> Dict[str, Any]:
        """Generate combined statistical insights across all data sources"""
        insights = {
            'finance': self.analyze_finance_data(),
            'social': self.analyze_social_metrics(),
            'trends': self.analyze_trends_data(),
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_sources': list(self.combined_data.keys()),
                'number_of_samples': {
                    source: len(data) for source, data in self.combined_data.items()
                }
            }
        }
        
        # Calculate cross-platform correlations
        correlations = {}
        if insights['social'].get('meta') and insights['trends'].get('trend_analysis'):
            meta_engagement = insights['social']['meta']['avg_engagement']
            trend_interest = insights['trends']['trend_analysis']['mean_interest']
            correlation = np.corrcoef([meta_engagement], [trend_interest])[0, 1]
            correlations['meta_trends_correlation'] = correlation
        
        insights['cross_platform_analysis'] = correlations
        
        return insights
    
    def save_insights(self, insights: Dict[str, Any], output_file: str = None) -> None:
        """Save the generated insights to a JSON file
        
        Args:
            insights: Dictionary containing the insights
            output_file: Optional output file path
        """
        if output_file is None:
            output_file = f'statistical_insights_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
        output_path = self.data_directory / output_file
        with open(output_path, 'w') as f:
            json.dump(insights, f, indent=2)

def main():
    """Main entry point for statistical analysis"""
    analyzer = StatisticalInsightGenerator()
    analyzer.load_json_files()
    insights = analyzer.generate_combined_insights()
    analyzer.save_insights(insights)
    
if __name__ == "__main__":
    main() 