"""CML Launch Script — starts Streamlit on CDSW_APP_PORT."""

import os
import subprocess

port = os.environ.get("CDSW_APP_PORT", "8501")

print(f"Starting Power BI Fixer on port {port}...")

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    "--server.address=127.0.0.1",
    "--server.headless=true",
    "--server.enableCORS=false",
    "--browser.gatherUsageStats=false",
])
