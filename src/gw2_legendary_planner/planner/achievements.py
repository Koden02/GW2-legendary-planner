from __future__ import annotations

import json
from datetime import date
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from gw2_legendary_planner.models.snapshot import AccountSnapshot


class AchievementGoalDefinition(BaseModel):
    """Data-only definition for account achievement progress tracking."""

    id: str
    name: str
    category: str
    achievement_id: int
    required_progress: int = 1
    require_done: bool = False
    source_url: str
    last_verified: date
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class AchievementGoalStatus(BaseModel):
    """Account progress for one data-defined achievement goal."""

    id: str
    name: str
    category: str
    achievement_id: int
    current_progress: int
    required_progress: int
    max_progress: int | None = None
    is_done: bool
    is_complete: bool
    readiness_percent: float
    source_url: str
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class AchievementDataError(Exception):
    """Raised when achievement planner data cannot be loaded."""


def load_achievement_goal_definitions() -> list[AchievementGoalDefinition]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "achievement_goals.json"
    )
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AchievementDataError(
            f"Packaged achievement data could not be read: {exc}"
        ) from exc
    return _parse_achievement_goal_definitions(text, source=str(data_path))


def load_achievement_goal_definitions_from_path(
    path: Path,
) -> list[AchievementGoalDefinition]:
    data_path = Path(path)
    if not data_path.exists():
        raise AchievementDataError(f"Achievement data file does not exist: {data_path}")
    if not data_path.is_file():
        raise AchievementDataError(f"Achievement data path is not a file: {data_path}")
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AchievementDataError(
            f"Achievement data file could not be read: {data_path}: {exc}"
        ) from exc
    return _parse_achievement_goal_definitions(text, source=str(data_path))


def build_achievement_report(
    snapshot: AccountSnapshot,
    *,
    definitions: list[AchievementGoalDefinition] | None = None,
    include_complete: bool = True,
) -> list[AchievementGoalStatus]:
    statuses: list[AchievementGoalStatus] = []
    for definition in definitions or load_achievement_goal_definitions():
        entry = snapshot.achievement_entry(definition.achievement_id)
        current = snapshot.achievement_current(definition.achievement_id)
        max_progress = entry.max if entry else None
        is_done = snapshot.achievement_done(definition.achievement_id)
        required = max(definition.required_progress, 1)
        readiness = min(current / required, 1.0)
        is_complete = is_done if definition.require_done else current >= required or is_done
        status = AchievementGoalStatus(
            id=definition.id,
            name=definition.name,
            category=definition.category,
            achievement_id=definition.achievement_id,
            current_progress=current,
            required_progress=required,
            max_progress=max_progress,
            is_done=is_done,
            is_complete=is_complete,
            readiness_percent=round(readiness * 100, 2),
            source_url=definition.source_url,
            note=definition.note,
            tags=definition.tags,
        )
        if include_complete or not status.is_complete:
            statuses.append(status)
    return statuses


def filter_achievement_goals(
    statuses: list[AchievementGoalStatus],
    *,
    goal_ids: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[AchievementGoalStatus]:
    normalized_goal_ids = {_normalize_filter(value) for value in goal_ids or set()}
    normalized_tags = {_normalize_filter(value) for value in tags or set()}
    filtered: list[AchievementGoalStatus] = []
    for status in statuses:
        status_goal_ids = {status.id, status.id.replace("_", "-")}
        status_tags = {_normalize_filter(tag) for tag in status.tags}
        if normalized_goal_ids and not normalized_goal_ids.intersection(status_goal_ids):
            continue
        if normalized_tags and not normalized_tags.issubset(status_tags):
            continue
        filtered.append(status)
    return filtered


def _parse_achievement_goal_definitions(
    text: str,
    *,
    source: str,
) -> list[AchievementGoalDefinition]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AchievementDataError(
            f"Achievement data in {source} is malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, list):
        raise AchievementDataError(f"Achievement data in {source} must be a JSON array.")
    try:
        return [AchievementGoalDefinition.model_validate(entry) for entry in payload]
    except ValidationError as exc:
        raise AchievementDataError(
            f"Achievement data in {source} failed schema validation: {exc}"
        ) from exc


def _normalize_filter(value: str) -> str:
    return value.strip().lower().replace("_", "-")
