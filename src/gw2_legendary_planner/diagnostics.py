from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rich.console import Console

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.config.settings import Settings


class DiagnosticStatus(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Diagnostic:
    check: str
    status: DiagnosticStatus
    detail: str
    fix: str = ""


@dataclass(frozen=True)
class DoctorReport:
    diagnostics: list[Diagnostic]

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.status == DiagnosticStatus.ERROR for diagnostic in self.diagnostics)


def build_doctor_report(
    *,
    input_dir: Path | None = None,
    require_api_key: bool = False,
    api_key: str | None = None,
    cache_dir: Path | None = None,
) -> DoctorReport:
    settings = Settings.from_environment()
    diagnostics = [
        _python_version_check(),
        _uv_check(),
        _api_key_check(api_key or settings.api_key, require_api_key),
        _cache_writable_check(cache_dir or settings.cache_dir),
    ]
    diagnostics.extend(_local_export_checks(input_dir))
    return DoctorReport(diagnostics=diagnostics)


def render_doctor_report(console: Console, report: DoctorReport) -> None:
    console.print("GW2 Legendary Planner Doctor")
    for diagnostic in report.diagnostics:
        console.print(
            f"{_status_label(diagnostic.status)} {diagnostic.check}: {diagnostic.detail}"
        )
        if diagnostic.fix:
            console.print(f"  Fix: {diagnostic.fix}")


def _python_version_check() -> Diagnostic:
    version = platform.python_version()
    current_version = tuple(int(part) for part in platform.python_version_tuple()[:2])
    if current_version >= (3, 13):
        return Diagnostic(
            check="Python version",
            status=DiagnosticStatus.OK,
            detail=f"Python {version} is supported.",
        )
    return Diagnostic(
        check="Python version",
        status=DiagnosticStatus.ERROR,
        detail=f"Python {version} is too old.",
        fix="Install Python 3.13 or newer and recreate the virtual environment.",
    )


def _uv_check() -> Diagnostic:
    uv_path = os.getenv("UV") or shutil.which("uv")
    if uv_path:
        return Diagnostic(
            check="uv",
            status=DiagnosticStatus.OK,
            detail=f"uv found at {uv_path}.",
        )
    return Diagnostic(
        check="uv",
        status=DiagnosticStatus.WARNING,
        detail="uv was not found on PATH.",
        fix="Install uv or run commands through the Python module form, such as py -3.13 -m uv.",
    )


def _api_key_check(api_key: str | None, require_api_key: bool) -> Diagnostic:
    if api_key:
        return Diagnostic(
            check="API key",
            status=DiagnosticStatus.OK,
            detail="API key is configured.",
        )
    if require_api_key:
        return Diagnostic(
            check="API key",
            status=DiagnosticStatus.ERROR,
            detail="No API key was provided or found in GW2PLANNER_API_KEY / GW2_API_KEY.",
            fix="Pass --api-key or set GW2PLANNER_API_KEY before using live API commands.",
        )
    return Diagnostic(
        check="API key",
        status=DiagnosticStatus.OK,
        detail="API key is not required for the selected checks.",
    )


def _cache_writable_check(cache_dir: Path) -> Diagnostic:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        test_path = cache_dir / ".write-test"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
    except OSError as exc:
        return Diagnostic(
            check="Cache directory",
            status=DiagnosticStatus.ERROR,
            detail=f"Cache directory is not writable: {cache_dir} ({exc}).",
            fix="Choose a writable path with GW2PLANNER_CACHE_DIR or fix directory permissions.",
        )
    return Diagnostic(
        check="Cache directory",
        status=DiagnosticStatus.OK,
        detail=f"Cache directory is writable: {cache_dir}.",
    )


def _local_export_checks(input_dir: Path | None) -> list[Diagnostic]:
    if not input_dir:
        return [
            Diagnostic(
                check="Local exports",
                status=DiagnosticStatus.OK,
                detail="No --input directory provided; local export validation skipped.",
            )
        ]

    validation = LocalExportLoader(input_dir).validate()
    if validation.is_valid:
        return [
            Diagnostic(
                check="Local exports",
                status=DiagnosticStatus.OK,
                detail=f"All required local exports are valid in {input_dir}.",
            )
        ]

    return [
        Diagnostic(
            check=f"Local exports: {issue.endpoint or 'directory'}",
            status=DiagnosticStatus.ERROR,
            detail=issue.message,
            fix=issue.fix,
        )
        for issue in validation.issues
    ]


def _status_label(status: DiagnosticStatus) -> str:
    if status == DiagnosticStatus.OK:
        return "[green]OK[/green]"
    if status == DiagnosticStatus.WARNING:
        return "[yellow]WARNING[/yellow]"
    return "[red]ERROR[/red]"
