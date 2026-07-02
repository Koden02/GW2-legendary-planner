from __future__ import annotations

import json
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.snapshot import AccountSnapshot

RecurringPeriod = Literal["daily", "weekly"]
RecurringTargetKind = Literal["manual", "achievement", "currency", "item"]


class RecurringTaskDefinition(BaseModel):
    """Data-only definition for a recurring daily or weekly task."""

    id: str
    name: str
    period: RecurringPeriod
    category: str
    target_kind: RecurringTargetKind = "manual"
    target_id: int | str | None = None
    required_quantity: int = 1
    action: str
    source_url: str
    last_verified: date
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class RecurringTaskStatus(BaseModel):
    """Account-state evaluation for one recurring task."""

    id: str
    name: str
    period: RecurringPeriod
    category: str
    target_kind: RecurringTargetKind
    target_id: int | str | None = None
    required_quantity: int
    current_progress: int
    missing_quantity: int
    readiness_percent: float
    is_trackable: bool
    is_complete: bool
    action: str
    source_url: str
    note: str | None = None
    tags: list[str] = Field(default_factory=list)
    locations: list[InventoryLocation] = Field(default_factory=list)


class RecurringTaskDataError(Exception):
    """Raised when recurring task data cannot be loaded."""


def load_recurring_task_definitions() -> list[RecurringTaskDefinition]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "recurring_tasks.json"
    )
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecurringTaskDataError(
            f"Packaged recurring task data could not be read: {exc}"
        ) from exc
    return _parse_recurring_task_definitions(text, source=str(data_path))


def load_recurring_task_definitions_from_path(path: Path) -> list[RecurringTaskDefinition]:
    data_path = Path(path)
    if not data_path.exists():
        raise RecurringTaskDataError(f"Recurring task data file does not exist: {data_path}")
    if not data_path.is_file():
        raise RecurringTaskDataError(f"Recurring task data path is not a file: {data_path}")
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecurringTaskDataError(
            f"Recurring task data file could not be read: {data_path}: {exc}"
        ) from exc
    return _parse_recurring_task_definitions(text, source=str(data_path))


def build_recurring_task_report(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    definitions: list[RecurringTaskDefinition] | None = None,
    periods: set[str] | None = None,
    include_complete: bool = True,
) -> list[RecurringTaskStatus]:
    normalized_periods = {_normalize_filter(period) for period in periods or set()}
    statuses: list[RecurringTaskStatus] = []
    for definition in definitions or load_recurring_task_definitions():
        if normalized_periods and _normalize_filter(definition.period) not in normalized_periods:
            continue
        current_progress, locations, is_trackable = _current_progress(
            definition,
            snapshot,
            inventory,
        )
        required = max(definition.required_quantity, 1)
        missing = max(required - current_progress, 0)
        readiness = min(current_progress / required, 1.0)
        status = RecurringTaskStatus(
            id=definition.id,
            name=definition.name,
            period=definition.period,
            category=definition.category,
            target_kind=definition.target_kind,
            target_id=definition.target_id,
            required_quantity=required,
            current_progress=current_progress,
            missing_quantity=missing,
            readiness_percent=round(readiness * 100, 2),
            is_trackable=is_trackable,
            is_complete=is_trackable and missing == 0,
            action=definition.action,
            source_url=definition.source_url,
            note=definition.note,
            tags=definition.tags,
            locations=locations,
        )
        if include_complete or not status.is_complete:
            statuses.append(status)
    return statuses


def filter_recurring_tasks(
    statuses: list[RecurringTaskStatus],
    *,
    task_ids: set[str] | None = None,
    periods: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[RecurringTaskStatus]:
    normalized_task_ids = {_normalize_filter(value) for value in task_ids or set()}
    normalized_periods = {_normalize_filter(value) for value in periods or set()}
    normalized_tags = {_normalize_filter(value) for value in tags or set()}
    filtered: list[RecurringTaskStatus] = []
    for status in statuses:
        status_ids = {status.id, status.id.replace("_", "-")}
        status_tags = {_normalize_filter(tag) for tag in status.tags}
        if normalized_task_ids and not normalized_task_ids.intersection(status_ids):
            continue
        if normalized_periods and _normalize_filter(status.period) not in normalized_periods:
            continue
        if normalized_tags and not normalized_tags.issubset(status_tags):
            continue
        filtered.append(status)
    return filtered


def _current_progress(
    definition: RecurringTaskDefinition,
    snapshot: AccountSnapshot,
    inventory: Inventory,
) -> tuple[int, list[InventoryLocation], bool]:
    if definition.target_kind == "manual":
        return 0, [], False
    if definition.target_kind == "achievement" and isinstance(definition.target_id, int):
        quantity = snapshot.achievement_current(definition.target_id)
        locations = (
            [InventoryLocation(source="achievements", quantity=quantity)]
            if quantity
            else []
        )
        return quantity, locations, True
    if definition.target_kind == "currency" and isinstance(definition.target_id, int):
        quantity = snapshot.wallet_value(definition.target_id)
        locations = [InventoryLocation(source="wallet", quantity=quantity)] if quantity else []
        return quantity, locations, True
    if definition.target_kind == "item" and isinstance(definition.target_id, int):
        return (
            inventory.quantity_for(definition.target_id),
            inventory.locations_for(definition.target_id),
            True,
        )
    return 0, [], False


def _parse_recurring_task_definitions(
    text: str,
    *,
    source: str,
) -> list[RecurringTaskDefinition]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecurringTaskDataError(
            f"Recurring task data in {source} is malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, list):
        raise RecurringTaskDataError(f"Recurring task data in {source} must be a JSON array.")
    try:
        return [RecurringTaskDefinition.model_validate(entry) for entry in payload]
    except ValidationError as exc:
        raise RecurringTaskDataError(
            f"Recurring task data in {source} failed schema validation: {exc}"
        ) from exc


def _normalize_filter(value: str) -> str:
    return value.strip().lower().replace("_", "-")
