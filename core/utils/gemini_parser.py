import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from core.utils.logger import logger

# Initialize Google GenAI Client
if not GEMINI_API_KEY or "mock" in GEMINI_API_KEY:
    logger.error("ALERT: Gemini API Key sahi se set nahi hai .env file me!")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

def parse_pdf_via_gemini(pdf_url: str) -> dict:
    """
    Directly passes the PDF URL using the correct SDK types object formatting 
    to completely avoid parameter structure validation errors.
    """
    if client is None:
        logger.error("Gemini Client initialization failed. Skipping processing.")
        return None

    logger.info(f"Sending PDF to Gemini Pro for AI processing: {pdf_url}")

    prompt = (
        "You are an expert government job analyst for a portal like Sarkari Result. "
        "Analyze the attached PDF document and extract the job details. "
        "Return the output strictly as a single valid JSON object containing exactly these fields and keys:\n\n"
        "{\n"
        '  "job_title": "Full specific job notification title or position name",\n'
        '  "organization": "Name of the conducting board/body (e.g., UPSC, SSC)",\n'
        '  "total_vacancies": 0,\n'
        '  "important_dates": {\n'
        '    "start_date": "YYYY-MM-DD or N/A",\n'
        '    "last_date": "YYYY-MM-DD or N/A"\n'
        "  },\n"
        '  "application_fee": {\n'
        '    "general_obc": "Amount or N/A",\n'
        '    "sc_st_pwd": "Amount or N/A"\n'
        "  },\n"
        '  "age_limit": {\n'
        '    "minimum_age": "Age or N/A",\n'
        '    "maximum_age": "Age or N/A"\n'
        "  },\n"
        '  "eligibility_criteria": "Brief textual list of educational qualification needed",\n'
        '  "official_website": "Main website URL"\n'
        "}\n\n"
        "Do not include markdown blocks like ```json or any trailing characters. Return clean text only."
    )

    try:
        # Pass payload safely using the explicit Part.from_uri types abstraction layer
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=[
                types.Part.from_uri(
                    file_uri=pdf_url,
                    mime_type='application/pdf'
                ),
                prompt
            ]
        )

        raw_text = response.text
        if not raw_text:
            logger.error("Gemini returned an empty response.")
            return None

        # Clean markdown if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text.split("```json")[1]
        if clean_text.endswith("```"):
            clean_text = clean_text.rsplit("```", 1)[0]
        clean_text = clean_text.strip()

        # Enforce Rule 4: Validate structured JSON format
        job_data = json.loads(clean_text)
        logger.info(f"✅ Successfully extracted data for: {job_data.get('job_title')}")
        return job_data

    except json.JSONDecodeError as je:
        logger.error(f"Rule 4 Violation: Gemini output wasn't valid JSON. Text was: {raw_text}. Error: {je}")
        return None
    except Exception as e:
        logger.error(f"Error during Gemini processing for {pdf_url}: {e}")
        return None
