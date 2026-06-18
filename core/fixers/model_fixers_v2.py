"""Semantic model fixers v2 - calendar tables, calculation groups, and more."""

import os
import re
from core.fixers.base import BaseFixer


class FixInactiveRelationships(BaseFixer):
    """Detect inactive relationships that may be unnecessary."""

    fixer_id = "fix_inactive_relationships"
    name = "Detectar relaciones inactivas"
    description = (
        "Detecta relaciones marcadas como inactivas. Las relaciones inactivas "
        "solo se usan con USERELATIONSHIP() en DAX. Si no se usan, deben eliminarse."
    )
    category = "model"
    severity = "info"
    requires_pbip = True
    is_manual = True
    detection_method = "heuristic"

    def scan(self):
        # Find inactive relationships
        inactive_rels = []
        for rel in self.result.relationships_detail:
            if not rel.is_active:
                inactive_rels.append(rel)

        if not inactive_rels:
            return

        # Check if USERELATIONSHIP references exist in measures
        all_expressions = " ".join(
            m.expression.upper() for m in self.result.measures_detail if m.expression
        )

        for rel in inactive_rels:
            ref_from = f"'{rel.from_table}'[{rel.from_column}]".upper()
            ref_to = f"'{rel.to_table}'[{rel.to_column}]".upper()
            # Simplified check: see if USERELATIONSHIP is used at all with these columns
            if "USERELATIONSHIP" in all_expressions:
                if ref_from in all_expressions or ref_to in all_expressions:
                    continue  # Likely referenced
            self.issues.append(
                f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}: "
                f"relación inactiva sin referencia USERELATIONSHIP() detectada"
            )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixAutoDateTime(BaseFixer):
    """Detect and recommend disabling Auto Date/Time tables."""

    fixer_id = "fix_auto_datetime"
    name = "Deshabilitar Auto Date/Time"
    description = (
        "Detecta tablas Auto Date/Time generadas automáticamente por Power BI. "
        "Estas tablas ocultas aumentan el tamaño del modelo y deben reemplazarse "
        "por una tabla de calendario explícita."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True
    is_manual = True
    detection_method = "pattern_match"

    AUTO_DT_PREFIXES = ("LocalDateTable_", "DateTableTemplate_")

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        # NO filtrar - este fixer NECESITA ver las tablas automáticas para detectarlas
        for table in model_data.get("tables", []):
            tname = table.get("name", "")
            if any(tname.startswith(p) for p in self.AUTO_DT_PREFIXES):
                self.issues.append(
                    f"Tabla Auto Date/Time: '{tname}'. "
                    f"Deshabilitá Auto Date/Time y usá una tabla de calendario."
                )

        # Also check TMDL files - include_system=True para ver las automáticas
        if not self.issues:
            for fpath, content, tname in self._iter_tmdl_table_files(include_system=True):
                if any(tname.startswith(p) for p in self.AUTO_DT_PREFIXES):
                    self.issues.append(
                        f"Tabla Auto Date/Time: '{tname}' en TMDL."
                    )

    def fix(self):
        self.scan()
        for issue in self.issues:
            self.fixes_applied.append(f"MANUAL: {issue}")


class FixCalendarTable(BaseFixer):
    """Generate a Calendar table if none exists."""

    fixer_id = "fix_calendar_table"
    name = "Generar tabla Calendario"
    description = (
        "Detecta si el modelo carece de una tabla de calendario/fecha explícita. "
        "Puede generar una tabla de calendario como calculated table en TMDL o BIM."
    )
    category = "model"
    severity = "warning"
    requires_pbip = True

    CALENDAR_INDICATORS = {
        "calendar", "calendario", "date", "fecha", "dim_date", "dim_fecha",
        "dim_calendar", "dim_calendario", "datetable", "dates",
    }

    CALENDAR_DAX = '''ADDCOLUMNS(
    CALENDAR(DATE(2020, 1, 1), DATE(2030, 12, 31)),
    "Year", YEAR([Date]),
    "Month Number", MONTH([Date]),
    "Month Name", FORMAT([Date], "MMMM"),
    "Month Short", FORMAT([Date], "MMM"),
    "Quarter", "Q" & FORMAT([Date], "Q"),
    "Year-Month", FORMAT([Date], "YYYY-MM"),
    "Day of Week", WEEKDAY([Date], 2),
    "Day Name", FORMAT([Date], "DDDD"),
    "Week Number", WEEKNUM([Date], 2),
    "Is Weekend", IF(WEEKDAY([Date], 2) >= 6, TRUE(), FALSE()),
    "Year-Quarter", FORMAT([Date], "YYYY") & "-Q" & FORMAT([Date], "Q")
)'''

    CALENDAR_TMDL = '''table Calendar
\tlineageTag: {cal-lineage-tag}

\tcolumn Date
\t\tdataType: dateTime
\t\tformatString: Short Date
\t\tlineageTag: {date-lineage-tag}
\t\tdataCategory: Date
\t\tisKey
\t\tsummarizeBy: none
\t\tsourceColumn: [Date]

\tcolumn Year
\t\tdataType: int64
\t\tlineageTag: {year-lineage-tag}
\t\tsummarizeBy: none
\t\tsourceColumn: [Year]

\tcolumn 'Month Number'
\t\tdataType: int64
\t\tlineageTag: {monthnum-lineage-tag}
\t\tsummarizeBy: none
\t\tsourceColumn: [Month Number]

\tcolumn 'Month Name'
\t\tdataType: string
\t\tlineageTag: {monthname-lineage-tag}
\t\tsortByColumn: 'Month Number'
\t\tsourceColumn: [Month Name]

\tcolumn Quarter
\t\tdataType: string
\t\tlineageTag: {quarter-lineage-tag}
\t\tsourceColumn: [Quarter]

\tcolumn 'Year-Month'
\t\tdataType: string
\t\tlineageTag: {yearmonth-lineage-tag}
\t\tsourceColumn: [Year-Month]

\tpartition Calendar = calculated
\t\tmode: import
\t\tsource = ''' + CALENDAR_DAX

    def scan(self):
        has_calendar = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            # IGNORAR tablas automáticas de Power BI (Auto Date/Time)
            # NO son calendarios "reales" del usuario
            if table.get("isSystemTable", False):
                continue
            tname_raw = table.get("name", "")
            if tname_raw.startswith("LocalDateTable_") or tname_raw.startswith("DateTableTemplate_"):
                continue

            tname = tname_raw.lower().replace(" ", "").replace("_", "")
            if tname in self.CALENDAR_INDICATORS:
                has_calendar = True
                break
            # Check if any column has DataCategory = Date
            for col in table.get("columns", []):
                if col.get("dataCategory", "").lower() == "date":
                    has_calendar = True
                    break
            if has_calendar:
                break

        # Also check TMDL
        if not has_calendar:
            for _, content, tname in self._iter_tmdl_table_files():
                # IGNORAR tablas automáticas
                if tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_"):
                    continue
                if "__PBI_TemplateDateTable" in content:
                    continue

                tname_clean = tname.lower().replace(" ", "").replace("_", "")
                if tname_clean in self.CALENDAR_INDICATORS:
                    has_calendar = True
                    break
                if "dataCategory: Date" in content:
                    has_calendar = True
                    break

        if not has_calendar:
            self.issues.append(
                "No se detectó tabla de calendario en el modelo. "
                "Se recomienda crear una para Time Intelligence."
            )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        # Try TMDL format first
        if os.path.isdir(tables_dir):
            cal_path = os.path.join(tables_dir, "Calendar.tmdl")
            if not os.path.exists(cal_path):
                content = self.CALENDAR_TMDL
                # Generate unique lineage tags
                for tag in ["{cal-lineage-tag}", "{date-lineage-tag}",
                            "{year-lineage-tag}", "{monthnum-lineage-tag}",
                            "{monthname-lineage-tag}", "{quarter-lineage-tag}",
                            "{yearmonth-lineage-tag}"]:
                    content = content.replace(tag, str(uuid.uuid4()))
                with open(cal_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied.append(
                    "Tabla 'Calendar' creada en TMDL con DAX calculated table"
                )
                return

        # Try BIM format
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
            tables = model.get("tables", [])

            cal_table = {
                "name": "Calendar",
                "columns": [
                    {"name": "Date", "dataType": "dateTime",
                     "sourceColumn": "[Date]", "formatString": "Short Date",
                     "dataCategory": "Date", "isKey": True, "summarizeBy": "none"},
                    {"name": "Year", "dataType": "int64",
                     "sourceColumn": "[Year]", "summarizeBy": "none"},
                    {"name": "Month Number", "dataType": "int64",
                     "sourceColumn": "[Month Number]", "summarizeBy": "none"},
                    {"name": "Month Name", "dataType": "string",
                     "sourceColumn": "[Month Name]", "sortByColumn": "Month Number"},
                    {"name": "Quarter", "dataType": "string",
                     "sourceColumn": "[Quarter]"},
                    {"name": "Year-Month", "dataType": "string",
                     "sourceColumn": "[Year-Month]"},
                ],
                "partitions": [{
                    "name": "Calendar",
                    "mode": "import",
                    "source": {
                        "type": "calculated",
                        "expression": self.CALENDAR_DAX.split("\n"),
                    },
                }],
                "isCalculatedTable": True,
            }
            tables.append(cal_table)
            self._write_json_file(bim_path, data)
            self.fixes_applied.append(
                "Tabla 'Calendar' creada en BIM con DAX calculated table"
            )
            return


class FixMeasureTable(BaseFixer):
    """Create an empty '_Measures' table with a Last Refresh timestamp measure."""

    fixer_id = "fix_measure_table"
    name = "Crear tabla de medidas"
    description = (
        "Crea una tabla '_Measures' dedicada para organizar medidas DAX. "
        "Incluye una medida 'Last Refresh' con timestamp del último refresh."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    MEASURE_TABLE_NAMES = {
        "_measures", "measures", "_medidas", "medidas",
        "_kpis", "kpis", "_calc", "calculations",
    }

    TMDL_CONTENT = '''table _Measures
\tlineageTag: {table-tag}

\t/// Fecha y hora del ultimo refresh del modelo
\tmeasure 'Last Refresh' = NOW()
\t\tformatString: dd/MM/yyyy HH:mm:ss
\t\tlineageTag: {measure-tag}

\tcolumn Value
\t\tdataType: int64
\t\tlineageTag: {col-tag}
\t\tisHidden
\t\tsummarizeBy: none
\t\tsourceColumn: [Value]

\tpartition _Measures = calculated
\t\tmode: import
\t\tsource = ROW("Value", 0)
'''

    def scan(self):
        has_measure_table = False
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in model_data.get("tables", []):
            # IGNORAR tablas automáticas (no son tablas de medidas reales)
            if table.get("isSystemTable", False):
                continue
            tname_raw = table.get("name", "")
            if tname_raw.startswith("LocalDateTable_") or tname_raw.startswith("DateTableTemplate_"):
                continue

            tname = tname_raw.lower().replace(" ", "")
            if tname in self.MEASURE_TABLE_NAMES:
                has_measure_table = True
                break

        if not has_measure_table:
            for _, _, tname in self._iter_tmdl_table_files():
                if tname.startswith("LocalDateTable_") or tname.startswith("DateTableTemplate_"):
                    continue
                if tname.lower().replace(" ", "") in self.MEASURE_TABLE_NAMES:
                    has_measure_table = True
                    break

        if not has_measure_table and self.result.total_measures > 0:
            self.issues.append(
                "No se detectó tabla dedicada de medidas. "
                "Se recomienda '_Measures' para organizar KPIs y agregar Last Refresh."
            )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "_Measures.tmdl")
            if not os.path.exists(path):
                content = self.TMDL_CONTENT
                for tag in ["{table-tag}", "{measure-tag}", "{col-tag}"]:
                    content = content.replace(tag, str(uuid.uuid4()))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied.append(
                    "Tabla '_Measures' creada con medida 'Last Refresh'"
                )
                return

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
            tables = model.get("tables", [])
            tables.append({
                "name": "_Measures",
                "columns": [{
                    "name": "Value", "dataType": "int64",
                    "isHidden": True, "summarizeBy": "none",
                    "sourceColumn": "[Value]",
                }],
                "measures": [{
                    "name": "Last Refresh",
                    "expression": "NOW()",
                    "formatString": "dd/MM/yyyy HH:mm:ss",
                    "description": "Fecha y hora del ultimo refresh del modelo",
                }],
                "partitions": [{
                    "name": "_Measures",
                    "mode": "import",
                    "source": {"type": "calculated", "expression": ['ROW("Value", 0)']},
                }],
                "isCalculatedTable": True,
            })
            self._write_json_file(bim_path, data)
            self.fixes_applied.append(
                "Tabla '_Measures' creada con medida 'Last Refresh'"
            )
            return


class FixTimeIntelligenceGroup(BaseFixer):
    """Create a Time Intelligence calculation group."""

    fixer_id = "fix_time_intelligence"
    name = "Crear Calculation Group: Time Intelligence"
    description = (
        "Crea un Calculation Group de Time Intelligence con items: "
        "YTD, QTD, MTD, PY (año anterior), PY YTD, YoY, YoY%. "
        "Requiere tabla de calendario con columna Date marcada."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    CALC_ITEMS = {
        "Current": "SELECTEDMEASURE()",
        "YTD": "CALCULATE(SELECTEDMEASURE(), DATESYTD('Calendar'[Date]))",
        "QTD": "CALCULATE(SELECTEDMEASURE(), DATESQTD('Calendar'[Date]))",
        "MTD": "CALCULATE(SELECTEDMEASURE(), DATESMTD('Calendar'[Date]))",
        "PY": "CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))",
        "PY YTD": "CALCULATE(SELECTEDMEASURE(), DATESYTD(SAMEPERIODLASTYEAR('Calendar'[Date])))",
        "YoY": (
            "VAR _Current = SELECTEDMEASURE()\n"
            "VAR _PY = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))\n"
            "RETURN _Current - _PY"
        ),
        "YoY %": (
            "VAR _Current = SELECTEDMEASURE()\n"
            "VAR _PY = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Calendar'[Date]))\n"
            "RETURN DIVIDE(_Current - _PY, _PY)"
        ),
    }

    @staticmethod
    def _ensure_discourage_implicit_measures(model_def: str, model_base_path: str) -> bool:
        """Ensure the model has `discourageImplicitMeasures: true`.

        Power BI rejects any model that contains a calculation group unless
        this property is set to true. Must be called BEFORE writing a
        calc-group .tmdl file. Returns True if a change was made.

        Handles both TMDL (`definition/model.tmdl`) and BIM (`model.bim`).
        """
        import json as _json

        # TMDL: definition/model.tmdl
        tmdl_path = os.path.join(model_def, "model.tmdl")
        if os.path.exists(tmdl_path):
            try:
                with open(tmdl_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                return False
            # If already true, nothing to do
            if re.search(r"^\s*discourageImplicitMeasures:\s*true\b", content, re.MULTILINE):
                return False
            # If set to false, flip to true
            if re.search(r"^\s*discourageImplicitMeasures:\s*\w+", content, re.MULTILINE):
                new_content = re.sub(
                    r"^(\s*)discourageImplicitMeasures:\s*\w+",
                    r"\1discourageImplicitMeasures: true",
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                # Insert as a property of the `model` block. The model declaration
                # is `model <Name>` on the first non-empty non-comment line; its
                # properties are the indented lines immediately following.
                lines = content.split("\n")
                out = []
                inserted = False
                for i, ln in enumerate(lines):
                    out.append(ln)
                    if inserted:
                        continue
                    if re.match(r"^model\s+\S+", ln):
                        # Find first indented property line after this and
                        # insert before any of the model-level child blocks.
                        # Simplest: insert right after the model declaration.
                        out.append("\tdiscourageImplicitMeasures: true")
                        inserted = True
                if not inserted:
                    return False
                new_content = "\n".join(out)

            with open(tmdl_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        # BIM: model.bim / dataset.bim
        for bim_name in ("model.bim", "dataset.bim"):
            bim_path = os.path.join(model_def, bim_name)
            if not os.path.exists(bim_path):
                bim_path = os.path.join(model_base_path, bim_name)
            if not os.path.exists(bim_path):
                continue
            try:
                with open(bim_path, "r", encoding="utf-8") as f:
                    data = _json.load(f)
            except Exception:
                continue
            model = data.get("model", data)
            if model.get("discourageImplicitMeasures") is True:
                return False
            model["discourageImplicitMeasures"] = True
            with open(bim_path, "w", encoding="utf-8") as f:
                _json.dump(data, f, indent=2, ensure_ascii=False)
            return True

        return False

    # Heuristic to detect calc-group files generated by an OLDER buggy version
    # of this fixer (contained `lineageTag` inside calculationItem, which is
    # NOT valid TMDL and breaks Power BI Desktop on open).
    @staticmethod
    def _has_invalid_calcitem_lineagetag(content: str) -> bool:
        in_item = False
        for ln in content.split("\n"):
            stripped = ln.strip()
            if stripped.startswith("calculationItem "):
                in_item = True
                continue
            if in_item:
                if stripped.startswith("calculationItem ") or stripped.startswith("calculationGroup") \
                        or stripped.startswith("column ") or stripped.startswith("table "):
                    in_item = False
                    continue
                if stripped.startswith("lineageTag:"):
                    return True
        return False

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            if table.get("calculationGroup"):
                tname = table.get("name", "").lower()
                if any(kw in tname for kw in ("time", "periodo", "temporal", "intelligence")):
                    return  # Already exists with valid metadata

        # TMDL — only return early if the existing file is VALID
        for _, content, tname in self._iter_tmdl_table_files():
            if "calculationGroup" not in content:
                continue
            if not any(kw in tname.lower() for kw in ("time", "periodo", "temporal", "intelligence")):
                continue
            if self._has_invalid_calcitem_lineagetag(content):
                self.issues.append(
                    f"'{tname}' tiene lineageTag inválido en calculationItem — regenerar"
                )
                return
            return  # valid existing file, nothing to do

        self.issues.append(
            "No se detectó Calculation Group de Time Intelligence. "
            "Se puede crear con YTD, QTD, MTD, PY, YoY, YoY%."
        )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "Time Intelligence.tmdl")
            # If a broken version exists, overwrite it.
            broken = False
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = f.read()
                    broken = self._has_invalid_calcitem_lineagetag(existing)
                except Exception:
                    broken = False
                if not broken:
                    # File is valid, but still make sure the model has
                    # discourageImplicitMeasures: true (required for any calc
                    # group). Older runs may have skipped this.
                    if self._ensure_discourage_implicit_measures(
                        model_def, self.result._model_base_path
                    ):
                        self.fixes_applied.append(
                            "model.tmdl: discourageImplicitMeasures: true "
                            "(requerido para calculation groups)"
                        )
                    return

            # About to write the calc group — enforce the model flag first.
            if self._ensure_discourage_implicit_measures(
                model_def, self.result._model_base_path
            ):
                self.fixes_applied.append(
                    "model.tmdl: discourageImplicitMeasures: true "
                    "(requerido para calculation groups)"
                )

            lines = [f"table 'Time Intelligence'"]
            lines.append(f"\tlineageTag: {uuid.uuid4()}")
            lines.append("")
            lines.append(f"\tcolumn 'Time Calculation'")
            lines.append(f"\t\tdataType: string")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\tsourceColumn: Name")
            lines.append(f"\t\tsummarizeBy: none")
            lines.append("")
            lines.append(f"\tcalculationGroup")
            lines.append(f"\t\tprecedence: 10")
            lines.append("")
            # calculationItem in TMDL: 'Name' = <expression>. NO lineageTag —
            # not allowed by the schema. Multi-line expressions use triple
            # backticks; single-line goes inline after =.
            for item_name, expr in self.CALC_ITEMS.items():
                expr_clean = expr.strip()
                if "\n" in expr_clean:
                    lines.append(f"\t\tcalculationItem '{item_name}' = ```")
                    for el in expr_clean.split("\n"):
                        lines.append(f"\t\t\t{el}")
                    lines.append(f"\t\t\t```")
                else:
                    lines.append(f"\t\tcalculationItem '{item_name}' = {expr_clean}")
                lines.append("")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.fixes_applied.append(
                ("Regenerado" if broken else "Creado")
                + f" Calculation Group 'Time Intelligence' con "
                + f"{len(self.CALC_ITEMS)} items"
            )
            return

        self.fixes_applied.append(
            "MANUAL: Crear Calculation Group 'Time Intelligence' manualmente"
        )


class FixUnitsCalcGroup(BaseFixer):
    """Create a Units calculation group for currency/unit conversion."""

    fixer_id = "fix_units_calc_group"
    name = "Crear Calculation Group: Unidades"
    description = (
        "Crea un Calculation Group de Unidades con items: "
        "Valor, Miles (K), Millones (M), Porcentaje. "
        "Permite cambiar la escala de cualquier medida dinámicamente."
    )
    category = "model"
    severity = "info"
    requires_pbip = True

    CALC_ITEMS = {
        "Valor": ("SELECTEDMEASURE()", "#,0.00"),
        "Miles (K)": ("DIVIDE(SELECTEDMEASURE(), 1000)", "#,0.0 K"),
        "Millones (M)": ("DIVIDE(SELECTEDMEASURE(), 1000000)", "#,0.00 M"),
        "Porcentaje": ("SELECTEDMEASURE()", "0.0%"),
    }

    def scan(self):
        model = self.result._raw_model_data
        model_data = model.get("model", model)
        for table in self._iter_user_tables(model_data):
            if table.get("calculationGroup"):
                tname = table.get("name", "").lower()
                if any(kw in tname for kw in ("unit", "unidad", "scale", "escala", "format")):
                    return

        # TMDL — only return early if the existing file is VALID.
        # See FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag for context.
        for _, content, tname in self._iter_tmdl_table_files():
            if "calculationGroup" not in content:
                continue
            if not any(kw in tname.lower() for kw in ("unit", "unidad", "scale", "escala")):
                continue
            if FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag(content):
                self.issues.append(
                    f"'{tname}' tiene lineageTag inválido en calculationItem — regenerar"
                )
                return
            return  # valid existing file

        self.issues.append(
            "No se detectó Calculation Group de Unidades. "
            "Permite cambiar escala (K, M, %) dinámicamente."
        )

    def fix(self):
        if not self.issues:
            self.scan()
        if not self.issues:
            return

        import uuid
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")

        if os.path.isdir(tables_dir):
            path = os.path.join(tables_dir, "Units.tmdl")
            broken = False
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = f.read()
                    broken = FixTimeIntelligenceGroup._has_invalid_calcitem_lineagetag(existing)
                except Exception:
                    broken = False
                if not broken:
                    if FixTimeIntelligenceGroup._ensure_discourage_implicit_measures(
                        model_def, self.result._model_base_path
                    ):
                        self.fixes_applied.append(
                            "model.tmdl: discourageImplicitMeasures: true "
                            "(requerido para calculation groups)"
                        )
                    return

            # About to write the calc group — enforce the model flag first.
            if FixTimeIntelligenceGroup._ensure_discourage_implicit_measures(
                model_def, self.result._model_base_path
            ):
                self.fixes_applied.append(
                    "model.tmdl: discourageImplicitMeasures: true "
                    "(requerido para calculation groups)"
                )

            lines = [f"table Units"]
            lines.append(f"\tlineageTag: {uuid.uuid4()}")
            lines.append("")
            lines.append(f"\tcolumn 'Display Unit'")
            lines.append(f"\t\tdataType: string")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\tsourceColumn: Name")
            lines.append(f"\t\tsummarizeBy: none")
            lines.append("")
            lines.append(f"\tcalculationGroup")
            lines.append(f"\t\tprecedence: 5")
            lines.append("")
            # calculationItem: 'Name' = <expression>. NO lineageTag (invalid TMDL).
            for item_name, (expr, fmt) in self.CALC_ITEMS.items():
                lines.append(f"\t\tcalculationItem '{item_name}' = {expr}")
                lines.append(f"\t\t\tformatStringDefinition = \"{fmt}\"")
                lines.append("")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.fixes_applied.append(
                ("Regenerado" if broken else "Creado")
                + f" Calculation Group 'Units' con "
                + f"{len(self.CALC_ITEMS)} items"
            )
            return

        self.fixes_applied.append(
            "MANUAL: Crear Calculation Group 'Units' manualmente"
        )
