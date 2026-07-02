from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from gw2_legendary_planner.models.snapshot import AccountSnapshot

ASTRAL_ACCLAIM_CURRENCY_ID = 63
"""GW2 wallet currency id for Astral Acclaim."""

WizardVaultRewardKind = Literal[
    "currency",
    "item",
    "legendary_component",
    "starter_kit",
    "upgrade",
]
WizardVaultSeasonStatus = Literal["current", "future", "historical", "unknown"]


class WizardVaultReward(BaseModel):
    """One Wizard's Vault reward entry from source-verifiable seasonal data."""

    id: str
    name: str
    reward_kind: WizardVaultRewardKind
    astral_acclaim_cost: int
    purchase_limit: int | None = None
    item_id: int | None = None
    currency_id: int | None = None
    note: str | None = None
    source_url: str
    last_verified: date
    tags: list[str] = Field(default_factory=list)


class WizardVaultSeason(BaseModel):
    """Packaged Wizard's Vault season or reward table snapshot."""

    id: str
    name: str
    status: WizardVaultSeasonStatus = "unknown"
    starts_on: date | None = None
    ends_on: date | None = None
    source_url: str
    last_verified: date
    rewards: list[WizardVaultReward] = Field(default_factory=list)


class WizardVaultValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    season_id: str | None = None
    reward_id: str | None = None


class WizardVaultValidationReport(BaseModel):
    issues: list[WizardVaultValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


class WizardVaultRewardRecommendation(BaseModel):
    """Account-aware recommendation for one Wizard's Vault seasonal reward."""

    season_id: str
    season_name: str
    reward_id: str
    reward_name: str
    reward_kind: WizardVaultRewardKind
    astral_acclaim_cost: int
    purchase_limit: int | None = None
    priority_score: int
    is_affordable: bool
    affordable_quantity: int
    recommended_quantity: int
    recommended_cost: int
    remaining_after_purchase: int
    reason: str
    source_url: str
    tags: list[str] = Field(default_factory=list)


class WizardVaultOptimizationReport(BaseModel):
    """Ranked Wizard's Vault recommendations for the current account state."""

    astral_acclaim_currency_id: int = ASTRAL_ACCLAIM_CURRENCY_ID
    astral_acclaim_balance: int
    remaining_astral_acclaim: int
    recommendations: list[WizardVaultRewardRecommendation] = Field(default_factory=list)


class WizardVaultDataError(Exception):
    """Raised when Wizard's Vault data cannot be loaded."""


class WizardVaultValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class WizardVaultValidator:
    """Structural validator for Wizard's Vault seasonal data."""

    current_date: date | None = None
    max_current_age_days: int = 21

    def validate(self, seasons: list[WizardVaultSeason]) -> WizardVaultValidationReport:
        report = WizardVaultValidationReport()
        self._validate_duplicate_seasons(seasons, report)
        self._validate_season_shapes(seasons, report)
        self._validate_rewards(seasons, report)
        return report

    def _validate_duplicate_seasons(
        self,
        seasons: list[WizardVaultSeason],
        report: WizardVaultValidationReport,
    ) -> None:
        seen: set[str] = set()
        for season in seasons:
            if season.id in seen:
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.ERROR,
                    "duplicate_season_id",
                    f"Season id {season.id!r} appears more than once.",
                    season_id=season.id,
                )
            seen.add(season.id)

    def _validate_season_shapes(
        self,
        seasons: list[WizardVaultSeason],
        report: WizardVaultValidationReport,
    ) -> None:
        today = self.current_date or date.today()
        for season in seasons:
            if not season.id.strip():
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.ERROR,
                    "missing_season_id",
                    "Season id cannot be blank.",
                )
            if not season.name.strip():
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.ERROR,
                    "missing_season_name",
                    f"Season {season.id!r} must have a display name.",
                    season_id=season.id,
                )
            if season.starts_on and season.ends_on and season.starts_on > season.ends_on:
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.ERROR,
                    "invalid_season_dates",
                    f"Season {season.id!r} starts after it ends.",
                    season_id=season.id,
                )
            if not _is_http_url(season.source_url):
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.ERROR,
                    "invalid_season_source_url",
                    f"Season {season.id!r} needs an http(s) source URL.",
                    season_id=season.id,
                )
            if season.status == "current":
                age_days = (today - season.last_verified).days
                if age_days > self.max_current_age_days:
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "stale_current_season",
                        (
                            f"Current season {season.id!r} was last verified "
                            f"{age_days} days ago."
                        ),
                        season_id=season.id,
                    )
            if not season.rewards:
                _add_issue(
                    report,
                    WizardVaultValidationSeverity.WARNING,
                    "season_has_no_rewards",
                    f"Season {season.id!r} has no modeled rewards.",
                    season_id=season.id,
                )

    def _validate_rewards(
        self,
        seasons: list[WizardVaultSeason],
        report: WizardVaultValidationReport,
    ) -> None:
        for season in seasons:
            seen_reward_ids: set[str] = set()
            for reward in season.rewards:
                if reward.id in seen_reward_ids:
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "duplicate_reward_id",
                        (
                            f"Reward id {reward.id!r} appears more than once "
                            f"in season {season.id!r}."
                        ),
                        season_id=season.id,
                        reward_id=reward.id,
                    )
                seen_reward_ids.add(reward.id)

                if not reward.name.strip():
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "missing_reward_name",
                        f"Reward {reward.id!r} needs a display name.",
                        season_id=season.id,
                        reward_id=reward.id,
                    )
                if reward.astral_acclaim_cost <= 0:
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "invalid_reward_cost",
                        f"Reward {reward.id!r} must cost at least 1 Astral Acclaim.",
                        season_id=season.id,
                        reward_id=reward.id,
                    )
                if reward.purchase_limit is not None and reward.purchase_limit <= 0:
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "invalid_purchase_limit",
                        f"Reward {reward.id!r} purchase limit must be positive.",
                        season_id=season.id,
                        reward_id=reward.id,
                    )
                if not _is_http_url(reward.source_url):
                    _add_issue(
                        report,
                        WizardVaultValidationSeverity.ERROR,
                        "invalid_reward_source_url",
                        f"Reward {reward.id!r} needs an http(s) source URL.",
                        season_id=season.id,
                        reward_id=reward.id,
                    )


def load_wizard_vault_seasons() -> list[WizardVaultSeason]:
    data_path = resources.files("gw2_legendary_planner.data").joinpath(
        "wizards_vault_seasons.json"
    )
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WizardVaultDataError(
            f"Packaged Wizard's Vault data could not be read: {exc}"
        ) from exc
    return _parse_wizard_vault_seasons(text, source=str(data_path))


def load_wizard_vault_seasons_from_path(path: Path) -> list[WizardVaultSeason]:
    data_path = Path(path)
    if not data_path.exists():
        raise WizardVaultDataError(f"Wizard's Vault data file does not exist: {data_path}")
    if not data_path.is_file():
        raise WizardVaultDataError(f"Wizard's Vault data path is not a file: {data_path}")
    try:
        text = data_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WizardVaultDataError(
            f"Wizard's Vault data file could not be read: {data_path}: {exc}"
        ) from exc
    return _parse_wizard_vault_seasons(text, source=str(data_path))


def _parse_wizard_vault_seasons(text: str, *, source: str) -> list[WizardVaultSeason]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WizardVaultDataError(
            f"Wizard's Vault data in {source} is malformed JSON: {exc}"
        ) from exc
    if not isinstance(payload, list):
        raise WizardVaultDataError(
            f"Wizard's Vault data in {source} must be a JSON array."
        )
    try:
        return [WizardVaultSeason.model_validate(entry) for entry in payload]
    except ValidationError as exc:
        raise WizardVaultDataError(
            f"Wizard's Vault data in {source} failed schema validation: {exc}"
        ) from exc


def validate_wizard_vault_seasons(
    seasons: list[WizardVaultSeason],
    *,
    current_date: date | None = None,
    max_current_age_days: int = 21,
) -> WizardVaultValidationReport:
    return WizardVaultValidator(
        current_date=current_date,
        max_current_age_days=max_current_age_days,
    ).validate(seasons)


def filter_wizard_vault_seasons(
    seasons: list[WizardVaultSeason],
    *,
    season_ids: set[str] | None = None,
    statuses: set[str] | None = None,
    tags: set[str] | None = None,
) -> list[WizardVaultSeason]:
    normalized_season_ids = {_normalize_filter(value) for value in season_ids or set()}
    normalized_statuses = {_normalize_filter(value) for value in statuses or set()}
    normalized_tags = {_normalize_filter(value) for value in tags or set()}
    filtered: list[WizardVaultSeason] = []
    for season in seasons:
        if normalized_season_ids and _normalize_filter(season.id) not in normalized_season_ids:
            continue
        if normalized_statuses and _normalize_filter(season.status) not in normalized_statuses:
            continue
        rewards = [
            reward
            for reward in season.rewards
            if not normalized_tags
            or normalized_tags.issubset({_normalize_filter(tag) for tag in reward.tags})
        ]
        if normalized_tags and not rewards:
            continue
        filtered.append(season.model_copy(update={"rewards": rewards}))
    return filtered


def optimize_wizard_vault_rewards(
    snapshot: AccountSnapshot,
    seasons: list[WizardVaultSeason],
    *,
    astral_acclaim_currency_id: int = ASTRAL_ACCLAIM_CURRENCY_ID,
) -> WizardVaultOptimizationReport:
    """Rank legendary-relevant Wizard's Vault rewards against account currency."""

    balance = snapshot.wallet_value(astral_acclaim_currency_id)
    recommendations = _rank_wizard_vault_rewards(seasons, balance)
    remaining = balance
    planned_recommendations: list[WizardVaultRewardRecommendation] = []
    for recommendation in recommendations:
        recommended_quantity = min(
            recommendation.affordable_quantity,
            remaining // recommendation.astral_acclaim_cost,
        )
        recommended_cost = recommended_quantity * recommendation.astral_acclaim_cost
        remaining -= recommended_cost
        planned_recommendations.append(
            recommendation.model_copy(
                update={
                    "recommended_quantity": recommended_quantity,
                    "recommended_cost": recommended_cost,
                    "remaining_after_purchase": remaining,
                }
            )
        )
    return WizardVaultOptimizationReport(
        astral_acclaim_currency_id=astral_acclaim_currency_id,
        astral_acclaim_balance=balance,
        remaining_astral_acclaim=remaining,
        recommendations=planned_recommendations,
    )


def _rank_wizard_vault_rewards(
    seasons: list[WizardVaultSeason],
    astral_acclaim_balance: int,
) -> list[WizardVaultRewardRecommendation]:
    recommendations: list[WizardVaultRewardRecommendation] = []
    for season in seasons:
        for reward in season.rewards:
            if reward.astral_acclaim_cost <= 0:
                continue
            priority_score = _legendary_priority_score(reward)
            if priority_score <= 0:
                continue
            affordable_quantity = astral_acclaim_balance // reward.astral_acclaim_cost
            if reward.purchase_limit is not None:
                affordable_quantity = min(affordable_quantity, reward.purchase_limit)
            recommendations.append(
                WizardVaultRewardRecommendation(
                    season_id=season.id,
                    season_name=season.name,
                    reward_id=reward.id,
                    reward_name=reward.name,
                    reward_kind=reward.reward_kind,
                    astral_acclaim_cost=reward.astral_acclaim_cost,
                    purchase_limit=reward.purchase_limit,
                    priority_score=priority_score,
                    is_affordable=affordable_quantity > 0,
                    affordable_quantity=affordable_quantity,
                    recommended_quantity=0,
                    recommended_cost=0,
                    remaining_after_purchase=astral_acclaim_balance,
                    reason=_recommendation_reason(reward, astral_acclaim_balance),
                    source_url=reward.source_url,
                    tags=reward.tags,
                )
            )
    return sorted(
        recommendations,
        key=lambda recommendation: (
            -recommendation.priority_score,
            not recommendation.is_affordable,
            recommendation.astral_acclaim_cost,
            recommendation.reward_name,
        ),
    )


def _legendary_priority_score(reward: WizardVaultReward) -> int:
    score = {
        "starter_kit": 100,
        "legendary_component": 85,
        "item": 0,
        "currency": 0,
        "upgrade": 0,
    }[reward.reward_kind]
    tag_scores = {
        "legendary": 50,
        "starter-kit": 40,
        "legendary-component": 35,
        "mystic-clover": 30,
        "mystic-coin": 25,
        "clover": 30,
        "coin": 25,
        "material": 5,
    }
    return score + sum(tag_scores.get(_normalize_filter(tag), 0) for tag in reward.tags)


def _recommendation_reason(reward: WizardVaultReward, astral_acclaim_balance: int) -> str:
    tags = {_normalize_filter(tag) for tag in reward.tags}
    if reward.reward_kind == "starter_kit" or "starter-kit" in tags:
        reason = "Starter kit reward that can cover a precursor and weapon gift."
    elif reward.reward_kind == "legendary_component" or "legendary-component" in tags:
        reason = "Direct legendary crafting component."
    elif "mystic-clover" in tags or "clover" in tags:
        reason = "Mystic Clovers are a high-demand legendary crafting material."
    elif "mystic-coin" in tags or "coin" in tags:
        reason = "Mystic Coins are a high-demand legendary crafting material."
    else:
        reason = "Reward is tagged as legendary-relevant in the season data."

    if astral_acclaim_balance < reward.astral_acclaim_cost:
        missing = reward.astral_acclaim_cost - astral_acclaim_balance
        return f"{reason} Need {missing:,} more Astral Acclaim for one purchase."
    return reason


def _add_issue(
    report: WizardVaultValidationReport,
    severity: WizardVaultValidationSeverity,
    code: str,
    message: str,
    *,
    season_id: str | None = None,
    reward_id: str | None = None,
) -> None:
    report.issues.append(
        WizardVaultValidationIssue(
            severity=severity,
            code=code,
            message=message,
            season_id=season_id,
            reward_id=reward_id,
        )
    )


def _is_http_url(value: str) -> bool:
    return value.startswith(("https://", "http://"))


def _normalize_filter(value: str) -> str:
    return value.strip().lower().replace("_", "-")
