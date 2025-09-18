#!/usr/bin/env python3
"""
Google Trends CLI - Analyze search interest and regional trends
"""
import os
import sys
import argparse
from typing import Optional, List

from colorama import Fore, Style, init as colorama_init
from .trends_helpers import banner, info, warn, Colors
from .trends_core import proxy_rotator
from .trends_analysis import TrendsAnalyzer

# Initialize colorama
colorama_init(autoreset=True)

# Ensure trends_core.py is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Default output directory
BASE_DIR = os.path.join(CURRENT_DIR, "google_trends_data")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Google Trends Analysis CLI")
    parser.add_argument("query", nargs="?", help="Search query to analyze")
    parser.add_argument("-o", "--output", help="Output directory (default: google_trends_data)", default=BASE_DIR)
    return parser.parse_args()

def get_search_query() -> str:
    """Get search query from user input"""
    query = ""
    while not query:
        query = input(f"{Colors.INFO}Enter search query: {Colors.RESET}").strip()
    return query

def run_analysis(query: str, output_dir: str = BASE_DIR) -> None:
    """Run the trends analysis with the given query"""
    try:
        # Initialize analyzer with proxy rotator
        analyzer = TrendsAnalyzer(output_dir, proxy_rotator)
        
        # Run analysis
        analyzer.analyze_keyword(query)
        
        banner("ANALYSIS COMPLETE", Colors.SUCCESS)
        print(f"{Colors.INFO}Outputs saved in {output_dir}{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.ERROR}Analysis failed: {str(e)}{Colors.RESET}")
        sys.exit(1)

def main() -> None:
    """Main CLI entry point"""
    banner("GOOGLE TRENDS CLI", Colors.HEADER)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Get query from arguments or prompt user
    query = args.query if args.query else get_search_query()
    output_dir = args.output
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"{Colors.INFO}Using output directory: {output_dir}{Colors.RESET}")
    
    # Run the analysis
    run_analysis(query, output_dir)

if __name__ == "__main__":
    main()