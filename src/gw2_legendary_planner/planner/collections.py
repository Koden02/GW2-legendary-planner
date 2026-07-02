from __future__ import annotations

import json
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.snapshot import AccountSnapshot

CollectionTargetKind = Literal[
    "item",
    "currency",
    "legendary_armory",
    "achievement",
    "collection",
    "account_unlock",
]


class CollectionRequirement(BaseModel):
    """One data-defined requirement in a progression collection."""

    id: str
    name: str
    target_kind: CollectionTargetKind
    target_id: int | str
    required_quantity: int = 1
    note: str | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)


class CollectionDefinition(BaseModel):
    """Data-only definition of a source-verifiable collection checklist."""

    id: str
    name: str
    category: str
    source_url: str
    last_verified: date
    requirements: list[CollectionRequirement] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CollectionRequirementStatus(BaseModel):
    """Account progress for one collection requirement."""

    id: str
    name: str
    target_kind: CollectionTargetKind
    target_id: int | str
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    readiness_percent: float
    is_complete: bool
    is_supported: bool
    note: str | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    locations: list[InventoryLocation] = Field(default_factory=list)


class CollectionProgress(BaseModel):
    """Account progress for a data-defined collection."""

    id: str
    name: str
    category: str
    source_url: str
    last_verified: date
    readiness_percent: float
    is_complete: bool
    completed_requirements: int
    total_requirements: int
    unsupported_requirements: int
    tags: list[str] = Field(default_factory=list)
    requirements: list[CollectionRequirementStatus] = Field(default_factory=list)


class CollectionDataError(Exception):
    """Raised when collection definition data cannot be loaded."""


def load_collection_definitions() -> list[CollectionDefinition]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "collection_goals.json"
    )
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CollectionDataError(f"Packaged collection data could not be read: {exc}") from exc
    return _parse_collection_definitions(text, source=str(data_path))


def load_collection_definitions_from_path(path: Path) -> list[CollectionDefinition]:
    data_path = Path(path)
    if not data_path.exists():
        raise CollectionDataError(f"Collection data file does not exist: {data_path}")
    if not data_path.is_file():
        raise CollectionDataError(f"Collection data path is not a file: {data_path}")
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CollectionDataError(
            f"Collection data file could not be read: {data_path}: {exc}"
        ) from exc
    return _parse_collection_definitions(text, source=str(data_path))


def evaluate_collections(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    definitions: list[CollectionDefinition] | None = None,
    include_complete: bool = True,
) -> list[CollectionProgress]:
    """Evaluate data-defined collection progress from shared account state."""

    progress_entries: list[CollectionProgress] = []
    for definition in definitions or load_collection_definitions():
        requirement_statuses = [
            _evaluate_requirement(requirement, snapshot, inventory)
            for requirement in definition.requirements
        ]
        total_required = sum(requirement.required_quantity for requirement in requirement_statuses)
        total_available = sum(
            min(requirement.available_quantity, requirement.required_quantity)
            for requirement in requirement_statuses
        )
        readiness = min(total_available / total_required, 1.0) if total_required else 1.0
        unsupported = sum(1 for requirement in requirement_statuses if not requirement.is_supported)
        completed = sum(1 for requirement in requirement_statuses if requirement.is_complete)
        is_complete = bool(requirement_statuses) and completed == len(requirement_statuses)
        progress = CollectionProgress(
            id=definition.id,
            name=definition.name,
            category=definition.category,
            source_url=definition.source_url,
            last_verified=definition.last_verified,
            readiness_percent=round(readiness * 100, 2),
            is_complete=is_complete,
            completed_requirements=completed,
            total_requirements=len(requirement_statuses),
            unsupported_requirements=unsupported,
            tags=definition.tags,
            requirements=requirement_statuses,
        )
        if include_complete or not progress.is_complete:
            progress_entries.append(progress)
    return progress_entries


def filter_collections(
    progress_entries: list[CollectionProgress],
    *,
    collection_ids: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[CollectionProgress]:
    normalized_collection_ids = {_normalize_filter(value) for value in collection_ids or set()}
    normalized_tags = {_normalize_filter(value) for value in tags or set()}
    filtered: list[CollectionProgress] = []
    for progress in progress_entries:
        progress_ids = {progress.id, progress.id.replace("_", "-")}
        progress_tags = {_normalize_filter(tag) for tag in progress.tags}
        if normalized_collection_ids and not normalized_collection_ids.intersection(progress_ids):
            continue
        if normalized_tags and not normalized_tags.issubset(progress_tags):
            continue
        filtered.append(progress)
    return filtered


def _evaluate_requirement(
    requirement: CollectionRequirement,
    snapshot: AccountSnapshot,
    inventory: Inventory,
) -> CollectionRequirementStatus:
    available_quantity, locations, is_supported = _available_quantity(
        requirement,
        snapshot,
        inventory,
    )
    missing_quantity = max(requirement.required_quantity - available_quantity, 0)
    readiness = (
        min(available_quantity / requirement.required_quantity, 1.0)
        if requirement.required_quantity
        else 1.0
    )
    note = requirement.note
    if not is_supported:
        note = (
            f"{requirement.target_kind} tracking requires a future account data source."
            if note is None
            else note
        )
    return CollectionRequirementStatus(
        id=requirement.id,
        name=requirement.name,
        target_kind=requirement.target_kind,
        target_id=requirement.target_id,
        required_quantity=requirement.required_quantity,
        available_quantity=available_quantity,
        missing_quantity=missing_quantity,
        readiness_percent=round(readiness * 100, 2),
        is_complete=missing_quantity == 0 and is_supported,
        is_supported=is_supported,
        note=note,
        source_url=requirement.source_url,
        tags=requirement.tags,
        locations=locations,
    )


def _available_quantity(
    requirement: CollectionRequirement,
    snapshot: AccountSnapshot,
    inventory: Inventory,
) -> tuple[int, list[InventoryLocation], bool]:
    if requirement.target_kind == "item" and isinstance(requirement.target_id, int):
        return (
            inventory.quantity_for(requirement.target_id),
            inventory.locations_for(requirement.target_id),
            True,
        )
    if requirement.target_kind == "currency" and isinstance(requirement.target_id, int):
        quantity = snapshot.wallet_value(requirement.target_id)
        locations = [InventoryLocation(source="wallet", quantity=quantity)] if quantity else []
        return quantity, locations, True
    if requirement.target_kind == "legendary_armory" and isinstance(
        requirement.target_id,
        int,
    ):
        quantity = sum(
            entry.count for entry in snapshot.legendary_armory if entry.id == requirement.target_id
        )
        locations = (
            [InventoryLocation(source="legendary_armory", quantity=quantity)]
            if quantity
            else []
        )
        return quantity, locations, True
    if requirement.target_kind == "achievement" and isinstance(requirement.target_id, int):
        quantity = snapshot.achievement_current(requirement.target_id)
        locations = (
            [InventoryLocation(source="achievements", quantity=quantity)]
            if quantity
            else []
        )
        return quantity, locations, True
    return 0, [], False


def _parse_collection_definitions(text: str, *, source: str) -> list[CollectionDefinition]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CollectionDataError(f"Collection data in {source} is malformed JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise CollectionDataError(f"Collection data in {source} must be a JSON array.")
    try:
        return [CollectionDefinition.model_validate(entry) for entry in payload]
    except ValidationError as exc:
        raise CollectionDataError(
            f"Collection data in {source} failed schema validation: {exc}"
        ) from exc


def _normalize_filter(value: str) -> str:
    return value.strip().lower().replace("_", "-")
