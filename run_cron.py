import time
import subprocess
import os

print("🔄 Automated Sarkari Engine Cron Runner Activated...")

while True:
    print("⏳ Running live scraping cycle...")
    # Execute the master python pipeline
    subprocess.run(["python", "-m", "run_pipeline"])
    
    # Auto Git push changes to refresh GitHub Pages instantly
    print("📤 Pushing fresh data updates to cloud storage...")
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "cron-update: auto-sync jobs raw grid"])
    subprocess.run(["git", "push", "origin", "main"])
    
    print("💤 Cycle done. Sleeping for 1 hour...")
    time.sleep(3600) # 1 hour delay
