"""Fixer tab — User-friendly, trust-focused auto-fix engine.

Design principles applied:
- Progressive disclosure (summary → category → detail on demand)
- Only show fixers WITH issues
- Compact buttons, not giant bars
- Tooltips on metrics explaining what they mean
- Each fixer explains WHAT it does and HOW it will fix
- Validation after every fix
"""

import streamlit as st
from core.models import AnalysisResult, FileType, FixMode
from core.fixers.base import FixerEngine
from core.environment import is_cloud


# ── Fixer descriptions: what each fixer does in plain language ──
FIXER_EXPLANATIONS = {
    "fix_pie_charts": {
        "what": "Los graficos de torta/dona dificultan comparar valores.",
        "action": "Reemplaza el tipo de visual de pieChart/donutChart a barChart en cada visual.json.",
    },
    "fix_page_size": {
        "what": "Paginas con resolucion menor a Full HD desaprovechan pantallas modernas.",
        "action": "Cambia width/height a 1920x1080 en page.json y escala posiciones de visuals proporcionalmente.",
    },
    "fix_visual_alignment": {
        "what": "Visuals desalineados se ven desprolijos.",
        "action": "Redondea x/y/width/height al multiplo de 8px mas cercano en cada visual.json.",
    },
    "fix_unused_custom_visuals": {
        "what": "Custom visuals registrados pero sin usar agregan peso al archivo.",
        "action": "Elimina la carpeta del custom visual de definition/customVisuals/.",
    },
    "fix_hide_visual_filters": {
        "what": "ShowItemsWithNoData genera queries innecesarias.",
        "action": "Remueve la propiedad showItemsWithNoData de cada visual.json afectado.",
    },
    "fix_duplicate_visuals": {
        "what": "Visuals con misma posicion y tipo son probablemente duplicados accidentales.",
        "action": "Solo reporta. Debe eliminarse manualmente en Power BI Desktop.",
    },
    "fix_overlapping_visuals": {
        "what": "Visuals superpuestos >50% pueden indicar errores de diseno.",
        "action": "Solo reporta. Reposicionar manualmente en Power BI Desktop.",
    },
    "fix_empty_pages": {
        "what": "Paginas sin visuals de datos confunden a los usuarios.",
        "action": "Solo reporta. Evaluar si la pagina debe eliminarse o completarse.",
    },
    "fix_visual_tab_order": {
        "what": "Tab order desordenado afecta accesibilidad (navegacion con teclado).",
        "action": "Reasigna tabOrder en cada visual.json siguiendo patron izquierda-derecha, arriba-abajo.",
    },
    "fix_large_card_count": {
        "what": "Mas de 10 cards por pagina genera muchas queries DAX simultaneas.",
        "action": "Solo reporta. Considere consolidar KPIs en menos cards o usar matrix.",
    },
    "fix_slicer_sync": {
        "what": "Paginas con cantidad de slicers muy distinta al promedio.",
        "action": "Solo reporta. Considere usar sync slicers para consistencia.",
    },
    "fix_bidirectional": {
        "what": "Relaciones bidireccionales causan ambiguedad y bajo rendimiento.",
        "action": "Cambia crossFilteringBehavior de bothDirections a oneDirection en TMDL/BIM.",
    },
    "fix_calculated_columns": {
        "what": "Columnas calculadas con agregaciones podrian ser medidas (menos memoria).",
        "action": "Solo reporta. Convertir manualmente a medida en Power BI Desktop.",
    },
    "fix_inactive_relationships": {
        "what": "Relaciones inactivas sin USERELATIONSHIP() son innecesarias.",
        "action": "Solo reporta. Eliminar manualmente si no se usa con USERELATIONSHIP().",
    },
    "fix_auto_datetime": {
        "what": "Tablas Auto Date/Time ocultas aumentan el tamano del modelo.",
        "action": "Solo reporta. Deshabilitar en Opciones > Carga de datos > Auto Date/Time.",
    },
    "fix_calendar_table": {
        "what": "Sin tabla calendario explicita no se puede usar Time Intelligence.",
        "action": "Crea un archivo Calendar.tmdl con tabla calculada DAX (2020-2030) con Year, Month, Quarter.",
    },
    "fix_measure_table": {
        "what": "Sin tabla dedicada las medidas quedan dispersas entre tablas de datos.",
        "action": "Crea _Measures.tmdl con una medida 'Last Refresh' = NOW().",
    },
    "fix_time_intelligence": {
        "what": "Sin Calculation Group de Time Intelligence hay que duplicar medidas YTD/PY.",
        "action": "Crea 'Time Intelligence.tmdl' con items: YTD, QTD, MTD, PY, YoY, YoY%.",
    },
    "fix_units_calc_group": {
        "what": "Sin Calculation Group de Unidades no se puede cambiar escala dinamicamente.",
        "action": "Crea 'Units.tmdl' con items: Valor, Miles (K), Millones (M), Porcentaje.",
    },
    "fix_divide_operator": {
        "what": "El operador / puede causar errores de division por cero.",
        "action": "Reemplaza patrones [A] / [B] por DIVIDE([A], [B]) en expresiones TMDL/BIM.",
    },
    "fix_measure_descriptions": {
        "what": "Medidas sin descripcion dificultan el mantenimiento del modelo.",
        "action": "Agrega description: 'Medida: [nombre]' en cada medida sin descripcion en TMDL/BIM.",
    },
    "fix_measure_formats": {
        "what": "Medidas sin formato se muestran con decimales arbitrarios.",
        "action": "Solo sugiere formatos basados en el nombre (pct->%, count->#,0).",
    },
    "fix_column_naming": {
        "what": "Nombres con espacios extra se ven mal en el panel de campos.",
        "action": "Elimina espacios al inicio/final de nombres de tablas, columnas y medidas en BIM.",
    },
    "fix_hide_foreign_keys": {
        "what": "Columnas FK visibles confunden a usuarios que no necesitan verlas.",
        "action": "Establece isHidden=true en columnas usadas como fromColumn en relaciones.",
    },
    "fix_summarize_by": {
        "what": "Columnas de texto/fecha con SummarizeBy permiten agregaciones accidentales.",
        "action": "Establece summarizeBy='none' en columnas string/dateTime/boolean en BIM.",
    },
    "fix_floating_point": {
        "what": "Columnas Double para IDs/keys causan errores de precision.",
        "action": "Solo sugiere cambiar tipo a Int64 o Decimal segun el nombre de la columna.",
    },
    "fix_measure_folders": {
        "what": "Medidas sin carpeta se acumulan en la raiz de la tabla.",
        "action": "Agrega displayFolder='Measures' a cada medida sin folder en TMDL/BIM.",
    },
    "fix_column_folders": {
        "what": "Tablas con +10 columnas sin carpetas son dificiles de navegar.",
        "action": "Solo reporta. Organizar manualmente en carpetas logicas.",
    },
    "fix_unreferenced_measures": {
        "what": "Medidas no referenciadas por otras pueden ser huerfanas.",
        "action": "Solo reporta. Verificar si se usan en visuals antes de eliminar.",
    },
    "fix_expensive_dax": {
        "what": "Patrones como FILTER(tabla), COUNTROWS(FILTER(...)) son costosos.",
        "action": "Solo sugiere alternativas mas eficientes (CALCULATE, SELECTEDVALUE, etc).",
    },
    "fix_missing_relationships": {
        "what": "Columnas con nombre similar sin relacion pueden necesitar una.",
        "action": "Solo reporta. Evaluar si la relacion es necesaria para el modelo.",
    },
    "fix_sort_by_column": {
        "what": "Columnas de texto como 'Mes' sin SortByColumn se ordenan alfabeticamente.",
        "action": "Solo sugiere agregar SortByColumn a columnas de nombres temporales.",
    },
    "fix_data_category_geo": {
        "what": "Columnas geograficas sin DataCategory no funcionan con mapas.",
        "action": "Asigna DataCategory (Country, City, etc.) basado en el nombre en BIM.",
    },
}


def render_fixer_tab(result: AnalysisResult):

    if result.file_type == FileType.PBIX:
        st.warning(
            "Auto-fix requiere formato **PBIP/PBIR**. "
            "En Power BI Desktop: Archivo > Guardar como > Proyecto (.pbip)"
        )
        _render_scan_only(result)
        return

    engine = FixerEngine()
    scan_key = f"scan_{result.report_path}"

    if scan_key not in st.session_state:
        st.session_state[scan_key] = None

    # ── Compact action bar ──────────────────────────────────────
    if is_cloud():
        col_scan, col_space = st.columns([1, 3])
        do_restore = False
    else:
        col_scan, col_restore, col_space = st.columns([1, 1, 2])
        with col_restore:
            do_restore = st.button("Restaurar Backup", use_container_width=True)

    with col_scan:
        do_scan = st.button("Escanear", type="primary", use_container_width=True)

    if do_scan:
        with st.spinner("Escaneando..."):
            scans = engine.scan_all(result)
            if not result.model_analysis_available:
                scans = [s for s in scans if s.category != "model"]
            st.session_state[scan_key] = scans

    if do_restore:
        _render_restore_ui(engine, result)
        return

    scans = st.session_state.get(scan_key)
    if scans is None:
        st.caption("Presione Escanear para detectar problemas corregibles.")
        return

    # ── Classify ────────────────────────────────────────────────
    with_issues = [s for s in scans if s.issues_found > 0]
    passing = [s for s in scans if s.issues_found == 0]
    total_issues = sum(s.issues_found for s in with_issues)

    if not with_issues:
        st.success(f"Sin problemas. {len(passing)} fixers escaneados, todos OK.")
        return

    auto_fixable = [s for s in with_issues if not getattr(s, "is_manual", False)]
    manual_only = [s for s in with_issues if getattr(s, "is_manual", False)]

    # ── Filter state ────────────────────────────────────────────
    filter_key = f"filter_{result.report_path}"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = "all"  # "all" | "auto" | "manual"

    active_filter = st.session_state[filter_key]

    # ── Clickable summary cards ─────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Problemas detectados", total_issues,
            help="Total de issues. Click para ver todos.",
        )
        if st.button(
            "Ver todos" if active_filter != "all" else "Mostrando todos",
            key="filter_all", use_container_width=True,
            disabled=(active_filter == "all"),
        ):
            st.session_state[filter_key] = "all"
            st.rerun()

    with c2:
        st.metric(
            "Auto-corregibles", f"{len(auto_fixable)} fixers",
            help="Fixers que modifican archivos automaticamente. Se crea backup antes de cada correccion.",
        )
        if st.button(
            "Filtrar" if active_filter != "auto" else "Filtro activo",
            key="filter_auto", use_container_width=True,
            disabled=(active_filter == "auto"),
        ):
            st.session_state[filter_key] = "auto"
            st.rerun()

    with c3:
        st.metric(
            "Requieren revision", f"{len(manual_only)} fixers",
            help="Problemas que requieren accion manual en Power BI Desktop.",
        )
        if st.button(
            "Filtrar" if active_filter != "manual" else "Filtro activo",
            key="filter_manual", use_container_width=True,
            disabled=(active_filter == "manual"),
        ):
            st.session_state[filter_key] = "manual"
            st.rerun()

    st.divider()

    # ── Apply filter ────────────────────────────────────────────
    if active_filter == "auto":
        visible = auto_fixable
        st.caption(f"Mostrando {len(visible)} fixers auto-corregibles")
    elif active_filter == "manual":
        visible = manual_only
        st.caption(f"Mostrando {len(visible)} fixers que requieren revision manual")
    else:
        visible = with_issues

    # ── Group by severity → then by category ──────────────────
    by_sev = {"critical": [], "warning": [], "info": []}
    for s in visible:
        sev = getattr(s, "severity", "warning")
        by_sev.get(sev, by_sev["warning"]).append(s)

    cat_labels = {
        "report": "Reporte / Visuals",
        "model": "Modelo Semantico",
        "bpa": "Best Practices",
    }
    cat_order = ["report", "model", "bpa"]

    for sev_key, label in [("critical", "Criticos"), ("warning", "Advertencias"), ("info", "Informativos")]:
        fixers = by_sev[sev_key]
        if not fixers:
            continue

        count = sum(s.issues_found for s in fixers)
        st.markdown(f"**{label}** ({count} issues en {len(fixers)} fixers)")

        # Sub-group by category
        by_cat = {}
        for s in fixers:
            cat = s.category if s.category in cat_labels else "bpa"
            by_cat.setdefault(cat, []).append(s)

        for cat_key in cat_order:
            cat_fixers = by_cat.get(cat_key)
            if not cat_fixers:
                continue

            cat_count = sum(s.issues_found for s in cat_fixers)
            st.caption(f"{cat_labels[cat_key]} ({cat_count})")

            for sr in cat_fixers:
                _render_fixer_item(sr, engine, result, scan_key)

        st.markdown("")

    # ── Passing (collapsed) ─────────────────────────────────────
    if passing and active_filter == "all":
        with st.expander(f"{len(passing)} fixers sin problemas"):
            names = [s.fixer_name for s in passing]
            st.caption(" | ".join(names))


def _render_fixer_item(sr, engine, result, scan_key):
    """Render one fixer as a compact expander with explanation."""
    is_manual = getattr(sr, "is_manual", False)
    explanation = FIXER_EXPLANATIONS.get(sr.fixer_id, {})
    what = explanation.get("what", "")
    action = explanation.get("action", "")

    # Build expander label
    tag = " [manual]" if is_manual else ""
    label = f"{sr.fixer_name} — {sr.issues_found}{tag}"

    with st.expander(label):
        # ── Explanation block ───────────────────────────────────
        if what:
            st.markdown(f"**Problema:** {what}")
        if action:
            st.markdown(f"**Correccion:** {action}")

        st.caption(
            f"Categoria: {sr.category.upper()} | "
            f"Confianza: {getattr(sr, 'confidence', 'high').upper()} | "
            f"Deteccion: {getattr(sr, 'detection_method', 'pattern_match')}"
        )

        # ── Issue details (compact, max 8) ──────────────────────
        st.markdown("---")
        shown = min(8, len(sr.details))
        for d in sr.details[:shown]:
            text = d
            for prefix in ("MANUAL:", "SUGERENCIA:", "REVISION:"):
                text = text.replace(prefix, "").strip()
            st.caption(f"  {text}")

        remaining = len(sr.details) - shown
        if remaining > 0:
            st.caption(f"  ... y {remaining} mas")

        # ── Action ──────────────────────────────────────────────
        if not is_manual and result.file_type == FileType.PBIP:
            st.markdown("")
            if st.button("Corregir", key=f"fix_{sr.fixer_id}"):
                _apply_fix(engine, sr, result, scan_key)


def _apply_fix(engine, sr, result, scan_key):
    if not is_cloud():
        with st.spinner("Creando backup..."):
            try:
                bk = engine.create_backup(result, fixer_ids=[sr.fixer_id])
                st.caption(f"Backup: `{bk.backup_path}`")
            except Exception as e:
                st.error(f"Error en backup: {e}")
                return

    with st.spinner("Aplicando..."):
        fr = engine.run_single(sr.fixer_id, result, FixMode.SCAN_AND_FIX)

    if not fr:
        st.error("Error aplicando fix")
        return

    val = fr.validation_result
    if val.get("passed", False):
        st.success(f"Corregido: {val.get('issues_resolved', 0)} problema(s). Validacion OK.")
    else:
        st.warning(
            f"Parcial: {fr.issues_fixed}/{fr.issues_found} corregidos. "
            f"{val.get('issues_remaining', '?')} restantes."
        )

    with st.spinner("Re-escaneando..."):
        new_scans = engine.scan_all(result)
        if not result.model_analysis_available:
            new_scans = [s for s in new_scans if s.category != "model"]
        st.session_state[scan_key] = new_scans

    if is_cloud():
        st.info("Use el boton 'Descargar' en el sidebar para obtener el proyecto corregido.")
    else:
        st.info("Recargue en Power BI Desktop para ver los cambios.")
    st.rerun()


def _render_restore_ui(engine, result):
    st.markdown("#### Restaurar Backup")
    backups = engine.list_backups(result.report_path)
    if not backups:
        st.info("No hay backups disponibles.")
        return

    for i, bk in enumerate(backups[:5]):
        with st.expander(f"{bk.created_at[:19]} — {bk.size_mb:.1f} MB", expanded=(i == 0)):
            st.caption(f"`{bk.backup_path}`")
            if bk.applied_fixers:
                st.caption(f"Fixers: {', '.join(bk.applied_fixers[:5])}")
            if st.button("Restaurar", key=f"restore_{i}"):
                target = result._report_base_path or result.report_path
                ok = engine.restore_backup(bk.backup_path, target)
                st.success("Restaurado.") if ok else st.error("Error.")


def _render_scan_only(result):
    engine = FixerEngine()
    if st.button("Escanear (solo lectura)", type="primary"):
        with st.spinner("Escaneando..."):
            scans = engine.scan_all(result)
        with_issues = [s for s in scans if s.issues_found > 0]
        total = sum(s.issues_found for s in with_issues)
        st.markdown(f"**{total} problemas** ({len(with_issues)} fixers, no corregibles en PBIX)")
        for sr in with_issues:
            exp = FIXER_EXPLANATIONS.get(sr.fixer_id, {})
            with st.expander(f"{sr.fixer_name} ({sr.issues_found})"):
                if exp.get("what"):
                    st.markdown(f"**Problema:** {exp['what']}")
                for d in sr.details[:10]:
                    st.caption(f"  {d}")
