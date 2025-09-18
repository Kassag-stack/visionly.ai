#!/usr/bin/env python3
"""
Combined API Runner - Executes all API analysis in sequence
"""
import os
import sys
import json
import subprocess
import glob
from datetime import datetime
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for colored output
colorama_init(autoreset=True)

# Use ASCII characters for Windows compatibility
SYMBOLS = {
    'check': '+',  # Changed from '√' to '+'
    'cross': 'x',
    'arrow': '->',
    'separator': '=' * 80
}

def load_config(config_file='api_input_data.json'):
    """
    Load API configuration from JSON file
    """
    try:
        # Explicitly use UTF-8 encoding
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"{Fore.GREEN}{SYMBOLS['check']} Loaded configuration from {config_file}")
        return config['apis']
    except Exception as e:
        print(f"{Fore.RED}Error loading configuration: {str(e)}")
        return None

def activate_conda_env():
    """
    Activate the conda environment and return the modified environment variables
    """
    if os.name == 'nt':  # Windows
        activate_cmd = "conda activate hackathon && set"
        shell = "cmd.exe"
        shell_args = ["/c"]
    else:  # Unix-like
        activate_cmd = "conda activate hackathon && printenv"
        shell = "bash"
        shell_args = ["-c"]
    
    try:
        # Run activation command and capture environment
        process = subprocess.Popen(
            [shell, *shell_args, activate_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        output, error = process.communicate()
        
        if process.returncode != 0:
            print(f"{Fore.RED}Error activating conda environment:")
            print(error)
            return None
            
        # Parse environment variables
        env = os.environ.copy()
        for line in output.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
        
        # Add PYTHONIOENCODING to ensure proper encoding
        env['PYTHONIOENCODING'] = 'utf-8'
        
        print(f"{Fore.GREEN}{SYMBOLS['check']} Conda environment 'hackathon' activated")
        return env
        
    except Exception as e:
        print(f"{Fore.RED}Error activating conda environment: {str(e)}")
        return None

def run_command(command, description, env):
    """
    Run a command and print its output with proper formatting
    """
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"{Fore.CYAN}{SYMBOLS['arrow']} Running {description}...")
    print(f"{Fore.CYAN}{SYMBOLS['arrow']} Command: {command}")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}\n")
    
    try:
        # Add python -u flag to force unbuffered output
        if command.startswith('python '):
            command = command.replace('python ', 'python -u ', 1)
        
        # Run the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True,
            encoding='utf-8',
            env=env,
            cwd=os.getcwd()  # Ensure working directory is set correctly
        )
        
        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Get the return code
        return_code = process.poll()
        
        if return_code == 0:
            print(f"\n{Fore.GREEN}{SYMBOLS['check']} {description} completed successfully!")
            return True
        else:
            # Print any error output
            error_output = process.stderr.read()
            if error_output:
                print(f"{Fore.RED}Error output:")
                print(error_output)
            print(f"\n{Fore.RED}{SYMBOLS['cross']} {description} failed with return code {return_code}")
            return False
            
    except Exception as e:
        print(f"\n{Fore.RED}{SYMBOLS['cross']} Error running {description}: {str(e)}")
        return False

def build_commands(config):
    """
    Build commands from configuration
    """
    commands = []
    
    # TikTok API
    if 'tiktokAPI' in config:
        cmd = f"python -m backend_api_backup.tiktok_api.tiktok_api {config['tiktokAPI']['query']}"
        if 'number' in config['tiktokAPI']:
            cmd += f" -n {config['tiktokAPI']['number']}"
        commands.append({
            "cmd": cmd,
            "desc": "TikTok API Analysis"
        })
    
    # Meta API
    if 'metaAPI' in config:
        commands.append({
            "cmd": f"python -m backend_api_backup.meta_api.meta_api {config['metaAPI']['query']}",
            "desc": "Meta API Analysis"
        })
    
    # Google Trends API
    if 'googleTrendsAPI' in config:
        commands.append({
            "cmd": f"python -m backend_api_backup.google_trends.trends_cli \"{config['googleTrendsAPI']['query']}\"",
            "desc": "Google Trends Analysis"
        })
    
    # News API
    if 'newsAPI' in config:
        commands.append({
            "cmd": f"python -m backend_api_backup.news_api.news_api \"{config['newsAPI']['query']}\"",
            "desc": "News API Analysis"
        })
    
    # Finance API
    if 'financeAPI' in config:
        finance_args = []
        if 'currency_pairs' in config['financeAPI']:
            finance_args.extend(config['financeAPI']['currency_pairs'])
        if 'commodities' in config['financeAPI']:
            finance_args.extend(config['financeAPI']['commodities'])
        if 'stocks' in config['financeAPI']:
            finance_args.extend(config['financeAPI']['stocks'])
        
        if finance_args:
            commands.append({
                "cmd": f"python -m backend_api_backup.finance_api.finance_api {' '.join(finance_args)}",
                "desc": "Finance API Analysis"
            })
    
    return commands

def collect_generated_files():
    """
    Collect all generated image files from the analysis
    """
    image_files = []
    
    # Define directories to search
    search_dirs = [
        "backend_api_backup/tiktok_api/analysed_data/*/*.png",
        "backend_api_backup/meta_api/analysed_data/*/*.png",
        "backend_api_backup/google_trends/google_trends_data/*/*.png",
        "backend_api_backup/news_api/news_analysis_data/*/*.png",
        "backend_api_backup/finance_api/analysed_data/finance_logs/images/*.png"
    ]
    
    # Collect files generated in this session
    timestamp = datetime.now().strftime("%Y%m%d")
    for pattern in search_dirs:
        for file in glob.glob(pattern):
            if timestamp in file:  # Only include files from this session
                image_files.append(file)
    
    return sorted(image_files)

def collect_analysis_files():
    """
    Collect all analysis data files from the analysis
    """
    analysis_files = {
        "TikTok": [],
        "Meta": [],
        "Google Trends": [],
        "News": [],
        "Finance": []
    }
    
    # Define directories to search
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # TikTok logs
    tiktok_logs = glob.glob("backend_api_backup/tiktok_api/analysed_data/chatgpt_logs/*.json")
    analysis_files["TikTok"] = [os.path.abspath(f) for f in tiktok_logs if timestamp in f]
    
    # Meta logs
    meta_logs = glob.glob("backend_api_backup/meta_api/analysed_data/chatgpt_logs/*.json")
    analysis_files["Meta"] = [os.path.abspath(f) for f in meta_logs if timestamp in f]
    
    # Google Trends
    trends_logs = glob.glob("backend_api_backup/google_trends/google_trends_data/chatgpt_json/*.json")
    analysis_files["Google Trends"] = [os.path.abspath(f) for f in trends_logs if timestamp in f]
    
    # News analysis
    news_logs = glob.glob("backend_api_backup/news_api/news_analysis_data/csv_files/*_sentiment_analysis_*.csv")
    analysis_files["News"] = [os.path.abspath(f) for f in news_logs if timestamp in f]
    
    # Finance analysis
    finance_logs = glob.glob("backend_api_backup/finance_api/analysed_data/finance_logs/json/*.json")
    analysis_files["Finance"] = [os.path.abspath(f) for f in finance_logs if timestamp in f]
    
    return analysis_files

def print_generated_files(image_files):
    """
    Print two separate JSONs - one for images and one for analysis data, referencing actual files
    """
    if not image_files:
        return
    
    # Group image files by API and type
    image_output = {
        "TikTok": {},
        "Meta": {},
        "Google Trends": {},
        "News": {},
        "Finance": {}
    }
    
    for file_path in image_files:
        abs_path = os.path.abspath(file_path)
        if "tiktok_api" in file_path:
            if "engagement" in file_path:
                image_output["TikTok"]["engagement"] = abs_path
            elif "hashtag" in file_path:
                image_output["TikTok"]["hashtag"] = abs_path
            elif "sentiment" in file_path:
                image_output["TikTok"]["sentiment"] = abs_path
        elif "meta_api" in file_path:
            if "engagement" in file_path:
                image_output["Meta"]["engagement"] = abs_path
            elif "hashtag" in file_path:
                image_output["Meta"]["hashtag"] = abs_path
            elif "sentiment" in file_path:
                image_output["Meta"]["sentiment"] = abs_path
            elif "likes" in file_path:
                image_output["Meta"]["likes"] = abs_path
        elif "google_trends" in file_path:
            if "interest" in file_path:
                image_output["Google Trends"]["interest"] = abs_path
            elif "regional" in file_path:
                image_output["Google Trends"]["regional"] = abs_path
        elif "news_api" in file_path:
            if "sentiment" in file_path:
                image_output["News"]["sentiment"] = abs_path
            elif "wordcloud" in file_path:
                image_output["News"]["wordcloud"] = abs_path
        elif "finance_api" in file_path:
            if "timeseries" in file_path:
                image_output["Finance"]["timeseries"] = abs_path
            elif "stats" in file_path:
                image_output["Finance"]["stats"] = abs_path
    
    # Remove empty categories
    image_output = {k: v for k, v in image_output.items() if v}
    
    # Collect analysis files
    analysis_files = collect_analysis_files()
    
    # Create analysis output structure
    analysis_output = {
        "TikTok": {
            "data_source": "chatgpt_logs",
            "files": analysis_files["TikTok"]
        },
        "Meta": {
            "data_source": "chatgpt_logs",
            "files": analysis_files["Meta"]
        },
        "Google Trends": {
            "data_source": "chatgpt_json",
            "files": analysis_files["Google Trends"]
        },
        "News": {
            "data_source": "sentiment_analysis",
            "files": analysis_files["News"]
        },
        "Finance": {
            "data_source": "analysis_json",
            "files": analysis_files["Finance"]
        }
    }
    
    # Remove empty categories
    analysis_output = {k: v for k, v in analysis_output.items() if v["files"]}
    
    # Print image files JSON
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"{Fore.CYAN}Generated Visualization Files")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}")
    print(json.dumps(image_output, indent=2))

    # Print analysis data JSON
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"{Fore.CYAN}Analysis Data Files")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}")
    print(json.dumps(analysis_output, indent=2))

def main():
    """
    Main function to run all APIs in sequence
    """
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"{Fore.CYAN}Starting Combined API Analysis")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}")
    
    # Load configuration
    config = load_config()
    if not config:
        print(f"{Fore.RED}Failed to load configuration. Exiting.")
        return
    
    # Activate conda environment
    env = activate_conda_env()
    if not env:
        print(f"{Fore.RED}Failed to activate conda environment. Exiting.")
        return
    
    # Store start time
    start_time = datetime.now()
    
    # Build commands from configuration
    commands = build_commands(config)
    
    # Track success/failure
    results = []
    
    # Run each command
    for cmd in commands:
        success = run_command(cmd["cmd"], cmd["desc"], env)
        results.append({
            "description": cmd["desc"],
            "success": success
        })
        
        # Add a small delay between commands
        if not success:
            print(f"{Fore.YELLOW}Waiting 5 seconds before next command...")
            import time
            time.sleep(5)
    
    # Calculate duration
    duration = datetime.now() - start_time
    
    # Print summary
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"{Fore.CYAN}Analysis Summary")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}")
    print(f"\nTotal Duration: {duration}")
    print("\nResults:")
    
    all_success = True
    for result in results:
        status = f"{Fore.GREEN}{SYMBOLS['check']}" if result["success"] else f"{Fore.RED}{SYMBOLS['cross']}"
        print(f"{status} {result['description']}: {'Success' if result['success'] else 'Failed'}")
        all_success = all_success and result["success"]
    
    # Collect and print generated files
    image_files = collect_generated_files()
    print_generated_files(image_files)
    
    # Final status
    print(f"\n{Fore.CYAN}{SYMBOLS['separator']}")
    if all_success:
        print(f"{Fore.GREEN}{SYMBOLS['check']} All analyses completed successfully!")
    else:
        print(f"{Fore.YELLOW}Warning: Some analyses failed. Check the logs above for details.")
    print(f"{Fore.CYAN}{SYMBOLS['separator']}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Warning: Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}{SYMBOLS['cross']} Fatal error: {str(e)}")
        sys.exit(1) 