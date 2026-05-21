# Changelog

## [2.0] - 2026-04-13

### 🚀 Added - Major Features
- **Auto-Fix Engine**: 14 fixers automáticos para corregir problemas sin abrir Power BI Desktop
  - 5 Report Fixers (pie charts, page size, alignment, custom visuals, ShowItemsWithNoData)
  - 2 Model Fixers (bidirectional relationships, calculated columns detection)
  - 7 BPA Fixers (DIVIDE, descriptions, formats, naming, FK hiding, SummarizeBy, float types)
- **FixerEngine**: Sistema extensible con clase base `BaseFixer` y registro automático
- **Backup automático**: Crea respaldo antes de aplicar fixes
- **Modos de ejecución**: Scan | Fix | Scan+Fix para cada fixer
- **UI moderna**: Tab Auto-Fix con categorización por tipo (Report/Model/BPA)

### ✨ Improved - Architecture
- **Modelos tipados**: Migración de `dict` a `@dataclass` (AnalysisResult, Recommendation, etc.)
- **Parsers modulares**: Separación clara entre PBIXParser, PBIPParser y TMDLParser
- **Código DRY**: Eliminación de duplicación entre PBIXAnalyzer y PBIPAnalyzer
- **Session state**: Uso de `st.session_state` para persistir análisis
- **CSS modular**: Estilos separados en `ui/styles.py`
- **Components reutilizables**: Cards, badges, charts compartidos

### 🎨 UI Enhancements
- **Badges de categoría**: Report/Model/BPA con colores distintivos
- **Cards mejoradas**: Fix cards con estados (has-issues, fixed, no-issues)
- **Filtros en Recommendations**: Por severidad y fixable
- **Tabs organizadas**: Overview, Métricas, Recomendaciones, Auto-Fix, Exportar
- **Sidebar summary**: Métricas clave y conteo de problemas
- **Theme corporativo YPF**: Azul oscuro con acentos

### 📦 New Dependencies
- No nuevas dependencias externas (solo stdlib + streamlit, pandas, plotly, pyyaml)

### 🐛 Fixed
- Parseo de TMDL con nombres de tabla con caracteres especiales
- Detección de custom visuals en formato PBIR
- Cálculo de score cuando model analysis no está disponible (PBIX)
- Manejo de None en métricas de modelo

### ⚠️ Breaking Changes
- API cambió de dict a dataclasses: acceso via `result.total_pages` en vez de `result['metrics']['total_pages']`
- El análisis ahora retorna `AnalysisResult` en vez de dict plano

### 📝 Documentation
- README.md completo con guía de inicio rápido
- Documentación de arquitectura de fixers
- Comparación detallada con v1.1
- Roadmap para v2.1 y v2.2

---

## [1.1] - 2026-03 (Baseline)

### Features
- Análisis de best practices (22 reglas)
- Scoring ponderado 0-100
- Soporte PBIP/PBIR y PBIX
- Exportar HTML/JSON
- Detección de TMDL format
- UI Streamlit con 5 tabs

### Known Issues
- Solo detección, sin capacidad de fix
- Código duplicado entre PBIXAnalyzer y PBIPAnalyzer
- Modelo no disponible en muchos PBIX
- Recomendaciones hardcoded sin fixer engine
