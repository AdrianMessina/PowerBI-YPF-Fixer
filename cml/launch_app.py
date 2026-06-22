"""CML Launch Script — starts Streamlit on CDSW_APP_PORT.

Cloudera AI corre la app detrás de un proxy Istio que espera la app
escuchando en CDSW_APP_PORT (típicamente 8100) en 0.0.0.0. Si un
restart deja un proceso Streamlit zombie ocupando el puerto, el
nuevo arranque falla con 'Port X is not available'. Por eso limpiamos
procesos viejos antes de arrancar.
"""

import os
import subprocess
import time

port = os.environ.get("CDSW_APP_PORT", "8501")

# ── Limpiar procesos Streamlit zombie del restart anterior ──
# Cloudera 'Restart' a veces no libera el puerto a tiempo.
try:
    subprocess.run(["pkill", "-9", "-f", "streamlit"], check=False)
    time.sleep(2)  # dar tiempo al OS a liberar el socket
except Exception as e:
    print(f"[warn] pkill streamlit fallo (no critico): {e}")

print(f"Starting Power BI Fixer on port {port}...")

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    # 0.0.0.0 para que el proxy Istio de Cloudera alcance al container.
    "--server.address=0.0.0.0",
    "--server.headless=true",
    # enableCORS=false es incompatible con enableXsrfProtection=true (default).
    # Dejamos el comportamiento por defecto (CORS activo + XSRF activo).
    "--browser.gatherUsageStats=false",
])
