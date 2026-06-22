"""CML Launch Script — starts Streamlit on CDSW_APP_PORT."""

import os
import subprocess

port = os.environ.get("CDSW_APP_PORT", "8501")

print(f"Starting Power BI Fixer on port {port}...")

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    # 0.0.0.0 para que el proxy Istio de Cloudera alcance al container.
    # 127.0.0.1 hace que Streamlit solo escuche en loopback → 503 vía proxy.
    "--server.address=0.0.0.0",
    "--server.headless=true",
    "--server.enableCORS=false",
    "--browser.gatherUsageStats=false",
])
