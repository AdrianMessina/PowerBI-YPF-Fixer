"""Power BI Fixer — Main Application (Local + Cloud dual mode)"""

import os
import sys
import shutil
import tempfile
import zipfile
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from core import PowerBIAnalyzer
from core.environment import is_cloud, get_current_user
from core.usage_logger import UsageLogger
from ui.styles import MAIN_CSS
from ui.components import render_header, render_summary_metrics, render_feature_card
from ui.tab_overview import render_overview_tab
from ui.tab_metrics import render_metrics_tab
from ui.tab_recommendations import render_recommendations_tab
from ui.tab_fixer import render_fixer_tab
from ui.tab_export import render_export_tab
from ui.tab_memory import render_memory_tab
from ui.tab_tools import render_tools_tab
from ui.tab_usage import render_usage_tab


# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Power BI Fixer",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%23FDB913'/><text x='16' y='22' text-anchor='middle' font-size='18' fill='%23000'>F</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(MAIN_CSS, unsafe_allow_html=True)

CLOUD_MODE = is_cloud()


def _clean_path(raw_path: str) -> str:
    if not raw_path:
        return ""
    path = raw_path.strip().strip('"').strip("'").strip()
    path = path.replace("\\", "/").rstrip("/")
    return path


def _get_logger() -> UsageLogger:
    if "logger" not in st.session_state:
        st.session_state.logger = UsageLogger("PBI_Fixer", "2.0")
    return st.session_state.logger


def _extract_zip(uploaded_file) -> str:
    """Extract uploaded ZIP to temp directory. Returns extracted path."""
    temp_dir = tempfile.mkdtemp(prefix="pbi_fixer_")
    with zipfile.ZipFile(uploaded_file, "r") as zf:
        zf.extractall(temp_dir)
    return temp_dir


def _create_download_zip(base_path: str) -> bytes:
    """Create a ZIP from a directory for download — delegates to the
    Auto-Fix tab builder so the same exclusion filter applies (skips .bak*,
    __pycache__, OS metadata, etc.)."""
    from ui.tab_fixer import _build_project_zip
    return _build_project_zip(base_path)


# ── Sidebar ──────────────────────────────────────────────────────────

def _render_sidebar():
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1.5rem 0 0.75rem 0;">
        <img src="data:image/png;base64,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"
             alt="YPF" style="width: 44px; height: 44px; border-radius: 10px; margin-bottom: 0.75rem; opacity: 0.9;">
        <h1 style="font-size: 1.2rem; font-weight: 700; margin: 0; color: #E8ECF4; letter-spacing: -0.04em; font-family: 'Space Grotesk', sans-serif;">
            Power BI <span style="color: #F2C811;">Fixer</span>
        </h1>
        <p style="font-size: 0.68rem; margin-top: 0.4rem; color: #5A6478; text-transform: uppercase; letter-spacing: 0.1em;">
            YPF Data Analytics
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.divider()


# ── Main App ─────────────────────────────────────────────────────────

def main():
    logger = _get_logger()
    render_header()
    _render_sidebar()

    # Session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "analyzer" not in st.session_state:
        st.session_state.analyzer = PowerBIAnalyzer()
    if "extracted_path" not in st.session_state:
        st.session_state.extracted_path = None

    result = st.session_state.analysis_result

    # ── Results view ────────────────────────────────────────────────
    if result is not None:
        render_summary_metrics(result)

        col_new, col_dl = st.sidebar.columns(2) if CLOUD_MODE else (st.sidebar, None)

        if CLOUD_MODE:
            with col_new:
                new_btn = st.button("Nuevo", use_container_width=True)
            with col_dl:
                # Download corrected ZIP
                ext_path = st.session_state.get("extracted_path")
                if ext_path and os.path.isdir(ext_path):
                    zip_bytes = _create_download_zip(ext_path)
                    st.download_button(
                        "Descargar",
                        data=zip_bytes,
                        file_name=f"{result.report_name}_fixed.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )
        else:
            new_btn = st.sidebar.button("Nuevo Analisis", use_container_width=True)

        if new_btn:
            # Cleanup temp dir in cloud
            ext_path = st.session_state.get("extracted_path")
            if ext_path and os.path.isdir(ext_path):
                shutil.rmtree(ext_path, ignore_errors=True)
            st.session_state.analysis_result = None
            st.session_state.extracted_path = None
            logger.log_event("new_analysis_requested", {})
            st.rerun()

        tabs = st.tabs([
            "Overview", "Metricas", "Recomendaciones",
            "Auto-Fix", "Memoria", "Herramientas", "Exportar", "Uso",
        ])

        with tabs[0]: render_overview_tab(result)
        with tabs[1]: render_metrics_tab(result)
        with tabs[2]: render_recommendations_tab(result)
        with tabs[3]: render_fixer_tab(result)
        with tabs[4]: render_memory_tab(result)
        with tabs[5]: render_tools_tab(result)
        with tabs[6]: render_export_tab(result)
        with tabs[7]: render_usage_tab()
        return

    # ── Input view ──────────────────────────────────────────────────
    if CLOUD_MODE:
        _render_cloud_input(logger)
    else:
        _render_local_input(logger)

    # Features
    st.markdown("")
    st.divider()
    st.markdown("#### Capacidades")

    col1, col2 = st.columns(2)
    with col1:
        render_feature_card("A", "Analisis de Best Practices",
            "Detecta 60+ problemas comunes en reportes y modelos basandose en las mejores practicas de Microsoft")
        render_feature_card("S", "Scoring Inteligente",
            "Calcula un score de 0-100 basado en metricas ponderadas con thresholds configurables")
    with col2:
        render_feature_card("F", "Auto-Fix Engine",
            "Corrige automaticamente problemas sin necesidad de abrir Power BI Desktop. 33 fixers disponibles")
        render_feature_card("E", "Reportes Detallados",
            "Exporta analisis completos en HTML y JSON para compartir con el equipo")

    st.markdown("")
    st.caption("Formatos soportados: **PBIP/PBIR** (analisis completo + auto-fix) | **PBIX** (analisis limitado)")


# ── Input Modes ──────────────────────────────────────────────────────

def _render_local_input(logger):
    """Local mode: text input with path."""
    input_col, btn_col = st.columns([4, 1])

    with input_col:
        raw_path = st.text_input(
            "Ruta al proyecto PBIP",
            placeholder="C:/Users/tu_usuario/MiReporte.Report",
            help="Ruta a carpeta .Report, archivo .pbip, o .pbix. Acepta comillas.",
            label_visibility="collapsed",
        )
    file_path = _clean_path(raw_path)

    with btn_col:
        analyze = st.button("Analizar", type="primary",
                            use_container_width=True, disabled=not file_path)

    if analyze and file_path:
        resolved = PowerBIAnalyzer.resolve_path(file_path)
        if not os.path.exists(resolved):
            st.error(f"No se encontro: `{file_path}`")
        else:
            if resolved != file_path:
                st.info(f"Ruta detectada: `{resolved}`")
            _run_analysis(resolved, logger)


def _render_cloud_input(logger):
    """Cloud mode: ZIP file uploader."""
    st.caption(
        "Suba un archivo ZIP con su proyecto Power BI "
        "(carpeta .Report y opcionalmente .SemanticModel)."
    )

    uploaded = st.file_uploader(
        "Subir proyecto PBIP (ZIP)",
        type=["zip"],
        help="ZIP conteniendo la carpeta .Report (y .SemanticModel si tiene modelo).",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        with st.spinner("Extrayendo proyecto..."):
            try:
                temp_dir = _extract_zip(uploaded)
                resolved = PowerBIAnalyzer.resolve_path(temp_dir)
                st.session_state.extracted_path = temp_dir
                _run_analysis(resolved, logger)
            except zipfile.BadZipFile:
                st.error("El archivo no es un ZIP valido.")
            except Exception as e:
                st.error(f"Error extrayendo: {str(e)}")


def _run_analysis(path: str, logger: UsageLogger):
    """Run analysis on resolved path (shared between local and cloud)."""
    with st.spinner("Analizando reporte..."):
        try:
            result = st.session_state.analyzer.analyze(path)
            st.session_state.analysis_result = result

            logger.log_event("analysis_completed", {
                "report_name": result.report_name,
                "path": path,
                "score": result.overall_score,
                "pages": result.total_pages,
                "visuals": result.total_visuals,
                "tables": result.total_tables,
                "measures": result.total_measures,
                "recommendations": len(result.recommendations),
                "user": get_current_user(),
                "mode": "cloud" if CLOUD_MODE else "local",
            })
            st.rerun()
        except Exception as e:
            logger.log_event("analysis_error", {"path": path, "error": str(e)})
            st.error(f"Error: {str(e)}")
            import traceback
            with st.expander("Detalles del error"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
