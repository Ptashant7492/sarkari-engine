import csv
import os
from pathlib import Path
from core.utils.logger import logger

CSV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "sarkari_jobs.csv"

def export_job_to_csv(job_data: dict):
    file_exists = os.path.isfile(CSV_FILE_PATH)
    
    headers = [
        "Job Title", "Organization", "Total Vacancies", 
        "Start Date", "Last Date", "General/OBC Fee", 
        "SC/ST Fee", "Min Age", "Max Age", "Eligibility", "Official Website"
    ]
    
    try:
        os.makedirs(CSV_FILE_PATH.parent, exist_ok=True)
        with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
                
            writer.writerow([
                job_data.get("job_title", "N/A"),
                job_data.get("organization", "N/A"),
                job_data.get("total_vacancies", 0),
                job_data.get("important_dates", {}).get("start_date", "N/A"),
                job_data.get("important_dates", {}).get("last_date", "N/A"),
                job_data.get("application_fee", {}).get("general_obc", "N/A"),
                job_data.get("application_fee", {}).get("sc_st_pwd", "N/A"),
                job_data.get("age_limit", {}).get("minimum_age", "N/A"),
                job_data.get("age_limit", {}).get("maximum_age", "N/A"),
                job_data.get("eligibility_criteria", "N/A"),
                job_data.get("official_website", "N/A")
            ])
            
        logger.info(f"📊 Job data exported successfully to CSV at: {CSV_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to export data to CSV file: {e}")
        return False
