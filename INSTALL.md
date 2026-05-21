# Instrucciones de Instalación - Power BI Analyzer v2

## Requisitos Previos
- Python 3.8 o superior
- pip instalado

## Instalación

### Opción 1: Instalación rápida (Recomendada)

```bash
# 1. Descomprimir el archivo ZIP
# 2. Navegar al directorio
cd powerbi_analyzer_v2

# 3. Crear entorno virtual (recomendado)
python -m venv venv

# 4. Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# 5. Instalar dependencias
pip install -r requirements.txt
```

### Opción 2: Si tienes NumPy 2.0 instalado

Si ya tienes NumPy 2.0+ instalado y obtienes el error:
```
AttributeError: `np.unicode_` was removed in the NumPy 2.0 release
```

**Solución:**
```bash
# Desinstalar numpy actual y reinstalar versión compatible
pip uninstall numpy -y
pip install "numpy<2.0"
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run test_analyzer.py
```

## Problemas Comunes

### Error: np.unicode_ was removed
- **Causa:** NumPy 2.0+ no es compatible con algunas dependencias
- **Solución:** Instalar NumPy <2.0 (ver Opción 2 arriba)

### Error: ModuleNotFoundError
- **Causa:** Dependencias no instaladas
- **Solución:** Ejecutar `pip install -r requirements.txt`

## Soporte
Para reportar problemas o preguntas, contactar al desarrollador.
