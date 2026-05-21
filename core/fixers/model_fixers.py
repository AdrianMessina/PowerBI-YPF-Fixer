"""Semantic model fixers - modify TMDL/BIM files."""

import os
import re
from core.fixers.base import BaseFixer


class FixBidirectionalRelationships(BaseFixer):
    """Convert bidirectional relationships to one-direction."""

    fixer_id = "fix_bidirectional"
    name = "Corregir relaciones bidireccionales"
    description = (
        "Convierte relaciones bidireccionales (crossFilteringBehavior: bothDirections) "
        "a unidireccionales. Las bidireccionales causan ambiguedad y bajo rendimiento."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True

    def scan(self):
        for rel in self.result.relationships_detail:
            if rel.is_bidirectional:
                self.issues.append(
                    f"{rel.from_table}.{rel.from_column} <-> {rel.to_table}.{rel.to_column}: bidireccional"
                )

    def fix(self):
        if not self.result.bidirectional_relationships:
            return

        model_def = self._get_model_definition_path()

        # Try TMDL format
        rel_file = os.path.join(model_def, "relationships.tmdl")
        if os.path.exists(rel_file):
            self._fix_tmdl_relationships(rel_file)
            return

        # Try BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if os.path.exists(bim_path):
                self._fix_bim_relationships(bim_path)
                return

    def _fix_tmdl_relationships(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        content = content.replace(
            "crossFilteringBehavior: bothDirections",
            "crossFilteringBehavior: oneDirection"
        )

        if content != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            count = original.count("crossFilteringBehavior: bothDirections")
            self.fixes_applied.append(
                f"{count} relaciones cambiadas de bothDirections a oneDirection en {os.path.basename(path)}"
            )

    def _fix_bim_relationships(self, path: str):
        data = self._read_json_file(path)
        if not data:
            return

        model = data.get("model", data)
        count = 0
        for rel in model.get("relationships", []):
            if rel.get("crossFilteringBehavior", "").lower() == "bothdirections":
                rel["crossFilteringBehavior"] = "oneDirection"
                count += 1

        if count:
            self._write_json_file(path, data)
            self.fixes_applied.append(
                f"{count} relaciones cambiadas de bothDirections a oneDirection en {os.path.basename(path)}"
            )


class FixCalculatedColumnsToMeasures(BaseFixer):
    """Detect calculated columns that could be measures instead."""

    fixer_id = "fix_calculated_columns"
    name = "Detectar columnas calculadas convertibles a medidas"
    description = (
        "Detecta columnas calculadas que podrían ser medidas DAX. "
        "Las medidas se calculan en tiempo de consulta y no ocupan espacio en el modelo. "
        "NOTA: Este fix solo reporta, no convierte automáticamente (requiere revisión manual)."
    )
    category = "model"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    # Patterns that suggest the column could be a measure
    MEASURE_PATTERNS = [
        r"CALCULATE\s*\(", r"SUMX\s*\(", r"AVERAGEX\s*\(",
        r"COUNTROWS\s*\(", r"SUM\s*\(", r"AVERAGE\s*\(",
        r"COUNT\s*\(", r"MIN\s*\(", r"MAX\s*\(",
    ]

    def scan(self):
        for col in self.result.columns_detail:
            if not col.is_calculated:
                continue
            if not col.expression:
                continue
            # Check if expression looks like an aggregation (measure candidate)
            expr_upper = col.expression.upper()
            for pattern in self.MEASURE_PATTERNS:
                if re.search(pattern, expr_upper):
                    self.issues.append(
                        f"[{col.table}] Columna calculada '{col.name}' usa {pattern.split('(')[0].strip(chr(92))}"
                        f" y podría ser una medida"
                    )
                    break

    def fix(self):
        # This fixer only reports, doesn't auto-convert
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")
