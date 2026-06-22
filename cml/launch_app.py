"""CML Launch Script — starts Streamlit on CDSW_APP_PORT.

Cloudera AI corre la app detrás de un proxy Istio que espera la app
escuchando en CDSW_APP_PORT (típicamente 8100) en 0.0.0.0. Si un
restart deja un proceso zombie ocupando el puerto o el socket queda
en TIME_WAIT, el nuevo arranque falla con 'Port X is not available'.

Estrategia:
  1. Diagnosticar quién tiene el puerto
  2. Matar por PUERTO (no por nombre) — fuser/lsof son más confiables que pkill
  3. Loop de espera: hasta 30s polleando el puerto hasta que esté libre
  4. Recién ahí arrancar Streamlit
"""

import os
import socket
import subprocess
import sys
import time

port = os.environ.get("CDSW_APP_PORT", "8501")
port_int = int(port)


def diagnose_port(p: int) -> None:
    """Imprime quién tiene el puerto ocupado (best-effort)."""
    for cmd in (["lsof", "-i", f":{p}"],
                ["ss", "-tlnp", f"sport = :{p}"],
                ["netstat", "-tlnp"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if out.stdout.strip():
                print(f"[diag] {' '.join(cmd)}:")
                print(out.stdout)
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    print(f"[diag] No se pudo diagnosticar el puerto {p} (lsof/ss/netstat no disponibles).")


def kill_port(p: int) -> None:
    """Mata procesos ocupando el puerto p, probando varios métodos."""
    # Método 1: fuser (más directo)
    try:
        subprocess.run(["fuser", "-k", f"{p}/tcp"],
                       check=False, capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Método 2: lsof + kill (fallback)
    try:
        out = subprocess.run(["lsof", "-ti", f":{p}"],
                             capture_output=True, text=True, timeout=5)
        pids = [pid.strip() for pid in out.stdout.split() if pid.strip()]
        for pid in pids:
            try:
                subprocess.run(["kill", "-9", pid], check=False, timeout=3)
            except subprocess.TimeoutExpired:
                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Método 3: pkill por nombre (catch-all)
    try:
        subprocess.run(["pkill", "-9", "-f", "streamlit"], check=False, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def is_port_free(p: int) -> bool:
    """Devuelve True si el puerto p está libre para bindear."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", p))
        return True
    except OSError:
        return False
    finally:
        s.close()


def wait_for_port(p: int, timeout: int = 30) -> bool:
    """Polleá el puerto cada 1s hasta `timeout` segundos."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_free(p):
            return True
        time.sleep(1)
    return False


# ── Limpieza pre-arranque ──
print(f"[init] Limpiando puerto {port}...")
diagnose_port(port_int)
kill_port(port_int)
time.sleep(2)

if not wait_for_port(port_int, timeout=30):
    print(f"[ERROR] Puerto {port} sigue ocupado despues de 30s. Estado actual:")
    diagnose_port(port_int)
    print("[ERROR] No se puede arrancar Streamlit. Hacé un Stop completo de la "
          "app en Cloudera AI y volvé a Start (no solo Restart).")
    sys.exit(1)

print(f"[init] Puerto {port} libre. Arrancando Power BI Fixer...")

subprocess.run([
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    # 0.0.0.0 para que el proxy Istio de Cloudera alcance al container.
    "--server.address=0.0.0.0",
    "--server.headless=true",
    # enableCORS=false es incompatible con enableXsrfProtection=true (default).
    "--browser.gatherUsageStats=false",
])
