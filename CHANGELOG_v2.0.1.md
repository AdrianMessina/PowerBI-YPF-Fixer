# 🔧 Power BI Fixer v2.0.1 - Parche de Compatibilidad

**Fecha:** 19 de Mayo de 2026  
**Tipo:** Hotfix  
**Prioridad:** CRÍTICA

---

## 🐛 Problema Resuelto

**Error reportado por usuario:**
```
AttributeError: `np.unicode_` was removed in the NumPy 2.0 release. Use `np.str_` instead.
```

**Causa raíz:**
- NumPy 2.0 fue lanzado con breaking changes
- Las dependencias `xarray` (usada por `plotly`) y otras aún usan `np.unicode_`
- El `requirements.txt` no especificaba versión de NumPy, instalando 2.0+ por defecto

---

## ✅ Cambios Implementados

### 1. **requirements.txt** (CRÍTICO)
```diff
# Data processing
pandas>=2.2.0
+ numpy<2.0  # Pin to <2.0 for compatibility with plotly/xarray dependencies
```

### 2. **INSTALL.md** (NUEVO)
- Instrucciones detalladas de instalación
- Solución específica para el error de NumPy 2.0
- Guía de problemas comunes

### 3. **install.bat** (NUEVO)
- Script automático de instalación para Windows
- Crea venv, instala dependencias con versión correcta

### 4. **run.bat** (NUEVO)
- Script simple para ejecutar la app después de instalar
- Verifica que el venv exista

### 5. **README.md** (ACTUALIZADO)
- Nueva sección de Troubleshooting para error de NumPy
- Marcado como CRÍTICO
- Instrucciones de solución rápida

---

## 📦 Qué Incluir en el ZIP para Distribución

### ✅ INCLUIR (Archivos esenciales):
```
powerbi_analyzer_v2/
├── core/                      # Todo el código fuente
├── ui/                        # Interfaz Streamlit
├── config/                    # Configuración
├── requirements.txt           # ⚠️ CON FIX DE NUMPY
├── requirements_cloud.txt
├── README.md                  # ⚠️ ACTUALIZADO
├── INSTALL.md                 # 🆕 NUEVO
├── CHANGELOG_v2.0.1.md       # 🆕 Este archivo
├── Power BI Fixer.bat        # Launcher principal
├── install.bat               # 🆕 Instalador alternativo
├── run.bat                   # 🆕 Ejecutor simple
├── app.py                    # Script principal
└── test_analyzer.py          # Script de test
```

### ❌ NO INCLUIR:
```
❌ venv/                      # 156 MB - el usuario debe crearlo
❌ __pycache__/               # Archivos compilados Python
❌ *.pyc                      # Bytecode Python
❌ .git/                      # Historial de Git
❌ .vscode/                   # Configuración de editor
❌ *.log                      # Logs
❌ .DS_Store                  # Archivos de macOS
```

---

## 🚀 Proceso de Empaquetado Recomendado

### Opción 1: Comprimir manualmente
```bash
# Desde C:\Users\SE46958\1 - Claude - Proyecto viz\
# Seleccionar carpeta powerbi_analyzer_v2
# Click derecho > Enviar a > Carpeta comprimida

# Asegurar que NO incluye:
# - venv/ (muy pesado)
# - __pycache__/
```

### Opción 2: Script de empaquetado (PowerShell)
```powershell
# Crear un script package.ps1
$exclude = @('venv', '__pycache__', '*.pyc', '.git', '.vscode', '*.log')
Compress-Archive -Path "C:\Users\SE46958\1 - Claude - Proyecto viz\powerbi_analyzer_v2" `
                 -DestinationPath "C:\Users\SE46958\Desktop\PowerBI_Fixer_v2.0.1.zip" `
                 -Force `
                 -CompressionLevel Optimal
```

---

## 📝 Instrucciones para el Usuario Final

**Agregar este texto en el email o comunicación:**

```
Hola,

Adjunto la versión 2.0.1 de Power BI Fixer con un hotfix crítico de compatibilidad.

IMPORTANTE - INSTALACIÓN ACTUALIZADA:

1. Descomprimir el archivo ZIP
2. Ejecutar: install.bat (NUEVO - recomendado)
   O usar el launcher habitual: Power BI Fixer.bat

El archivo install.bat asegura que se instale la versión correcta de las dependencias.

Si encuentras el error:
"AttributeError: np.unicode_ was removed"

Solución rápida:
  pip uninstall numpy -y
  pip install "numpy<2.0"
  pip install -r requirements.txt

Cualquier problema, revisar INSTALL.md dentro del ZIP.

Saludos,
Equipo de Visualización de Datos
```

---

## 🔍 Testing Recomendado

Antes de distribuir, probar en una máquina limpia:

```bash
# 1. Descomprimir ZIP
# 2. Ejecutar install.bat
# 3. Verificar que instala numpy < 2.0:
python -c "import numpy; print(numpy.__version__)"
# Debe mostrar 1.x.x, NO 2.x.x

# 4. Ejecutar app:
run.bat
# Debe abrir sin errores
```

---

## 📊 Impacto

- **Criticidad:** Alta - La app no arranca sin este fix
- **Usuarios afectados:** Cualquiera con NumPy 2.0+ instalado (por defecto en instalaciones nuevas)
- **Solución:** Inmediata - Forzar numpy<2.0 en requirements

---

## 🔄 Próximos Pasos (Opcional - Futuro)

### v2.1 (Cuando xarray soporte NumPy 2.0):
- Actualizar a `numpy>=2.0` cuando las dependencias sean compatibles
- Monitorear releases de:
  - xarray: https://github.com/pydata/xarray/releases
  - plotly: https://github.com/plotly/plotly.py/releases

---

**Versión:** 2.0.1  
**Build:** 2026-05-19  
**Responsable:** Equipo de Visualización de Datos
