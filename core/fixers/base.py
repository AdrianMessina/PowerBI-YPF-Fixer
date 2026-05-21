"""Base fixer class and fixer engine with trust & validation."""

import json
import os
import shutil
from datetime import datetime
from abc import ABC, abstractmethod

from core.models import AnalysisResult, BackupInfo, FixMode, FixResult, FileType


class BaseFixer(ABC):
    """Base class for all fixers."""

    fixer_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""          # "report", "model", "bpa"
    severity: str = "warning"   # default severity
    requires_pbip: bool = False
    confidence: str = "high"    # "high" | "medium" | "low"
    detection_method: str = "pattern_match"  # "pattern_match" | "threshold" | "heuristic"
    is_manual: bool = False

    def __init__(self, result: AnalysisResult):
        self.result = result
        self.issues = []
        self.fixes_applied = []

    def run(self, mode: FixMode = FixMode.SCAN) -> FixResult:
        """Run the fixer in the specified mode."""
        fix_result = FixResult(
            fixer_id=self.fixer_id,
            fixer_name=self.name,
            category=self.category,
            mode=mode,
            severity=self.severity,
            confidence=self.confidence,
            detection_method=self.detection_method,
            is_manual=self.is_manual,
        )

        if self.requires_pbip and self.result.file_type == FileType.PBIX:
            fix_result.error = "Este fix solo funciona con archivos PBIP/PBIR (no PBIX)"
            fix_result.success = False
            return fix_result

        try:
            # Scan phase
            self.issues = []
            self.scan()
            fix_result.issues_found = len(self.issues)
            fix_result.details = [str(i) for i in self.issues]

            # Preview phase (no writes)
            if mode == FixMode.PREVIEW and self.issues:
                preview = self.preview()
                fix_result.before_preview = preview.get("before", "")
                fix_result.after_preview = preview.get("after", "")
                fix_result.affected_files = preview.get("affected_files", [])

            # Fix phase
            elif mode in (FixMode.FIX, FixMode.SCAN_AND_FIX) and self.issues:
                self.fixes_applied = []
                self.fix()
                fix_result.issues_fixed = len(self.fixes_applied)
                if self.fixes_applied:
                    fix_result.details = [str(f) for f in self.fixes_applied]

                # Validation: re-scan to confirm
                validation = self.validate()
                fix_result.validation_result = validation
                if not validation.get("passed", True):
                    fix_result.error = validation.get("message", "")

        except Exception as e:
            fix_result.success = False
            fix_result.error = str(e)

        return fix_result

    @abstractmethod
    def scan(self):
        """Scan for issues. Populate self.issues."""
        pass

    @abstractmethod
    def fix(self):
        """Fix the detected issues. Populate self.fixes_applied."""
        pass

    def preview(self) -> dict:
        """Generate before/after preview without writing files.
        Override in subclasses for detailed previews.
        """
        return {
            "before": f"{len(self.issues)} problema(s) detectado(s)",
            "after": f"Se corregiran {len(self.issues)} problema(s)" if not self.is_manual
                     else "Requiere correccion manual",
            "affected_files": [],
        }

    def validate(self) -> dict:
        """Re-scan after fix to confirm issues are resolved."""
        original_count = len(self.fixes_applied)
        self.issues = []
        self.scan()
        remaining = len(self.issues)

        return {
            "passed": remaining == 0,
            "issues_remaining": remaining,
            "issues_resolved": original_count,
            "message": (
                f"Validacion OK: {original_count} corregidos, 0 restantes"
                if remaining == 0
                else f"{remaining} problema(s) aun presentes despues del fix"
            ),
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _read_json_file(self, path: str) -> dict | list | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _write_json_file(self, path: str, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_report_definition_path(self) -> str:
        base = self.result._report_base_path
        defn = os.path.join(base, "definition")
        return defn if os.path.isdir(defn) else base

    def _get_model_definition_path(self) -> str:
        base = self.result._model_base_path
        defn = os.path.join(base, "definition")
        return defn if os.path.isdir(defn) else base

    def _iter_visual_files(self):
        """Iterate over all visual.json files in PBIR format."""
        report = self.result._raw_report_data
        sections = report.get("sections", [])
        for section in sections:
            page_name = section.get("displayName", section.get("name", ""))
            for container in section.get("visualContainers", []):
                visual_dir = container.get("_visual_dir", "")
                visual_id = container.get("_visual_id", "")
                if visual_dir:
                    visual_path = os.path.join(visual_dir, "visual.json")
                    if os.path.exists(visual_path):
                        data = self._read_json_file(visual_path)
                        if data:
                            yield visual_path, data, page_name, visual_id

    def _iter_page_files(self):
        """Iterate over all page.json files in PBIR format."""
        report = self.result._raw_report_data
        sections = report.get("sections", [])
        for section in sections:
            page_name = section.get("displayName", section.get("name", ""))
            page_dir = section.get("_page_dir", "")
            if page_dir:
                page_path = os.path.join(page_dir, "page.json")
                if os.path.exists(page_path):
                    data = self._read_json_file(page_path)
                    if data:
                        yield page_path, data, page_name

    def _iter_tmdl_table_files(self):
        """Iterate over all .tmdl table files."""
        model_def = self._get_model_definition_path()
        tables_dir = os.path.join(model_def, "tables")
        if not os.path.isdir(tables_dir):
            return
        import re
        for fname in os.listdir(tables_dir):
            if not fname.endswith(".tmdl"):
                continue
            fpath = os.path.join(tables_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.match(r"^table\s+'([^']+)'", content)
            tname = m.group(1) if m else fname.replace(".tmdl", "")
            yield fpath, content, tname


class FixerEngine:
    """Manages and runs multiple fixers."""

    def __init__(self, fixer_classes: list = None):
        from core.fixers import ALL_FIXERS
        self.fixer_classes = fixer_classes or ALL_FIXERS

    def get_available_fixers(self, result: AnalysisResult) -> list:
        fixers = []
        for cls in self.fixer_classes:
            fixer = cls(result)
            if fixer.requires_pbip and result.file_type == FileType.PBIX:
                continue
            fixers.append(fixer)
        return fixers

    def scan_all(self, result: AnalysisResult) -> list[FixResult]:
        results = []
        for fixer in self.get_available_fixers(result):
            fr = fixer.run(FixMode.SCAN)
            fr.severity = fixer.severity
            fr.confidence = fixer.confidence
            fr.detection_method = fixer.detection_method
            fr.is_manual = fixer.is_manual
            results.append(fr)
        return results

    def fix_all(self, result: AnalysisResult) -> list[FixResult]:
        results = []
        for fixer in self.get_available_fixers(result):
            results.append(fixer.run(FixMode.SCAN_AND_FIX))
        return results

    def run_single(self, fixer_id: str, result: AnalysisResult,
                   mode: FixMode = FixMode.SCAN) -> FixResult | None:
        for cls in self.fixer_classes:
            if cls.fixer_id == fixer_id:
                fixer = cls(result)
                return fixer.run(mode)
        return None

    @staticmethod
    def create_backup(result: AnalysisResult, fixer_ids: list = None) -> BackupInfo:
        """Create a backup with metadata tracking."""
        base_path = result._report_base_path or result.report_path
        if not os.path.isdir(base_path):
            base_path = os.path.dirname(base_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{base_path}_backup_{timestamp}"
        shutil.copytree(base_path, backup_path, dirs_exist_ok=False)

        file_count = sum(len(files) for _, _, files in os.walk(backup_path))
        size_mb = sum(
            os.path.getsize(os.path.join(root, f))
            for root, _, files in os.walk(backup_path) for f in files
        ) / (1024 * 1024)

        info = BackupInfo(
            backup_path=backup_path,
            created_at=datetime.now().isoformat(),
            report_name=result.report_name,
            file_count=file_count,
            size_mb=round(size_mb, 2),
            applied_fixers=fixer_ids or [],
        )

        # Save metadata file inside backup
        meta_path = os.path.join(backup_path, ".backup_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "created_at": info.created_at,
                "report_name": info.report_name,
                "file_count": info.file_count,
                "size_mb": info.size_mb,
                "applied_fixers": info.applied_fixers,
            }, f, indent=2)

        return info

    @staticmethod
    def restore_backup(backup_path: str, target_path: str) -> bool:
        """Restore project from backup."""
        try:
            meta = os.path.join(backup_path, ".backup_metadata.json")
            if not os.path.exists(meta):
                return False
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(backup_path, target_path)
            # Remove metadata file from restored copy
            restored_meta = os.path.join(target_path, ".backup_metadata.json")
            if os.path.exists(restored_meta):
                os.remove(restored_meta)
            return True
        except Exception:
            return False

    @staticmethod
    def list_backups(report_path: str) -> list[BackupInfo]:
        """List available backups for a project."""
        base = report_path
        if os.path.isfile(base):
            base = os.path.dirname(base)
        parent = os.path.dirname(base)
        backups = []
        try:
            for item in os.listdir(parent):
                if "_backup_" not in item:
                    continue
                bp = os.path.join(parent, item)
                mp = os.path.join(bp, ".backup_metadata.json")
                if os.path.exists(mp):
                    with open(mp, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    backups.append(BackupInfo(
                        backup_path=bp,
                        created_at=m.get("created_at", ""),
                        report_name=m.get("report_name", ""),
                        file_count=m.get("file_count", 0),
                        size_mb=m.get("size_mb", 0),
                        applied_fixers=m.get("applied_fixers", []),
                    ))
        except Exception:
            pass
        return sorted(backups, key=lambda b: b.created_at, reverse=True)
