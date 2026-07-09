import random
import time
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS, RANDOM_DELAY_MIN, RANDOM_DELAY_MAX
from core.utils.logger import logger
from core.storage.db_manager import log_new_link

URL = "https://www.upsc.gov.in/vacancy-circulars"

def get_safe_headers():
    """Returns headers with a randomized User-Agent to avoid IP blocks."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }

def scrape_upsc():
    """Scrapes latest recruitment PDF links from UPSC website."""
    logger.info("Starting UPSC scraping cycle...")
    
    # Enforce Rule 3: Random Delay to act human-like
    delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
    logger.info(f"Applying stealth delay of {delay:.2f} seconds before request.")
    time.sleep(delay)
    
    # Enforce Rule 2: Robust Error Handling
    try:
        headers = get_safe_headers()
        response = requests.get(URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"UPSC site returned non-200 status: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.find_all("tr")
        
        new_links_counter = 0
        
        for row in rows:
            link_tag = row.find("a", href=True)
            if link_tag and ".pdf" in link_tag['href'].lower():
                # Extract title cleanly
                title = row.get_text(separator=" ").strip().split("\n")[0]
                title = " ".join(title.split()) # Remove extra spaces
                
                # Resolve relative URL to absolute URL
                link = link_tag['href']
                if not link.startswith("http"):
                    link = "https://www.upsc.gov.in" + link
                
                # Enforce Rule 1: Log new link (Automatically ignores if already exists)
                is_inserted = log_new_link(url=link, source="UPSC")
                if is_inserted:
                    new_links_counter += 1
                    logger.info(f"Discovered: {title[:60]}...")
                    
        logger.info(f"UPSC scraping cycle finished. Found {new_links_counter} new entries.")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while reaching UPSC: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in UPSC scraper module: {e}")
