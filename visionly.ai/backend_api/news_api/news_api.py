import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from textblob import TextBlob
import re
from collections import Counter
import os
import argparse
from wordcloud import WordCloud
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
import io
from colorama import Fore, Style, Back, init as colorama_init
import warnings

# Filter out specific scikit-learn deprecation warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='sklearn')

load_dotenv()

# Initialize colorama
colorama_init(autoreset=True)

class NewsAnalyzer:
    def __init__(self, api_key):
        """
        Initialize NewsAPI analyzer
        
        Args:
            api_key (str): Your NewsAPI key from https://newsapi.org/
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/"
        self.headers = {'X-API-Key': api_key}
        
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_API_KEY')
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Set up fixed output directories using os.path for cross-platform compatibility
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_analysis_data")
        self.csv_dir = os.path.join(self.base_dir, "csv_files")
        self.images_dir = os.path.join(self.base_dir, "images")
        
        # Generate timestamp for this analysis session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories if they don't exist
        for directory in [self.csv_dir, self.images_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Created directory: {Fore.CYAN}{directory}{Style.RESET_ALL}")
    
    def upload_to_supabase(self, file_data, filename, bucket_name):
        """
        Upload file to Supabase bucket
        
        Args:
            file_data: File data (bytes or string)
            filename (str): Name of the file
            bucket_name (str): Name of the Supabase bucket
        """
        try:
            # If file_data is a string (CSV), convert to bytes
            if isinstance(file_data, str):
                file_data = file_data.encode('utf-8')
            
            # Add news_api prefix to filename if not already present
            if 'news_api' not in filename:
                name, ext = os.path.splitext(filename)
                filename = f"news_api_{name}_{self.timestamp}{ext}"
            
            # Save locally if it's a CSV file
            if filename.endswith('.csv'):
                local_path = os.path.join(self.csv_dir, filename)
                with open(local_path, 'wb') as f:
                    f.write(file_data)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Saved CSV locally: {Fore.CYAN}{local_path}{Style.RESET_ALL}")
            
            # Upload to Supabase
            self.supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=file_data,
                file_options={"content-type": "text/csv" if filename.endswith('.csv') else "image/png"}
            )
            
            # Get public URL
            url = self.supabase.storage.from_(bucket_name).get_public_url(filename)
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} File uploaded to Supabase: {Fore.CYAN}{url}{Style.RESET_ALL}")
            return url
            
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error uploading to Supabase: {str(e)}")
            return None
    
    def save_plot_to_supabase(self, plt, filename, bucket_name):
        """
        Save matplotlib plot to Supabase
        
        Args:
            plt: Matplotlib figure
            filename (str): Name of the file
            bucket_name (str): Name of the Supabase bucket
        """
        try:
            # Save plot to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            # Save locally to images directory
            local_path = os.path.join(self.images_dir, filename)
            plt.savefig(local_path, format='png', dpi=300, bbox_inches='tight')
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} Saved plot locally: {Fore.CYAN}{local_path}{Style.RESET_ALL}")
            
            # Upload to Supabase
            return self.upload_to_supabase(buf.getvalue(), filename, bucket_name)
            
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error saving plot to Supabase: {e}")
            return None
        finally:
            plt.close()
    
    def get_everything_news(self, query, days_back=7, language='en', sort_by='publishedAt'):
        """
        Get news articles using everything endpoint
        
        Args:
            query (str): Search query
            days_back (int): Number of days back to search
            language (str): Language code
            sort_by (str): Sort by relevancy, popularity, or publishedAt
        """
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        
        url = f"{self.base_url}everything"
        params = {
            'q': query,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'language': language,
            'sortBy': sort_by,
            'pageSize': 100  # Max articles per request
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error fetching news: {e}")
            return None
    
    def get_top_headlines(self, query=None, category=None, country='us'):
        """
        Get top headlines
        
        Args:
            query (str): Search query
            category (str): business, entertainment, general, health, science, sports, technology
            country (str): Country code
        """
        
        url = f"{self.base_url}top-headlines"
        params = {
            'country': country,
            'pageSize': 100
        }
        
        if query:
            params['q'] = query
        if category:
            params['category'] = category
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error fetching headlines: {e}")
            return None
    
    def analyze_sentiment(self, text):
        """
        Analyze sentiment of text using TextBlob
        
        Args:
            text (str): Text to analyze
            
        Returns:
            dict: Sentiment analysis results
        """
        if not text:
            return {'polarity': 0, 'subjectivity': 0, 'sentiment': 'neutral'}
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Classify sentiment
        if polarity > 0.1:
            sentiment = 'positive'
        elif polarity < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'sentiment': sentiment
        }
    
    def process_articles(self, news_data, query_name):
        """
        Process and analyze news articles
        
        Args:
            news_data (dict): Raw news data from API
            query_name (str): Name for the query (for saving files)
            
        Returns:
            pd.DataFrame: Processed articles with sentiment analysis
        """
        if not news_data or 'articles' not in news_data:
            print(f"{Fore.RED}✗{Style.RESET_ALL} No articles found in news data")
            return pd.DataFrame()
        
        articles = news_data['articles']
        processed_articles = []
        
        print(f"{Fore.CYAN}📰 Processing {len(articles)} articles...{Style.RESET_ALL}")
        
        for article in articles:
            # Clean and prepare text for analysis
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', '')
            
            # Combine title and description for analysis
            full_text = f"{title} {description}".strip()
            
            # Analyze sentiment
            sentiment_analysis = self.analyze_sentiment(full_text)
            
            # Extract key information
            processed_article = {
                'title': title,
                'description': description,
                'url': article.get('url', ''),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'author': article.get('author', 'Unknown'),
                'published_at': article.get('publishedAt', datetime.now().isoformat()),  # Default to current time if not present
                'full_text': full_text,
                'polarity': sentiment_analysis['polarity'],
                'subjectivity': sentiment_analysis['subjectivity'],
                'sentiment': sentiment_analysis['sentiment'],
                'word_count': len(full_text.split()),
                'query': query_name
            }
            
            processed_articles.append(processed_article)
        
        df = pd.DataFrame(processed_articles)
        
        try:
            # Convert published_at to datetime, handling potential errors
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
            # Fill any NaT (Not a Time) values with current time
            df['published_at'] = df['published_at'].fillna(pd.Timestamp.now())
            df['date'] = df['published_at'].dt.date
        except Exception as e:
            print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} Warning: Error processing dates: {e}")
            # If date processing fails, use current date
            df['date'] = pd.Timestamp.now().date()
        
        return df
    
    def analyze_product_sentiment(self, product_name, days_back=7):
        """
        Comprehensive product sentiment analysis
        
        Args:
            product_name (str): Product name to analyze
            days_back (int): Days back to analyze
            
        Returns:
            dict: Complete analysis results
        """
        print(f"\n{Back.BLUE}{Fore.WHITE} ANALYZING NEWS SENTIMENT FOR: {product_name.upper()} {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}")
        
        # Search queries for comprehensive coverage
        search_queries = [
            product_name,
            f"{product_name} health",
            f"{product_name} benefits",
            f"{product_name} market",
            f"{product_name} trend",
            f"{product_name} industry"
        ]
        
        all_articles = []
        
        for query in search_queries:
            print(f"\n{Fore.CYAN}🔎 Searching for: '{query}'{Style.RESET_ALL}")
            news_data = self.get_everything_news(query, days_back=days_back)
            
            if news_data:
                df = self.process_articles(news_data, query)
                if not df.empty:
                    all_articles.append(df)
                    print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Found {Fore.YELLOW}{len(df)}{Style.RESET_ALL} articles")
                else:
                    print(f"   {Fore.YELLOW}⚠{Style.RESET_ALL} No articles found")
        
        if not all_articles:
            print(f"{Fore.RED}✗{Style.RESET_ALL} No articles found for analysis")
            return None
        
        # Combine all articles
        combined_df = pd.concat(all_articles, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
        
        print(f"\n{Back.BLUE}{Fore.WHITE} ANALYSIS SUMMARY {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * 30}{Style.RESET_ALL}")
        print(f"Total unique articles: {Fore.YELLOW}{len(combined_df)}{Style.RESET_ALL}")
        print(f"Date range: {Fore.CYAN}{combined_df['date'].min()}{Style.RESET_ALL} to {Fore.CYAN}{combined_df['date'].max()}{Style.RESET_ALL}")
        
        # Sentiment analysis
        sentiment_counts = combined_df['sentiment'].value_counts()
        print(f"\n{Fore.BLUE}📈 SENTIMENT BREAKDOWN:{Style.RESET_ALL}")
        for sentiment, count in sentiment_counts.items():
            percentage = (count / len(combined_df)) * 100
            print(f"   {sentiment.title()}: {count} articles ({percentage:.1f}%)")
        
        # Average sentiment scores
        avg_polarity = combined_df['polarity'].mean()
        avg_subjectivity = combined_df['subjectivity'].mean()
        
        print(f"\n{Fore.BLUE}🎯 SENTIMENT SCORES:{Style.RESET_ALL}")
        print(f"   Average Polarity: {Fore.YELLOW}{avg_polarity:.3f} (Range: -1 to 1){Style.RESET_ALL}")
        print(f"   Average Subjectivity: {Fore.YELLOW}{avg_subjectivity:.3f} (Range: 0 to 1){Style.RESET_ALL}")
        
        # Determine overall sentiment
        if avg_polarity > 0.1:
            overall_sentiment = "POSITIVE 📈"
        elif avg_polarity < -0.1:
            overall_sentiment = "NEGATIVE 📉"
        else:
            overall_sentiment = "NEUTRAL ➡️"
        
        print(f"   Overall Sentiment: {Fore.GREEN}{overall_sentiment}{Style.RESET_ALL}")
        
        # Top sources
        top_sources = combined_df['source'].value_counts().head(5)
        print(f"\n{Fore.BLUE}📰 TOP NEWS SOURCES:{Style.RESET_ALL}")
        for source, count in top_sources.items():
            print(f"   {source}: {count} articles")
        
        # Daily sentiment trend
        daily_sentiment = combined_df.groupby('date').agg({
            'polarity': 'mean',
            'sentiment': lambda x: x.value_counts().index[0] if len(x) > 0 else 'neutral'
        }).round(3)
        
        print(f"\n{Fore.BLUE}📅 DAILY SENTIMENT TRENDS:{Style.RESET_ALL}")
        for date, row in daily_sentiment.iterrows():
            print(f"   {date}: {row['sentiment'].title()} (Score: {row['polarity']:.3f})")
        
        # Save data to Supabase
        csv_filename = f"{product_name.lower().replace(' ', '_')}_sentiment_analysis_{self.timestamp}.csv"
        csv_data = combined_df.to_csv(index=False)
        self.upload_to_supabase(csv_data, csv_filename, "chat-csv")
        
        return {
            'articles_df': combined_df,
            'sentiment_summary': sentiment_counts,
            'avg_polarity': avg_polarity,
            'avg_subjectivity': avg_subjectivity,
            'overall_sentiment': overall_sentiment,
            'daily_trends': daily_sentiment,
            'top_sources': top_sources
        }
    
    def create_sentiment_visualizations(self, analysis_results, product_name):
        """
        Create comprehensive visualizations for sentiment analysis
        """
        
        if not analysis_results:
            return
        
        df = analysis_results['articles_df']
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{product_name.title()} - News Sentiment Analysis', fontsize=16, fontweight='bold')
        
        # 1. Sentiment Distribution
        ax1 = axes[0, 0]
        sentiment_counts = df['sentiment'].value_counts()
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']  # green, red, gray
        wedges, texts, autotexts = ax1.pie(sentiment_counts.values, labels=sentiment_counts.index, 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('Sentiment Distribution')
        
        # 2. Daily Sentiment Trends
        ax2 = axes[0, 1]
        daily_sentiment = df.groupby('date')['polarity'].mean()
        ax2.plot(daily_sentiment.index, daily_sentiment.values, marker='o', linewidth=2, markersize=6)
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_title('Daily Sentiment Trend')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Average Polarity Score')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 3. Source Analysis
        ax3 = axes[1, 0]
        top_sources = df['source'].value_counts().head(8)
        bars = ax3.barh(range(len(top_sources)), top_sources.values)
        ax3.set_yticks(range(len(top_sources)))
        ax3.set_yticklabels(top_sources.index)
        ax3.set_title('Articles by News Source')
        ax3.set_xlabel('Number of Articles')
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, top_sources.values)):
            ax3.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    str(value), ha='left', va='center')
        
        # 4. Polarity vs Subjectivity Scatter
        ax4 = axes[1, 1]
        colors_map = {'positive': '#2ecc71', 'negative': '#e74c3c', 'neutral': '#95a5a6'}
        for sentiment in df['sentiment'].unique():
            mask = df['sentiment'] == sentiment
            ax4.scatter(df[mask]['polarity'], df[mask]['subjectivity'], 
                       c=colors_map[sentiment], label=sentiment.title(), alpha=0.6)
        
        ax4.set_title('Sentiment Analysis Scatter Plot')
        ax4.set_xlabel('Polarity (Negative ← → Positive)')
        ax4.set_ylabel('Subjectivity (Objective ← → Subjective)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        
        # Save visualization to Supabase with news_api prefix
        plot_filename = f"news_api_{product_name.lower().replace(' ', '_')}_sentiment_visualization_{self.timestamp}.png"
        self.save_plot_to_supabase(plt, plot_filename, "chat-images")
    
    def create_word_cloud(self, analysis_results, product_name):
        """
        Create word cloud from article titles and descriptions
        """
        
        if not analysis_results:
            return
        
        df = analysis_results['articles_df']
        
        # Combine all text
        all_text = ' '.join(df['full_text'].dropna())
        
        # Clean text
        all_text = re.sub(r'http\S+', '', all_text)  # Remove URLs
        all_text = re.sub(r'[^a-zA-Z\s]', '', all_text)  # Keep only letters and spaces
        
        # Create word cloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=100,
            colormap='viridis'
        ).generate(all_text)
        
        plt.figure(figsize=(12, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(f'{product_name.title()} - Most Mentioned Words in News', fontsize=16, fontweight='bold')
        
        # Save word cloud to Supabase with news_api prefix
        wordcloud_filename = f"news_api_{product_name.lower().replace(' ', '_')}_wordcloud_{self.timestamp}.png"
        self.save_plot_to_supabase(plt, wordcloud_filename, "chat-images")
    
    def get_general_market_news(self, days_back=7):
        """
        Get general market and business news for context
        """
        
        print(f"\n{Back.BLUE}{Fore.WHITE} GETTING GENERAL MARKET NEWS {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * 40}{Style.RESET_ALL}")
        
        categories = ['business', 'health', 'technology']
        all_news = []
        
        for category in categories:
            print(f"\n{Fore.CYAN}🔍 Fetching {category} news...{Style.RESET_ALL}")
            news_data = self.get_top_headlines(category=category)
            
            if news_data:
                df = self.process_articles(news_data, f"general_{category}")
                if not df.empty:
                    all_news.append(df)
                    print(f"   {Fore.GREEN}✓{Style.RESET_ALL} Found {Fore.YELLOW}{len(df)}{Style.RESET_ALL} articles")
        
        if all_news:
            combined_general = pd.concat(all_news, ignore_index=True)
            
            # Save general news to Supabase
            filename = f"general_market_news_{self.timestamp}.csv"
            csv_data = combined_general.to_csv(index=False)
            self.upload_to_supabase(csv_data, filename, "chat-csv")
            
            # Quick analysis
            sentiment_dist = combined_general['sentiment'].value_counts()
            avg_polarity = combined_general['polarity'].mean()
            
            print(f"\n{Fore.BLUE}📊 GENERAL MARKET SENTIMENT:{Style.RESET_ALL}")
            print(f"   Overall Polarity: {Fore.YELLOW}{avg_polarity:.3f}{Style.RESET_ALL}")
            for sentiment, count in sentiment_dist.items():
                print(f"   {sentiment.title()}: {Fore.YELLOW}{count}{Style.RESET_ALL} articles")
            
            return combined_general
        
        return None
    
    def get_additional_matcha_insights(self):
        """Get additional insights about matcha trends"""
        print("\n🔍 ADDITIONAL MATCHA INSIGHTS")
        print("=" * 40)
        print("This feature has been removed as requested.")
        return None

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="News API Sentiment Analysis")
    parser.add_argument("query", nargs="?", help="Search query for news analysis")
    parser.add_argument("-d", "--days", type=int, default=7,
                      help="Number of days back to analyze (default: 7)")
    parser.add_argument("-l", "--language", default="en",
                      help="Language code for news articles (default: en)")
    parser.add_argument("--no-general", action="store_true",
                      help="Skip general market news analysis")
    return parser.parse_args()

def main():
    """
    Main function to run news sentiment analysis
    """
    
    # Get API key from environment variable
    NEWS_API = os.getenv('NEWS_API')
    
    if not NEWS_API:
        print(f"{Fore.RED}✗{Style.RESET_ALL} NEWS_API environment variable not found")
        print(f"{Fore.CYAN}📝 Get your free API key from: https://newsapi.org/{Style.RESET_ALL}")
        return
    
    # Initialize analyzer
    analyzer = NewsAnalyzer(NEWS_API)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Get query from arguments or prompt user
    query = args.query
    if not query:
        while True:
            query = input(f"\n{Fore.CYAN}Enter your search query: {Style.RESET_ALL}").strip()
            if query:
                break
            print(f"{Fore.YELLOW}Please enter a valid search query.{Style.RESET_ALL}")
    
    print(f"\n{Back.BLUE}{Fore.WHITE} NEWS SENTIMENT ANALYSIS {Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 60}{Style.RESET_ALL}")
    print(f"\n{Back.BLUE}{Fore.WHITE} ANALYZING: {query.upper()} {Style.RESET_ALL}")
    print(f"{Fore.CYAN}▶ Days back: {args.days}")
    print(f"{Fore.CYAN}▶ Language: {args.language}")
    
    # Analyze sentiment
    results = analyzer.analyze_product_sentiment(query, days_back=args.days)
    
    if results:
        # Create visualizations
        analyzer.create_sentiment_visualizations(results, query)
        
        # Create word cloud
        analyzer.create_word_cloud(results, query)
    
    # Get general market context if not disabled
    general_news = None
    if not args.no_general:
        general_news = analyzer.get_general_market_news(days_back=args.days)
    
    # Summary report
    print(f"\n{Back.BLUE}{Fore.WHITE} FINAL SUMMARY REPORT {Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 50}{Style.RESET_ALL}")
    
    if results:
        print(f"\n{Fore.CYAN}🏷️  {query.title()}:{Style.RESET_ALL}")
        print(f"   Articles analyzed: {Fore.YELLOW}{len(results['articles_df'])}{Style.RESET_ALL}")
        print(f"   Overall sentiment: {Fore.GREEN}{results['overall_sentiment']}{Style.RESET_ALL}")
        print(f"   Average polarity: {Fore.YELLOW}{results['avg_polarity']:.3f}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✓{Style.RESET_ALL} Analysis complete! Files have been uploaded to Supabase buckets:")
    print(f"{Fore.CYAN}- CSV files in 'chat-csv' bucket{Style.RESET_ALL}")
    print(f"{Fore.CYAN}- Images in 'chat-images' bucket{Style.RESET_ALL}")

if __name__ == "__main__":
    main()