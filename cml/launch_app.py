"""CML Launch Script — starts Streamlit on CDSW_APP_PORT.

Cloudera AI Applications con Editor=JupyterLab/Python ejecutan ESTE archivo
dentro de un kernel Jupyter, sin importar la extensión. Por eso:
  - Usamos subprocess.run() (NO os.execvp ni .sh): mantiene el kernel vivo,
    streamlit corre como hijo, Cloudera ve la app viva.
  - Streamlit escucha en 127.0.0.1 (NO 0.0.0.0): el port-forwarder de
    Cloudera ya ocupa pod-IP:CDSW_APP_PORT y forwardea a localhost:PUERTO.
  - Desactivamos XSRF + CORS: el proxy Istio agrega headers que rompen
    XSRF, y enableCORS=false necesita enableXsrfProtection=false para
    coexistir.
"""

import os
import subprocess

port = os.environ.get("CDSW_APP_PORT", "8501")

print(f"[init] Launching Power BI Fixer on 127.0.0.1:{port}", flush=True)

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    "--server.address=127.0.0.1",
    "--server.headless=true",
    "--server.enableCORS=false",
    "--server.enableXsrfProtection=false",
    "--browser.gatherUsageStats=false",
])
