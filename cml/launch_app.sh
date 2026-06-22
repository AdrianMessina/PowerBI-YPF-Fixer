#!/bin/bash
# CML Launch Script (bash) — bypasses PBJ Workbench / Jupyter kernel layer.
#
# Cloudera AI Applications con entrypoint .py corren el script dentro de
# un kernel Jupyter (PBJ Workbench). Eso causa problemas:
#   - Si usamos subprocess.run() el kernel queda corriendo y puede chocar puertos.
#   - Si usamos os.execvp() el kernel muere y Cloudera mata el workload.
#
# Con entrypoint .sh, Cloudera ejecuta bash directo (sin kernel). El comando
# `exec` reemplaza el proceso bash por Streamlit manteniendo el mismo PID.
# Cloudera ve un proceso vivo, Streamlit binde su puerto, todos contentos.
#
# Streamlit escucha en 127.0.0.1:CDSW_APP_PORT porque el port-forwarder
# de Cloudera (registrado como engineHost=pod-ip:CDSW_APP_PORT) ya tiene
# 0.0.0.0 ocupado y forwardea desde la pod-ip hacia localhost:CDSW_APP_PORT.

PORT="${CDSW_APP_PORT:-8501}"

echo "[init] Launching Power BI Fixer on 127.0.0.1:${PORT}"

cd "$(dirname "$0")/.."  # ir al root del repo (donde está app.py)

exec streamlit run app.py \
    --server.port="${PORT}" \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --browser.gatherUsageStats=false
