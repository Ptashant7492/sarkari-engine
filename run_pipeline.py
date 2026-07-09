import random
import time
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS, RANDOM_DELAY_MIN, RANDOM_DELAY_MAX
from core.storage.db_manager import init_db, log_new_link, is_link_processed
from core.storage.csv_exporter import export_job_to_csv
from core.utils.gemini_parser import parse_pdf_via_gemini
from core.utils.logger import logger
from core.storage.html_generator import generate_static_website

URL = "https://www.upsc.gov.in/vacancy-circulars"

def get_safe_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

def execute_automation_cycle():
    logger.info("=== STARTING AUTOMATION CYCLE ===")
    
    # 1. Initialize State DB
    init_db()
    
    # Enforce Rule 3: Stealth Delay
    delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
    time.sleep(delay)
    
    # Enforce Rule 2: Exception handling for website down state
    try:
        response = requests.get(URL, headers=get_safe_headers(), timeout=15)
        if response.status_code != 200:
            logger.error(f"UPSC Portal returned error code: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, "html.parser")
        rows = soup.find_all("tr")
        
        for row in rows:
            link_tag = row.find("a", href=True)
            if link_tag and ".pdf" in link_tag['href'].lower():
                title = row.get_text(separator=" ").strip().split("\n")[0]
                title = " ".join(title.split())
                
                link = link_tag['href']
                if not link.startswith("http"):
                    link = "https://www.upsc.gov.in" + link
                
                # Enforce Rule 1: Idempotency Check
                if is_link_processed(link):
                    continue # Database me pehle se hai to skip karo, duplicate nahi banega
                    
                logger.info(f"New Unprocessed Job Detected: {title[:50]}...")
                
                # Attempt to extract with Gemini
                ai_data = parse_pdf_via_gemini(link)
                
                # Fail-safe mechanism if Gemini is blocked or returns 429
                if not ai_data:
                    logger.warning(f"Gemini processing failed/rate-limited. Using local fallback structure for: {title[:40]}")
                    ai_data = {
                        "job_title": title,
                        "organization": "UPSC",
                        "total_vacancies": 0,
                        "important_dates": {"start_date": "Check Notification", "last_date": "N/A"},
                        "application_fee": {"general_obc": "See PDF", "sc_st_pwd": "See PDF"},
                        "age_limit": {"minimum_age": "N/A", "maximum_age": "N/A"},
                        "eligibility_criteria": "Refer to official attached PDF documentation",
                        "official_website": "https://upsc.gov.in"
                    }
                
                # Export to local Excel compatible CSV sheet
                export_success = export_job_to_csv(ai_data)
                
                if export_success:
                    # Enforce Rule 1: Mark as processed safely in DB
                    log_new_link(link, source="UPSC")
                    
            logger.info("=== AUTOMATION CYCLE COMPLETED SUCCESSFULLY ===")
        # Generate the fresh static layout grid instantly
        generate_static_website()
        
    except Exception as e:
        logger.error(f"Pipeline loop compilation failed: {e}")

if __name__ == "__main__":
    execute_automation_cycle()
