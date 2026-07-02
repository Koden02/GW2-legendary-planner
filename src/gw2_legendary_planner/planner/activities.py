from __future__ import annotations

import json
from importlib import resources
from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner.inventory.models import Inventory, InventoryLocation
from gw2_legendary_planner.models.snapshot import AccountSnapshot

ActivityKind = Literal[
    "collection",
    "reward_track",
    "starter_kit",
    "wizard_vault",
    "world_completion",
]
ActivityTargetKind = Literal["item", "currency", "achievement", "collection", "account_unlock"]


class ActivityGoalDefinition(BaseModel):
    """Data-only definition for an account activity planner target."""

    id: str
    name: str
    category: str
    activity_kind: ActivityKind
    target_kind: ActivityTargetKind
    target_id: int | str
    required_quantity: int = 1
    action: str
    note: str | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)


class ActivityGoalStatus(BaseModel):
    """Readiness of one account activity goal against account state."""

    id: str
    name: str
    category: str
    activity_kind: ActivityKind
    target_kind: ActivityTargetKind
    target_id: int | str
    required_quantity: int
    available_quantity: int
    missing_quantity: int
    readiness_percent: float
    is_ready: bool
    action: str
    note: str | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    locations: list[InventoryLocation] = Field(default_factory=list)


def load_activity_goal_definitions() -> list[ActivityGoalDefinition]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "activity_goals.json"
    )
    return [
        ActivityGoalDefinition.model_validate(entry)
        for entry in json.loads(data_path.read_text(encoding="utf-8"))
    ]


def build_activity_report(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    *,
    definitions: list[ActivityGoalDefinition] | None = None,
    include_ready: bool = True,
) -> list[ActivityGoalStatus]:
    """Evaluate account activity goals using neutral account state."""

    statuses: list[ActivityGoalStatus] = []
    for definition in definitions or load_activity_goal_definitions():
        available_quantity, locations = _available_quantity(definition, snapshot, inventory)
        missing_quantity = max(definition.required_quantity - available_quantity, 0)
        readiness = (
            min(available_quantity / definition.required_quantity, 1.0)
            if definition.required_quantity
            else 1.0
        )
        status = ActivityGoalStatus(
            id=definition.id,
            name=definition.name,
            category=definition.category,
            activity_kind=definition.activity_kind,
            target_kind=definition.target_kind,
            target_id=definition.target_id,
            required_quantity=definition.required_quantity,
            available_quantity=available_quantity,
            missing_quantity=missing_quantity,
            readiness_percent=round(readiness * 100, 2),
            is_ready=missing_quantity == 0,
            action=definition.action,
            note=definition.note,
            source_url=definition.source_url,
            tags=definition.tags,
            locations=locations,
        )
        if include_ready or not status.is_ready:
            statuses.append(status)
    return statuses


def filter_activity_goals(
    statuses: list[ActivityGoalStatus],
    *,
    goal_ids: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[ActivityGoalStatus]:
    """Filter already-evaluated activity goal statuses for CLI/report surfaces."""

    normalized_goal_ids = {_normalize_filter(value) for value in goal_ids or set()}
    normalized_tags = {_normalize_filter(value) for value in tags or set()}
    filtered: list[ActivityGoalStatus] = []
    for status in statuses:
        status_goal_ids = {status.id, status.id.replace("_", "-")}
        status_tags = {_normalize_filter(tag) for tag in status.tags}
        if normalized_goal_ids and not normalized_goal_ids.intersection(status_goal_ids):
            continue
        if normalized_tags and not normalized_tags.issubset(status_tags):
            continue
        filtered.append(status)
    return filtered


def _available_quantity(
    definition: ActivityGoalDefinition,
    snapshot: AccountSnapshot,
    inventory: Inventory,
) -> tuple[int, list[InventoryLocation]]:
    if definition.target_kind == "item" and isinstance(definition.target_id, int):
        return (
            inventory.quantity_for(definition.target_id),
            inventory.locations_for(definition.target_id),
        )
    if definition.target_kind == "currency" and isinstance(definition.target_id, int):
        quantity = snapshot.wallet_value(definition.target_id)
        locations = [InventoryLocation(source="wallet", quantity=quantity)] if quantity else []
        return quantity, locations
    return 0, []


def _normalize_filter(value: str) -> str:
    return value.strip().lower().replace("_", "-")
