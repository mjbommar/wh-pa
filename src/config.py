"""
This module contains the configuration for the parser/monitor.
"""

# imports
import os
from pathlib import Path

# packages
import httpx

# default paths
PROJECT_PATH = Path(__file__).parent.parent
DEFAULT_HASH_PATH = Path(__file__).parent.parent / "hashes.json"
DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data"
DEFAULT_RAW_PATH = DEFAULT_DATA_PATH / "raw"
DEFAULT_MARKDOWN_PATH = DEFAULT_DATA_PATH / "markdown"
DEFAULT_SUMMARY_PATH = DEFAULT_DATA_PATH / "summary"
DEFAULT_JSON_PATH = DEFAULT_DATA_PATH / "json"
DEFAULT_SLEEP = 0.1

# set up timeout handler
TIMEOUT_CONFIG = httpx.Timeout(
    connect=float(os.getenv("HTTPX_CONNECT_TIMEOUT", 5.0)),
    read=float(os.getenv("HTTPX_READ_TIMEOUT", 10.0)),
    write=float(os.getenv("HTTPX_TIMEOUT", 10.0)),
    pool=float(os.getenv("HTTPX_POOL_TIMEOUT", 10.0)),
)


BASE_URL = "https://www.whitehouse.gov"
PRESIDENTIAL_ACTION_PATH = "/presidential-actions/"

EXCLUDE_EXTENSIONS = (
    ".js",
    ".css",
    ".png",
    ".jpg",
)
