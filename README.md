# 🔧 Power BI Fixer

**Suite completa de análisis y auto-corrección para reportes Power BI con diseño corporativo YPF**

> Desarrollado por **Equipo de Visualización de Datos** | YPF S.A. | Abril 2026

---

## ✨ Qué Hay de Nuevo en v2.0

### 🔧 Motor de Auto-Fix (14 Fixers)

La v2.0 introduce capacidades de **corrección automática** de problemas, inspiradas en [pbi_fixer](https://github.com/KornAlexander/pbi_fixer) pero **sin depender de Microsoft Fabric**. Funciona 100% local con proyectos PBIP/PBIR.

#### Report Fixers (5)
- ✅ **Reemplazar pie charts** por bar charts
- ✅ **Actualizar páginas a Full HD** (1920x1080) con escalado proporcional
- ✅ **Alinear visuals a grilla** de 8px
- ✅ **Eliminar custom visuals sin uso**
- ✅ **Deshabilitar ShowItemsWithNoData**

#### Model Fixers (2)
- ✅ **Corregir relaciones bidireccionales**
- ✅ **Detectar columnas calculadas** convertibles a medidas

#### BPA Fixers (7)
- ✅ **Reemplazar '/' con DIVIDE()** en DAX
- ✅ **Agregar descripciones a medidas**
- ✅ **Sugerir formatos para medidas**
- ✅ **Estandarizar nombres** (trim, capitalización)
- ✅ **Ocultar columnas FK**
- ✅ **Corregir SummarizeBy**
- ✅ **Detectar tipos floating point incorrectos**

### 🎯 Mejoras de Arquitectura

- **Modelos de datos tipados** con `@dataclass` para mejor mantenibilidad
- **Parsers modulares** separados por formato (PBIX, PBIP, TMDL)
- **Engine de fixers extensible** con clase base y registro automático
- **UI moderna** con tabs, métricas en cards, y badges de categoría
- **Backup automático** antes de aplicar fixes
- **Modos de ejecución**: Scan | Fix | Scan+Fix

---

## 🚀 Inicio Rápido

### Instalación (Windows)

**Opción 1: Launcher Automático (Recomendado)**
```bash
# Doble clic en:
Power BI Fixer.bat
```
El launcher crea el venv, instala dependencias y abre el navegador automáticamente.

**Opción 2: Manual**
```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Lanzar aplicación
streamlit run app.py
```

**Red corporativa con proxy:**
```bash
pip install --proxy http://proxy-azure -r requirements.txt
```

### Uso

1. **Seleccionar tipo de archivo** en la barra lateral
   - **PBIP (Proyecto)**: Carpeta `.Report` o archivo `.pbip` → Análisis completo + Auto-fix ✅
   - **PBIX (Archivo)**: Archivo `.pbix` → Análisis de solo lectura ⚠️

2. **Cargar archivo/proyecto**
   - PBIX: Drag & drop
   - PBIP: Ingresar ruta completa (ej: `C:\Proyectos\MiReporte.Report`)

3. **Presionar "Analizar"**

4. **Explorar resultados** en las pestañas:
   - **Overview**: Score, resumen ejecutivo, métricas clave
   - **Métricas Detalladas**: Deep dive por categoría (Modelo, DAX, Relaciones, Visuals)
   - **Recomendaciones**: Lista categorizada de problemas con filtros
   - **Auto-Fix**: 🆕 Motor de corrección automática (solo PBIP)
   - **Exportar**: Descargar reportes HTML/JSON

5. **Aplicar fixes** (solo PBIP):
   - Ir a pestaña "Auto-Fix"
   - Presionar "Escanear Problemas"
   - Revisar los fixers con issues detectados
   - Opción A: "Corregir Todo" (crea backup automático)
   - Opción B: Aplicar fixes individuales expandiendo cada card

---

## 📋 Capacidades Completas

### Análisis Automatizado (22 Reglas)

| Categoría | Métricas Analizadas |
|-----------|---------------------|
| **Modelo de Datos** | Tablas, columnas, columnas calculadas, tablas calculadas, auto date/time |
| **DAX** | Medidas totales, medidas complejas, descripciones, formatos, división con '/' |
| **Relaciones** | Total, bidireccionales, inactivas |
| **Visualizaciones** | Total, por página, por tipo, slicers, botones, shapes, textboxes, imágenes |
| **Diseño** | Tamaño de páginas, alineación, custom visuals, imágenes embebidas, tema |
| **Performance** | Tamaño del modelo, número de filtros, ShowItemsWithNoData |

### Sistema de Scoring

- **Ponderado** por importancia (ej: DAX complejo = 18%, Visuals por página = 12%)
- **Tres umbrales**: Good / Warning / Critical
- **Score final**: 0-100 con categorías:
  - 90-100: Excelente ✅
  - 75-89: Bueno 👍
  - 60-74: Atención ⚠️
  - 0-59: Crítico ❌

### Formatos Soportados

| Formato | Lectura | Modelo | Report | Auto-Fix |
|---------|:-------:|:------:|:------:|:--------:|
| **PBIP (PBIR)** | ✅ | ✅ | ✅ | ✅ |
| **PBIP (Legacy)** | ✅ | ✅ | ✅ | ✅ |
| **PBIX** | ✅ | ⚠️¹ | ✅ | ❌² |

¹ El modelo en PBIX puede no estar disponible si está comprimido  
² Los archivos .pbix son binarios y no pueden modificarse directamente

---

## 🏗️ Arquitectura

```
powerbi_analyzer_v2/
├── config/
│   └── thresholds.yaml          # Umbrales configurables
├── core/
│   ├── models.py                # Dataclasses tipados
│   ├── parsers/
│   │   ├── pbix_parser.py       # Parser PBIX (ZIP)
│   │   ├── pbip_parser.py       # Parser PBIP/PBIR
│   │   └── tmdl_parser.py       # Parser TMDL
│   ├── analyzers/
│   │   └── analyzer.py          # Motor de análisis
│   └── fixers/
│       ├── base.py              # BaseFixer + FixerEngine
│       ├── report_fixers.py     # Fixers de report layer
│       ├── model_fixers.py      # Fixers de semantic model
│       └── bpa_fixers.py        # Best practice fixers
├── ui/
│   ├── components.py            # Componentes reutilizables
│   ├── styles.py                # CSS corporativo
│   ├── tab_overview.py          # Tab Overview
│   ├── tab_metrics.py           # Tab Métricas
│   ├── tab_recommendations.py   # Tab Recomendaciones
│   ├── tab_fixer.py             # Tab Auto-Fix 🆕
│   └── tab_export.py            # Tab Exportar
├── app.py                       # Aplicación principal Streamlit
├── requirements.txt             # Dependencias
├── Power BI Analyzer 2.0.bat   # Launcher Windows
└── README.md                    # Este archivo
```

---

## 🔧 Desarrollo de Fixers Personalizados

Para agregar un nuevo fixer:

1. **Crear clase** heredando de `BaseFixer`:
```python
from core.fixers.base import BaseFixer

class FixMiRegla(BaseFixer):
    fixer_id = "fix_mi_regla"
    name = "Mi Regla Custom"
    description = "Descripción de qué hace"
    category = "report"  # "report" | "model" | "bpa"
    severity = "warning"
    requires_pbip = True  # Si solo funciona con PBIP

    def scan(self):
        # Detectar problemas
        for issue in self._detect_issues():
            self.issues.append(f"Problema: {issue}")

    def fix(self):
        # Corregir problemas
        for issue in self.issues:
            self._apply_fix(issue)
            self.fixes_applied.append(f"Corregido: {issue}")
```

2. **Registrar** en `core/fixers/__init__.py`:
```python
from core.fixers.mi_fixer import FixMiRegla

ALL_FIXERS = [
    # ... otros fixers
    FixMiRegla,
]
```

3. **Listo** - Aparecerá automáticamente en la pestaña Auto-Fix

---

## 🆚 Comparación con v1.1

| Característica | v1.1 | v2.0 |
|----------------|:----:|:----:|
| Análisis best practices | ✅ | ✅ |
| Scoring ponderado | ✅ | ✅ |
| Soporte PBIP/PBIR | ✅ | ✅ |
| Soporte PBIX | ✅ | ✅ |
| Exportar HTML/JSON | ✅ | ✅ |
| **Auto-fix de problemas** | ❌ | ✅ 14 fixers |
| **Modelos de datos tipados** | ❌ | ✅ |
| **Backup automático** | ❌ | ✅ |
| **Parsers modulares** | ❌ | ✅ |
| **UI moderna con badges** | ❌ | ✅ |
| **Modo Scan/Fix/Scan+Fix** | ❌ | ✅ |
| Código duplicado | ⚠️ Mucho | ✅ Refactorizado |

---

## ⚙️ Configuración

Los umbrales son configurables en `config/thresholds.yaml`:

```yaml
thresholds:
  visualizations_per_page:
    good: 10
    warning: 15
    critical: 20
    weight: 0.12
  # ... más umbrales
```

Modifica los valores según las necesidades de tu organización.

---

## 🐛 Troubleshooting

### ⚠️ Error: "np.unicode_ was removed in NumPy 2.0" (CRÍTICO)
- **Síntoma**: `AttributeError: 'np.unicode_' was removed in the NumPy 2.0 release. Use 'np.str_' instead.`
- **Causa**: NumPy 2.0+ tiene breaking changes incompatibles con algunas dependencias (xarray, plotly)
- **Solución rápida**: 
  ```bash
  pip uninstall numpy -y
  pip install "numpy<2.0"
  pip install -r requirements.txt
  ```
- **Prevención**: Usar `install.bat` que instala la versión correcta automáticamente
- **Nota**: `requirements.txt` ya está configurado con `numpy<2.0` desde v2.0.1

### "Model analysis not available" en PBIX
- **Causa**: El modelo está comprimido en formato binario
- **Solución**: Convertir a PBIP: `Archivo > Guardar como > Proyecto Power BI (.pbip)`

### Fixes no se aplican
- **Verifica**: Estás usando formato PBIP (no PBIX)
- **Verifica**: Tienes permisos de escritura en la carpeta
- **Verifica**: No tienes el proyecto abierto en Power BI Desktop

### Errores al parsear TMDL
- **Causa**: Sintaxis TMDL compleja con nombres especiales
- **Solución**: Los parsers regex pueden no cubrir todos los edge cases. Reportar el caso específico.

---

## 📝 Roadmap

### v2.1 (Planeado)
- [ ] Soporte para edición de BIM JSON (además de TMDL)
- [ ] Más fixers: upgrade PBIRLegacy, migrate slicers, IBCS charts
- [ ] Integración con pbi-cli para deployment
- [ ] Modo batch (analizar múltiples reportes)

### v2.2 (Futuro)
- [ ] Historial de análisis y comparación de scores
- [ ] Generación de reportes PDF
- [ ] API REST para integración CI/CD
- [ ] Dashboard de métricas corporativas

---

## 🤝 Contribución

Este proyecto es parte del ecosistema de herramientas Power BI de YPF. Para contribuir:

1. Reportar bugs/sugerencias en el canal interno
2. Proponer nuevos fixers vía pull request
3. Documentar casos de uso específicos

---

## 📄 Licencia

Uso interno - YPF S.A.

---

## 👥 Créditos

**Desarrollado por:** Equipo de Visualización de Datos - YPF S.A.

**Basado en:**
- Power BI Analyzer v1.1 (base de análisis)
- [pbi_fixer](https://github.com/KornAlexander/pbi_fixer) de Alexander Korn (inspiración para auto-fix)
- [Semantic Link Labs](https://github.com/microsoft/semantic-link-labs) de Microsoft (conceptos de BPA)

**Versión:** 2.0  
**Última actualización:** Abril 2026

---

**¿Preguntas?** Contacta al equipo de Visualización de Datos.
