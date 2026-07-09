from core.utils.gemini_parser import parse_pdf_via_gemini
import json

# UPSC ka ek sample notification PDF URL
sample_pdf = "https://www.upsc.gov.in/sites/default/files/VacCircHandwritingExpert-Engl-020726.pdf"

print("Testing Gemini AI Engine... Please wait (takes 5-10 seconds)...")
result = parse_pdf_via_gemini(sample_pdf)

if result:
    print("\n🔥 SUCCESS! GEMINI OUTPUT:")
    print(json.dumps(result, indent=4))
else:
    print("\n❌ FAILED! Logs check karein (`logs/pipeline.log`) to see what went wrong.")
