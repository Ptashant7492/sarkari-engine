import logging
import sys
from config import LOG_FILE

# Ensure logs directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout) # Prints cleanly to Codespace terminal
    ]
)

logger = logging.getLogger("SarkariAutomation")
