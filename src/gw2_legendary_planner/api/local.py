from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gw2_legendary_planner.models.snapshot import AccountSnapshot

EXPORT_FILE_ALIASES: dict[str, tuple[str, ...]] = {
    "account": ("account.json", "v2_account.json"),
    "wallet": ("account_wallet.json", "wallet.json", "v2_account_wallet.json"),
    "achievements": (
        "account_achievements.json",
        "achievements.json",
        "v2_account_achievements.json",
    ),
    "materials": ("account_materials.json", "materials.json", "v2_account_materials.json"),
    "bank": ("account_bank.json", "bank.json", "v2_account_bank.json"),
    "shared_inventory": (
        "account_inventory.json",
        "shared_inventory.json",
        "inventory.json",
        "v2_account_inventory.json",
    ),
    "legendary_armory": (
        "account_legendaryarmory.json",
        "legendary_armory.json",
        "legendaryarmory.json",
        "v2_account_legendaryarmory.json",
    ),
    "characters": ("characters.json", "characters_all.json", "v2_characters_all.json"),
}

REQUIRED_EXPORTS: tuple[str, ...] = tuple(EXPORT_FILE_ALIASES)
EXPECTED_PAYLOAD_TYPES: dict[str, type] = {
    "account": dict,
    "wallet": list,
    "achievements": list,
    "materials": list,
    "bank": list,
    "shared_inventory": list,
    "legendary_armory": list,
    "characters": list,
}


@dataclass(frozen=True)
class LocalExportIssue:
    code: str
    message: str
    fix: str
    endpoint: str | None = None
    path: Path | None = None


@dataclass
class LocalExportValidationReport:
    export_dir: Path
    payloads: dict[str, Any] = field(default_factory=dict)
    files: dict[str, Path] = field(default_factory=dict)
    issues: list[LocalExportIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues


class LocalExportError(RuntimeError):
    """Raised when local GW2 API exports cannot be loaded safely."""

    def __init__(self, report: LocalExportValidationReport) -> None:
        self.report = report
        messages = "; ".join(issue.message for issue in report.issues)
        super().__init__(messages or "Local export validation failed.")


class LocalExportLoader:
    """Load supported GW2 API endpoint exports from a local directory."""

    def __init__(self, export_dir: Path) -> None:
        self.export_dir = export_dir

    def load(self) -> AccountSnapshot:
        report = self.validate()
        if not report.is_valid:
            raise LocalExportError(report)
        return AccountSnapshot.from_raw(report.payloads)

    def validate(self) -> LocalExportValidationReport:
        report = LocalExportValidationReport(export_dir=self.export_dir)
        if not self.export_dir.exists():
            report.issues.append(
                LocalExportIssue(
                    code="export_dir_missing",
                    message=f"Export directory does not exist: {self.export_dir}",
                    fix="Create the directory or pass --input with the correct export path.",
                    path=self.export_dir,
                )
            )
            return report
        if not self.export_dir.is_dir():
            report.issues.append(
                LocalExportIssue(
                    code="export_path_not_directory",
                    message=f"Export path is not a directory: {self.export_dir}",
                    fix="Pass a directory containing GW2 API JSON exports.",
                    path=self.export_dir,
                )
            )
            return report

        report.issues.extend(self._unsupported_version_issues())

        for endpoint in REQUIRED_EXPORTS:
            aliases = EXPORT_FILE_ALIASES[endpoint]
            path = self._find_first_available(aliases)
            if not path:
                report.issues.append(
                    LocalExportIssue(
                        code="missing_endpoint_export",
                        endpoint=endpoint,
                        message=f"Missing {endpoint} export.",
                        fix=(
                            f"Export the matching GW2 API endpoint and save it as "
                            f"{aliases[0]}."
                        ),
                    )
                )
                continue

            report.files[endpoint] = path
            payload = self._load_json(path, endpoint, report)
            if payload is None:
                continue
            self._validate_payload_shape(endpoint, path, payload, report)
            report.payloads[endpoint] = payload

        if report.issues:
            return report

        try:
            AccountSnapshot.from_raw(report.payloads)
        except ValidationError as exc:
            report.issues.append(
                LocalExportIssue(
                    code="schema_validation_failed",
                    message=f"Endpoint payload schema validation failed: {exc.errors()[0]['msg']}",
                    fix="Re-export the endpoint JSON from the supported GW2 API v2 endpoints.",
                )
            )
        return report

    def _find_first_available(self, aliases: tuple[str, ...]) -> Path | None:
        for alias in aliases:
            path = self.export_dir / alias
            if path.exists():
                return path
        return None

    def _load_json(
        self,
        path: Path,
        endpoint: str,
        report: LocalExportValidationReport,
    ) -> Any | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except JSONDecodeError as exc:
            report.issues.append(
                LocalExportIssue(
                    code="malformed_json",
                    endpoint=endpoint,
                    path=path,
                    message=(
                        f"Malformed JSON in {path.name}: line {exc.lineno}, "
                        f"column {exc.colno}."
                    ),
                    fix="Re-export this endpoint or fix the JSON syntax.",
                )
            )
        return None

    def _validate_payload_shape(
        self,
        endpoint: str,
        path: Path,
        payload: Any,
        report: LocalExportValidationReport,
    ) -> None:
        expected_type = EXPECTED_PAYLOAD_TYPES[endpoint]
        if isinstance(payload, expected_type):
            return
        expected_name = "object" if expected_type is dict else "array"
        actual_name = type(payload).__name__
        report.issues.append(
            LocalExportIssue(
                code="invalid_payload_shape",
                endpoint=endpoint,
                path=path,
                message=(
                    f"{path.name} has the wrong payload shape for {endpoint}: "
                    f"expected JSON {expected_name}, got {actual_name}."
                ),
                fix="Re-export the endpoint directly from the GW2 API v2 endpoint.",
            )
        )

    def _unsupported_version_issues(self) -> list[LocalExportIssue]:
        issues: list[LocalExportIssue] = []
        for path in self.export_dir.glob("*.json"):
            name = path.name.lower()
            if name.startswith("v1_") or "_v1" in name or name.endswith("_v1.json"):
                issues.append(
                    LocalExportIssue(
                        code="unsupported_endpoint_version",
                        path=path,
                        message=f"Unsupported endpoint export version detected: {path.name}.",
                        fix=(
                            "Only GW2 API v2 exports are supported. Remove this file "
                            "or re-export v2 data."
                        ),
                    )
                )
        return issues
