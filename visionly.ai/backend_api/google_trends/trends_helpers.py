from colorama import Fore, Style, init as colorama_init
import os
from datetime import datetime
from typing import List, Optional

# Initialize colorama with autoreset
colorama_init(autoreset=True)

class Colors:
    """Color constants for consistent styling"""
    SUCCESS = Fore.GREEN
    INFO = Fore.CYAN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    HEADER = Fore.MAGENTA
    RESET = Style.RESET_ALL

def timestamp() -> str:
    """Returns formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def sanitize_filename(name: str) -> str:
    """Sanitizes a string for use in filenames"""
    return name.lower().replace(' ', '_')

# ─── Logging Utilities ───────────────────────────────────────
def banner(msg: str, color: str = Colors.INFO) -> None:
    """
    Prints a styled banner message
    Args:
        msg: Message to display
        color: Color to use (default: cyan)
    """
    bar = "═" * 72
    print(f"\n{color}{bar}{Colors.RESET}")
    print(f"{color}{msg.center(72)}{Colors.RESET}")
    print(f"{color}{bar}{Colors.RESET}\n")

def ok(msg: str) -> None:
    """Print success message"""
    print(f"{Colors.SUCCESS}✅ {msg}{Colors.RESET}")

def info(msg: str) -> None:
    """Print info message"""
    print(f"{Colors.INFO}ℹ️  {msg}{Colors.RESET}")

def warn(msg: str) -> None:
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.RESET}")

def err(msg: str) -> None:
    """Print error message"""
    print(f"{Colors.ERROR}❌ {msg}{Colors.RESET}")

# ─── Directory Utilities ─────────────────────────────────────
def ensure_dirs(*paths: str) -> None:
    """
    Ensures multiple directories exist
    Args:
        *paths: Variable number of directory paths
    """
    for path in paths:
        os.makedirs(path, exist_ok=True)
        info(f"Ensured directory exists: {path}")

def get_output_paths(base_dir: str, keyword: str, ts: Optional[str] = None) -> dict:
    """
    Creates standardized output paths for Google Trends data
    Args:
        base_dir: Base directory for outputs
        keyword: Search keyword
        ts: Timestamp (optional, will generate if not provided)
    Returns:
        Dictionary of output paths
    """
    if ts is None:
        ts = timestamp()
    
    keyword_safe = sanitize_filename(keyword)
    
    paths = {
        "summary": {
            "csv": os.path.join(base_dir, "SUMMARY", "csv"),
            "images": os.path.join(base_dir, "SUMMARY", "images")
        },
        "regional": {
            "csv": os.path.join(base_dir, "REGIONAL_INTEREST", "csv"),
            "images": os.path.join(base_dir, "REGIONAL_INTEREST", "images")
        }
    }
    
    # Ensure all directories exist
    for category in paths.values():
        ensure_dirs(*category.values())
    
    return paths 