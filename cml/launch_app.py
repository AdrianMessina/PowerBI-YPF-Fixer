"""CML Launch Script — starts Streamlit on CDSW_APP_PORT.

Cloudera AI corre este script dentro de un kernel IPython. Si usamos
subprocess.run(["streamlit", ...]) el kernel sigue vivo en el proceso
padre y sus puertos ZMQ pueden chocar con CDSW_APP_PORT.

La solucion correcta es os.execvp(): reemplaza la imagen del proceso
actual (Python+kernel) con Streamlit, manteniendo el mismo PID.
Cloudera ve el proceso vivo, los recursos del kernel se liberan, y
Streamlit binde a CDSW_APP_PORT sin conflicto.

Diagnostico fallback via /proc (no requiere lsof/ss/netstat — minimo
en muchos contenedores de Cloudera).
"""

import os
import re
import sys

port = os.environ.get("CDSW_APP_PORT", "8501")


def diagnose_port_via_proc(p: int) -> None:
    """Imprime quien tiene el puerto usando solo /proc (sin tools externos)."""
    port_hex = format(p, "04X")
    print(f"[diag] Buscando puerto {p} (=0x{port_hex}) en /proc/net/tcp")

    inode_to_pid = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fd_dir = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                link = os.readlink(f"{fd_dir}/{fd}")
            except OSError:
                continue
            m = re.match(r"socket:\[(\d+)\]", link)
            if m:
                inode_to_pid[m.group(1)] = pid

    try:
        with open("/proc/net/tcp") as f:
            for line in f.readlines()[1:]:  # skip header
                parts = line.split()
                if len(parts) < 10:
                    continue
                local = parts[1]
                if not local.endswith(f":{port_hex}"):
                    continue
                state = parts[3]
                inode = parts[9]
                pid = inode_to_pid.get(inode, "?")
                cmdline = ""
                if pid != "?":
                    try:
                        with open(f"/proc/{pid}/cmdline") as cf:
                            cmdline = cf.read().replace("\x00", " ").strip()
                    except OSError:
                        pass
                print(f"[diag]   local={local}  state={state}  pid={pid}  cmd={cmdline}")
    except OSError as e:
        print(f"[diag] No pude leer /proc/net/tcp: {e}")


print(f"[init] Preparando Streamlit en puerto {port}")
try:
    diagnose_port_via_proc(int(port))
except Exception as e:
    print(f"[diag] Falló el diagnóstico (no critico): {e}")

cmd = [
    "streamlit", "run", "app.py",
    f"--server.port={port}",
    # 0.0.0.0 para que el proxy Istio de Cloudera alcance al container.
    "--server.address=0.0.0.0",
    "--server.headless=true",
    "--browser.gatherUsageStats=false",
]

print(f"[init] Ejecutando: {' '.join(cmd)}")
sys.stdout.flush()

# execvp REEMPLAZA el proceso actual (incluyendo el kernel IPython).
# Esto libera los puertos que tenia tomados Python y deja a Streamlit
# bindear CDSW_APP_PORT limpio. NO retorna si tiene exito.
os.execvp(cmd[0], cmd)
