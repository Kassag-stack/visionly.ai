"""
Run statistical analysis on combined API data
"""

import os
from pathlib import Path
from backend_api_backup.combined_insight.statistical_insight import StatisticalInsightGenerator
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for colored output
colorama_init(autoreset=True)

def main():
    """Main entry point"""
    try:
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.CYAN}🔍 STARTING STATISTICAL ANALYSIS")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        # Get the workspace root directory
        workspace_root = Path(__file__).parent
        
        # Initialize the analyzer with the workspace root
        analyzer = StatisticalInsightGenerator(workspace_root)
        
        print(f"{Fore.CYAN}▶ Loading JSON files...")
        analyzer.load_json_files()
        
        print(f"{Fore.CYAN}▶ Generating statistical insights...")
        insights = analyzer.generate_combined_insights()
        
        print(f"{Fore.CYAN}▶ Saving results...")
        analyzer.save_insights(insights)
        
        print(f"\n{Fore.GREEN}✓ Analysis complete!")
        print(f"{Fore.GREEN}✓ Results saved to statistical_insights_*.json")
        
    except Exception as e:
        print(f"\n{Fore.RED}Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main() 