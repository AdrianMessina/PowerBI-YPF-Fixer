"""CML Launch Script — starts Streamlit on CDSW_APP_PORT.

Cloudera AI Applications:
- Ejecuta este .py dentro de un kernel Jupyter (PBJ Workbench).
- Por eso usamos subprocess.run() — mantiene el kernel vivo,
  Streamlit corre como hijo, Cloudera ve el workload vivo.

NOTA SOBRE EL BIND ADDRESS:
- 0.0.0.0 hace que Streamlit acepte conexiones desde la red del pod,
  necesario para que el gateway de Kubernetes (que llega a pod-IP:PORT)
  pueda alcanzar la app.
- 127.0.0.1 NO funciona en Cloudera AI Applications: el gateway no
  resuelve loopback dentro del container.

XSRF + CORS desactivados: el proxy Istio agrega headers que rompen
XSRF, y enableCORS=false necesita enableXsrfProtection=false.
"""

import os
import subprocess
import time

port = os.environ.get("CDSW_APP_PORT", "8501")

# Pequeño delay para evitar race-condition con el setup del engine
# (vimos antes "Port not available" cuando arrancábamos muy rápido).
time.sleep(3)

print(f"[init] Launching Power BI Fixer on 0.0.0.0:{port}", flush=True)

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    "--server.address=0.0.0.0",
    "--server.headless=true",
    "--server.enableCORS=false",
    "--server.enableXsrfProtection=false",
    "--browser.gatherUsageStats=false",
])
