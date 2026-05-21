"""Best Practice Analyzer v2 - additional DAX and model quality rules."""

import os
import re
from collections import defaultdict
from core.fixers.base import BaseFixer


class FixMeasureFolders(BaseFixer):
    """Organize measures into display folders by table."""

    fixer_id = "fix_measure_folders"
    name = "Organizar medidas en carpetas"
    description = (
        "Detecta medidas sin displayFolder asignado. Las carpetas organizan "
        "las medidas en el panel de campos, mejorando la usabilidad."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            for measure in table.get("measures", []):
                if not measure.get("displayFolder"):
                    self.issues.append(
                        f"[{tname}] Medida '{measure.get('name', '')}': sin displayFolder"
                    )

        # TMDL check
        if not self.issues:
            for _, content, tname in self._iter_tmdl_table_files():
                blocks = re.split(r"(?=^\tmeasure\s+')", content, flags=re.MULTILINE)
                for block in blocks:
                    mm = re.match(r"^\tmeasure\s+'([^']+)'", block)
                    if mm and "displayFolder" not in block:
                        self.issues.append(
                            f"[{tname}] Medida '{mm.group(1)}': sin displayFolder"
                        )

    def fix(self):
        model_def = self._get_model_definition_path()

        # BIM format
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)
            changed = False
            for table in model.get("tables", []):
                tname = table.get("name", "")
                for measure in table.get("measures", []):
                    if not measure.get("displayFolder"):
                        measure["displayFolder"] = "Measures"
                        changed = True
                        self.fixes_applied.append(
                            f"[{tname}] '{measure.get('name', '')}' -> displayFolder: 'Measures'"
                        )
            if changed:
                self._write_json_file(bim_path, data)
                return

        # TMDL format
        for fpath, content, tname in self._iter_tmdl_table_files():
            original = content
            blocks = re.split(r"(?=^\tmeasure\s+')", content, flags=re.MULTILINE)
            new_blocks = []
            for block in blocks:
                mm = re.match(r"^\tmeasure\s+'([^']+)'", block)
                if mm and "displayFolder" not in block:
                    mname = mm.group(1)
                    lines = block.split("\n")
                    new_lines = [lines[0]]
                    inserted = False
                    for line in lines[1:]:
                        if not inserted and line.startswith("\t\t"):
                            new_lines.append("\t\tdisplayFolder: Measures")
                            inserted = True
                        new_lines.append(line)
                    if not inserted:
                        new_lines.insert(1, "\t\tdisplayFolder: Measures")
                    block = "\n".join(new_lines)
                    self.fixes_applied.append(
                        f"[{tname}] '{mname}' -> displayFolder: 'Measures'"
                    )
                new_blocks.append(block)

            new_content = "".join(new_blocks)
            if new_content != original:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)


class FixColumnFolders(BaseFixer):
    """Organize columns into display folders."""

    fixer_id = "fix_column_folders"
    name = "Organizar columnas en carpetas"
    description = (
        "Detecta tablas con muchas columnas (>10) sin displayFolder. "
        "Organizar en carpetas mejora la navegación del modelo."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "threshold"

    MIN_COLUMNS = 10

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            cols = table.get("columns", [])
            if len(cols) <= self.MIN_COLUMNS:
                continue
            no_folder = [c for c in cols if not c.get("displayFolder")]
            if len(no_folder) > self.MIN_COLUMNS:
                self.issues.append(
                    f"[{tname}] {len(no_folder)}/{len(cols)} columnas sin displayFolder "
                    f"(tabla con muchas columnas)"
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixUnreferencedMeasures(BaseFixer):
    """Detect measures not referenced by any other measure or visual."""

    fixer_id = "fix_unreferenced_measures"
    name = "Detectar medidas sin referencias"
    description = (
        "Detecta medidas que no son referenciadas por otras medidas DAX. "
        "Pueden ser medidas huérfanas que se pueden eliminar."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = False
    is_manual = True
    detection_method = "heuristic"

    def scan(self):
        if not self.result.measures_detail:
            return

        # Build a set of all measure names
        all_measures = {m.name for m in self.result.measures_detail}
        # Build a concatenation of all expressions
        all_expressions = " ".join(
            m.expression for m in self.result.measures_detail if m.expression
        )

        for m in self.result.measures_detail:
            # Check if this measure is referenced in any other expression
            # Use [MeasureName] pattern (DAX convention)
            ref_pattern = f"[{m.name}]"
            # Count references (excluding self-reference in its own expression)
            other_expressions = " ".join(
                other.expression for other in self.result.measures_detail
                if other.name != m.name and other.expression
            )
            if ref_pattern not in other_expressions:
                # Could still be used in visuals, so mark as info only
                self.issues.append(
                    f"[{m.table}] Medida '{m.name}': no referenciada por otras medidas"
                )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"REVISION: {issue}")


class FixExpensiveDAXPatterns(BaseFixer):
    """Detect expensive DAX patterns that hurt performance."""

    fixer_id = "fix_expensive_dax"
    name = "Detectar patrones DAX costosos"
    description = (
        "Detecta patrones DAX conocidos por ser costosos: "
        "FILTER sobre tabla completa, COUNTROWS+FILTER vs CALCULATE, "
        "SUMX sobre tablas grandes, IF+HASONEVALUE vs SWITCH, etc."
    )
    category = "bpa"
    severity = "warning"
    requires_pbip = False
    is_manual = True
    detection_method = "pattern_match"

    EXPENSIVE_PATTERNS = [
        {
            "pattern": r"FILTER\s*\(\s*'?[A-Za-z]",
            "exclude": r"FILTER\s*\(\s*(ALL|VALUES|DISTINCT|SUMMARIZE)",
            "message": "FILTER() sobre tabla completa: use CALCULATE() con filtros directos",
            "id": "FILTER_TABLE",
        },
        {
            "pattern": r"COUNTROWS\s*\(\s*FILTER\s*\(",
            "exclude": None,
            "message": "COUNTROWS(FILTER(...)): reemplace con CALCULATE(COUNTROWS(...), ...)",
            "id": "COUNTROWS_FILTER",
        },
        {
            "pattern": r"IF\s*\(\s*HASONEVALUE\s*\(",
            "exclude": None,
            "message": "IF(HASONEVALUE(...)): considere SELECTEDVALUE() o SWITCH()",
            "id": "IF_HASONEVALUE",
        },
        {
            "pattern": r"SUMX\s*\(\s*FILTER\s*\(",
            "exclude": None,
            "message": "SUMX(FILTER(...)): puede ser costoso. Considere CALCULATE(SUM(...), ...)",
            "id": "SUMX_FILTER",
        },
        {
            "pattern": r"EARLIER\s*\(",
            "exclude": None,
            "message": "EARLIER(): patrón obsoleto, use VAR para mayor claridad y rendimiento",
            "id": "EARLIER",
        },
        {
            "pattern": r"VALUES\s*\(\s*'?[A-Za-z][^)]*\)\s*\)",
            "exclude": None,
            "message": "Contexto: revise si VALUES() necesita ser reemplazado por DISTINCT()",
            "id": "VALUES_CHECK",
        },
    ]

    def scan(self):
        for m in self.result.measures_detail:
            if not m.expression:
                continue
            expr = m.expression
            for rule in self.EXPENSIVE_PATTERNS:
                if re.search(rule["pattern"], expr, re.IGNORECASE):
                    if rule["exclude"] and re.search(rule["exclude"], expr, re.IGNORECASE):
                        continue
                    self.issues.append(
                        f"[{m.table}] Medida '{m.name}': {rule['message']}"
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixMissingRelationships(BaseFixer):
    """Detect potential missing relationships based on column name matching."""

    fixer_id = "fix_missing_relationships"
    name = "Detectar relaciones faltantes"
    description = (
        "Detecta columnas con nombres similares en diferentes tablas que podrían "
        "necesitar una relación (e.g., ProductID en Fact y Dim tables)."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = False
    is_manual = True
    detection_method = "heuristic"

    FK_SUFFIXES = {"id", "key", "code", "fk", "sk"}

    def scan(self):
        # Build map of existing relationships
        existing_rels = set()
        for rel in self.result.relationships_detail:
            existing_rels.add((rel.from_table, rel.from_column))
            existing_rels.add((rel.to_table, rel.to_column))

        # Build map of columns by normalized name
        col_map = defaultdict(list)
        for col in self.result.columns_detail:
            name_lower = col.name.lower().replace(" ", "").replace("_", "")
            # Only consider potential key columns
            if any(name_lower.endswith(s) for s in self.FK_SUFFIXES):
                col_map[name_lower].append((col.table, col.name))

        # Find columns with same name in different tables without a relationship
        for norm_name, locations in col_map.items():
            if len(locations) < 2:
                continue
            for i, (table_a, col_a) in enumerate(locations):
                for table_b, col_b in locations[i + 1:]:
                    if table_a == table_b:
                        continue
                    # Check if relationship already exists
                    if ((table_a, col_a) in existing_rels or
                            (table_b, col_b) in existing_rels):
                        continue
                    self.issues.append(
                        f"'{table_a}'.{col_a} y '{table_b}'.{col_b} "
                        f"comparten nombre pero no tienen relación"
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"REVISION: {issue}")


class FixSortByColumn(BaseFixer):
    """Detect text columns that likely need SortByColumn (e.g., month names)."""

    fixer_id = "fix_sort_by_column"
    name = "Detectar columnas sin SortByColumn"
    description = (
        "Detecta columnas de texto que probablemente necesitan SortByColumn "
        "(e.g., nombres de meses, días de la semana) para ordenar correctamente."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    SORTABLE_PATTERNS = {
        "month": "month number",
        "mes": "numero de mes",
        "day": "day number",
        "dia": "numero de dia",
        "weekday": "day of week number",
        "quarter": "quarter number",
        "trimestre": "numero trimestre",
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            columns = table.get("columns", [])
            col_names = {c.get("name", "").lower() for c in columns}

            for col in columns:
                cname = col.get("name", "")
                dtype = col.get("dataType", "").lower()
                if dtype != "string":
                    continue
                if col.get("sortByColumn"):
                    continue

                cname_lower = cname.lower().replace("_", " ")
                for pattern, _hint in self.SORTABLE_PATTERNS.items():
                    if pattern in cname_lower and "number" not in cname_lower and "num" not in cname_lower:
                        self.issues.append(
                            f"[{tname}] Columna '{cname}': texto que podría necesitar SortByColumn"
                        )
                        break

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"SUGERENCIA: {issue}")


class FixDataCategoryGeo(BaseFixer):
    """Detect columns that should have geographic DataCategory."""

    fixer_id = "fix_data_category_geo"
    name = "Asignar categorías geográficas"
    description = (
        "Detecta columnas que por su nombre podrían ser geográficas "
        "(ciudad, país, latitud, etc.) y necesitan DataCategory para mapas."
    )
    category = "bpa"
    severity = "info"
    requires_pbip = True

    GEO_MAP = {
        "country": "Country", "pais": "Country", "país": "Country",
        "city": "City", "ciudad": "City",
        "state": "StateOrProvince", "estado": "StateOrProvince",
        "provincia": "StateOrProvince", "province": "StateOrProvince",
        "postal": "PostalCode", "zip": "PostalCode",
        "latitude": "Latitude", "latitud": "Latitude", "lat": "Latitude",
        "longitude": "Longitude", "longitud": "Longitude", "lng": "Longitude", "lon": "Longitude",
        "address": "Address", "direccion": "Address", "dirección": "Address",
        "continent": "Continent", "continente": "Continent",
        "region": "StateOrProvince",
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            for col in table.get("columns", []):
                if col.get("dataCategory"):
                    continue
                cname = col.get("name", "")
                cname_lower = cname.lower().replace("_", " ").replace("-", " ")
                words = cname_lower.split()
                for word in words:
                    if word in self.GEO_MAP:
                        self.issues.append(
                            f"[{tname}] Columna '{cname}': podría necesitar "
                            f"DataCategory='{self.GEO_MAP[word]}' para mapas"
                        )
                        break

    def fix(self):
        model_def = self._get_model_definition_path()

        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(self.result._model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue

            data = self._read_json_file(bim_path)
            if not data:
                continue
            model = data.get("model", data)
            changed = False
            for table in model.get("tables", []):
                tname = table.get("name", "")
                for col in table.get("columns", []):
                    if col.get("dataCategory"):
                        continue
                    cname = col.get("name", "")
                    cname_lower = cname.lower().replace("_", " ").replace("-", " ")
                    words = cname_lower.split()
                    for word in words:
                        if word in self.GEO_MAP:
                            col["dataCategory"] = self.GEO_MAP[word]
                            changed = True
                            self.fixes_applied.append(
                                f"[{tname}] '{cname}' -> DataCategory: '{self.GEO_MAP[word]}'"
                            )
                            break
            if changed:
                self._write_json_file(bim_path, data)
                return

        # Fallback: report suggestions
        if not self.fixes_applied:
            self.scan()
            for issue in self.issues:
                self.fixes_applied.append(f"SUGERENCIA: {issue}")
