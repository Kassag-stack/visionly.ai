import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init

# Initialize colorama
colorama_init(autoreset=True)

# Load environment variables
load_dotenv()

def test_google_trends():
    """Test Google Trends functionality"""
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}🔍 TESTING GOOGLE TRENDS")
    print(f"{Fore.CYAN}{'='*50}\n")
    
    try:
        # Set up base directory for Google Trends data
        base_dir = os.path.join("backend_api_backup", "google_trends", "google_trends_data")
        
        # Create required directories
        for subdir in ["SUMMARY", "REGIONAL_INTEREST", "EXTRA_INSIGHTS"]:
            for subtype in ["csv", "images"]:
                os.makedirs(os.path.join(base_dir, subdir, subtype), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "chatgpt_json"), exist_ok=True)
        
        print(f"{Fore.GREEN}✓ Created output directories")
        
        # Import required modules
        from backend_api_backup.google_trends.proxy_utils import ProxyRotator, get_proxies_from_env
        from backend_api_backup.google_trends.trends_analysis import TrendsAnalyzer
        
        # Get proxies from environment
        proxies = get_proxies_from_env()
        if proxies:
            print(f"{Fore.GREEN}✓ Found {len(proxies)} proxies")
            for i, proxy in enumerate(proxies, 1):
                print(f"{Fore.CYAN}  Proxy {i}: {proxy}")
        else:
            print(f"{Fore.YELLOW}⚠ No proxies found - will attempt direct connection")
        
        # Initialize ProxyRotator
        proxy_rotator = ProxyRotator(proxies)
        print(f"{Fore.GREEN}✓ Initialized proxy rotator")
        
        # Initialize TrendsAnalyzer
        analyzer = TrendsAnalyzer(base_dir, proxy_rotator)
        print(f"{Fore.GREEN}✓ Initialized trends analyzer")
        
        # Test a single keyword first
        test_keyword = "snowboard"
        print(f"\n{Fore.CYAN}Testing single keyword: {test_keyword}")
        
        try:
            # Basic trend analysis
            print(f"{Fore.CYAN}Running basic trend analysis...")
            results = analyzer.analyze_keyword(test_keyword)
            print(f"{Fore.GREEN}✓ Basic trend analysis complete")
            
            # Extra insights
            print(f"{Fore.CYAN}Getting extra insights...")
            extra_results = analyzer.extra_insights(test_keyword)
            print(f"{Fore.GREEN}✓ Extra insights complete")
            
            print(f"\n{Fore.GREEN}✓ Successfully tested Google Trends!")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Error during analysis: {str(e)}")
            import traceback
            print(f"{Fore.RED}Stack trace:")
            print(traceback.format_exc())
        
    except Exception as e:
        print(f"\n{Fore.RED}✗ Setup failed: {str(e)}")
        import traceback
        print(f"{Fore.RED}Stack trace:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_google_trends() 