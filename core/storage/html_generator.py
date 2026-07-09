import csv
import os
from pathlib import Path

CSV_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "sarkari_jobs.csv"
HTML_OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "index.html"

def generate_static_website():
    """
    Reads the latest job entries from the CSV data logs and compiles a clean,
    highly responsive, Sarkari-result styled HTML landing grid system.
    """
    if not os.path.exists(CSV_FILE_PATH):
        print("Error: CSV data logs missing. Cannot compile web interface.")
        return False
        
    job_rows_html = ""
    
    with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            job_rows_html += f"""
            <tr>
                <td><a href="{row.get('Official Website', '#')}" target="_blank" class="job-link">{row.get('Job Title', 'N/A')}</a></td>
                <td><span class="badge org-badge">{row.get('Organization', 'N/A')}</span></td>
                <td><span class="badge vacancy-badge">{row.get('Total Vacancies', '0')}</span></td>
                <td class="text-danger font-weight-bold">{row.get('Last Date', 'N/A')}</td>
            </tr>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sarkari Engine | Latest Government Jobs 2026</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f4f6f9; font-family: sans-serif; }}
        .header-main {{ background-color: #990000; color: white; padding: 20px; text-align: center; border-bottom: 5px solid #ffcc00; }}
        .marquee-box {{ background-color: #000; color: #fff; padding: 5px; font-weight: bold; }}
        .card-table {{ border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); border-top: 4px solid #990000; }}
        .table thead {{ background-color: #efefef; color: #333; }}
        .job-link {{ color: #0000cc; font-weight: bold; text-decoration: none; }}
        .job-link:hover {{ text-decoration: underline; color: #ff0000; }}
        .badge {{ padding: 6px 10px; font-size: 13px; }}
        .org-badge {{ background-color: #e7f3ff; color: #007bff; }}
        .vacancy-badge {{ background-color: #e6f9ed; color: #198754; }}
    </style>
</head>
<body>

    <div class="header-main">
        <h1>SARKARI ENGINE AUTOMATION</h1>
        <p class="mb-0">100% Automated Government Job Updates Portal</p>
    </div>

    <div class="marquee-box">
        <marquee scrollamount="5">⚡ Welcome to Sarkari Engine Free Live Deployment Sandbox - Latest UPSC/SSC Notifications Updated Automatically ⚡</marquee>
    </div>

    <div class="container my-5">
        <div class="card card-table bg-white p-4">
            <h3 class="text-center text-dark mb-4">🔥 Latest Advertisements & Online Forms</h3>
            <div class="table-responsive">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>Job Post Title & Details</th>
                            <th>Agency</th>
                            <th>Vacancies</th>
                            <th>Last Date to Apply</th>
                        </tr>
                    </thead>
                    <tbody>
                        {job_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <footer class="text-center py-4 bg-dark text-white-50">
        <p class="mb-0">&copy; 2026 SarkariEngine. Hosted Free via GitHub Cloud Network.</p>
    </footer>

</body>
</html>
"""

    with open(HTML_OUTPUT_PATH, mode='w', encoding='utf-8') as html_file:
        html_file.write(html_content)
        
    print(f"✅ Live Web Frontend Interface generated successfully at: {HTML_OUTPUT_PATH}")
    return True

if __name__ == "__main__":
    generate_static_website()
