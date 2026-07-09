import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "core" / "storage" / "jobs.db"
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"

# API Configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WP_BASE_URL = os.getenv("WP_BASE_URL")
WP_APPLICATION_PASSWORD = os.getenv("WP_APPLICATION_PASSWORD")

# Scraping Guardrails (Rule 3)
RANDOM_DELAY_MIN = 2
RANDOM_DELAY_MAX = 5

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]
