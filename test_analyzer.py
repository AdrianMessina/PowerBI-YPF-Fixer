"""Test script para Power BI Analyzer 2.0 - Uso programático."""

from core import PowerBIAnalyzer, FixerEngine
from core.models import FixMode


def test_analysis(file_path: str):
    """Test básico de análisis."""
    print("=" * 60)
    print("Power BI Analyzer 2.0 - Test")
    print("=" * 60)
    print(f"\nAnalizando: {file_path}\n")

    # Crear analyzer
    analyzer = PowerBIAnalyzer()

    # Analizar
    result = analyzer.analyze(file_path)

    # Mostrar resultados
    print(f"Reporte: {result.report_name}")
    print(f"Tipo: {result.file_type.value}")
    print(f"Score: {result.overall_score}/100 ({result.score_category.value})")
    print(f"\nMétricas:")
    print(f"  - Páginas: {result.total_pages}")
    print(f"  - Visuals: {result.total_visuals}")
    print(f"  - Tablas: {result.total_tables}")
    print(f"  - Medidas: {result.total_measures}")
    print(f"  - Relaciones: {result.total_relationships}")
    print(f"  - Bidireccionales: {result.bidirectional_relationships}")
    print(f"  - Columnas calculadas: {result.calculated_columns}")

    print(f"\nRecomendaciones: {len(result.recommendations)}")
    for i, rec in enumerate(result.recommendations[:5], 1):
        print(f"  {i}. [{rec.severity.value}] {rec.message}")
    if len(result.recommendations) > 5:
        print(f"  ... y {len(result.recommendations) - 5} más")

    # Test fixers (solo PBIP)
    if result.file_type.value == "pbip":
        print(f"\n{'=' * 60}")
        print("Test de Fixers (SCAN mode)")
        print("=" * 60)

        engine = FixerEngine()
        scan_results = engine.scan_all(result)

        total_issues = sum(r.issues_found for r in scan_results)
        with_issues = [r for r in scan_results if r.issues_found > 0]

        print(f"\nFixers disponibles: {len(scan_results)}")
        print(f"Con problemas: {len(with_issues)}")
        print(f"Total issues: {total_issues}")

        if with_issues:
            print(f"\nDetalle de problemas:")
            for sr in with_issues[:5]:
                print(f"\n  [{sr.category}] {sr.fixer_name}")
                print(f"  Issues: {sr.issues_found}")
                for detail in sr.details[:3]:
                    print(f"    - {detail}")
                if len(sr.details) > 3:
                    print(f"    ... y {len(sr.details) - 3} más")

    print(f"\n{'=' * 60}")
    print("Test completado")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python test_analyzer.py <ruta_a_pbix_o_pbip>")
        print("\nEjemplos:")
        print('  python test_analyzer.py "C:/MisReportes/Reporte.pbix"')
        print('  python test_analyzer.py "C:/MisReportes/Proyecto.Report"')
        sys.exit(1)

    file_path = sys.argv[1]
    test_analysis(file_path)
