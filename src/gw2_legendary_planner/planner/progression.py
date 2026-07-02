from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.achievements import AchievementGoalStatus
from gw2_legendary_planner.planner.activities import ActivityGoalStatus
from gw2_legendary_planner.planner.collections import CollectionProgress
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation, RecipeEvaluator
from gw2_legendary_planner.planner.recipe_repository import InMemoryRecipeRepository
from gw2_legendary_planner.planner.recurring import RecurringTaskStatus
from gw2_legendary_planner.planner.starter_kits import StarterKitSetEvaluation
from gw2_legendary_planner.planner.wizards_vault import WizardVaultOptimizationReport

RecommendationKind = Literal[
    "achievement",
    "activity",
    "collection",
    "daily",
    "recipe",
    "starter_kit",
    "weekly",
    "wizard_vault",
]
RecommendationPriority = Literal["high", "medium", "low"]


class ProgressionScoreComponent(BaseModel):
    """One weighted account-progression score component."""

    id: str
    name: str
    score_percent: float
    weight: float
    weighted_score: float
    detail: str


class ProgressionScoreReport(BaseModel):
    """Weighted account progression score across available planner data."""

    overall_score_percent: float
    components: list[ProgressionScoreComponent] = Field(default_factory=list)


class AccountRecommendation(BaseModel):
    """One ranked next-step recommendation."""

    id: str
    kind: RecommendationKind
    title: str
    priority: RecommendationPriority
    priority_score: float
    action: str
    reason: str
    source_id: str
    readiness_percent: float | None = None
    impact_percent: float | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)


class AccountProgressionReport(BaseModel):
    """Account progression score plus ranked recommendations."""

    score: ProgressionScoreReport
    recommendations: list[AccountRecommendation] = Field(default_factory=list)


def build_account_progression_report(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    repository: InMemoryRecipeRepository,
    *,
    achievement_statuses: list[AchievementGoalStatus] | None = None,
    activity_statuses: list[ActivityGoalStatus] | None = None,
    collection_progress: list[CollectionProgress] | None = None,
    recurring_tasks: list[RecurringTaskStatus] | None = None,
    starter_kit_evaluations: list[StarterKitSetEvaluation] | None = None,
    wizard_vault_report: WizardVaultOptimizationReport | None = None,
    max_recommendations: int = 10,
) -> AccountProgressionReport:
    """Build a reusable account progression report from existing planner outputs."""

    recipe_evaluations = _evaluate_top_level_legendaries(snapshot, inventory, repository)
    components = _score_components(
        recipe_evaluations=recipe_evaluations,
        achievement_statuses=achievement_statuses or [],
        activity_statuses=activity_statuses or [],
        collection_progress=collection_progress or [],
        recurring_tasks=recurring_tasks or [],
    )
    recommendations = [
        *_recipe_recommendations(recipe_evaluations),
        *_achievement_recommendations(achievement_statuses or []),
        *_activity_recommendations(activity_statuses or []),
        *_collection_recommendations(collection_progress or []),
        *_recurring_task_recommendations(recurring_tasks or []),
        *_starter_kit_recommendations(starter_kit_evaluations or []),
        *_wizard_vault_recommendations(wizard_vault_report),
    ]
    return AccountProgressionReport(
        score=ProgressionScoreReport(
            overall_score_percent=_weighted_average(components),
            components=components,
        ),
        recommendations=sorted(
            recommendations,
            key=lambda recommendation: (
                -recommendation.priority_score,
                recommendation.kind,
                recommendation.title,
            ),
        )[:max_recommendations],
    )


def _evaluate_top_level_legendaries(
    snapshot: AccountSnapshot,
    inventory: Inventory,
    repository: InMemoryRecipeRepository,
) -> list[RecipeEvaluation]:
    evaluator = RecipeEvaluator(repository)
    recipes = [
        recipe
        for recipe in repository.list_recipes()
        if recipe.id.startswith("legendary.")
        and {"legendary", "weapon"}.issubset({tag.lower() for tag in recipe.tags})
    ]
    return [evaluator.evaluate(recipe, snapshot, inventory) for recipe in recipes]


def _score_components(
    *,
    recipe_evaluations: list[RecipeEvaluation],
    achievement_statuses: list[AchievementGoalStatus],
    activity_statuses: list[ActivityGoalStatus],
    collection_progress: list[CollectionProgress],
    recurring_tasks: list[RecurringTaskStatus],
) -> list[ProgressionScoreComponent]:
    components: list[ProgressionScoreComponent] = []
    if recipe_evaluations:
        best = max(recipe_evaluations, key=lambda evaluation: evaluation.readiness_percent)
        components.append(
            ProgressionScoreComponent(
                id="legendary_recipe_readiness",
                name="Legendary recipe readiness",
                score_percent=best.readiness_percent,
                weight=0.5,
                weighted_score=round(best.readiness_percent * 0.5, 2),
                detail=f"Closest legendary: {best.recipe.name} at {best.readiness_percent:.2f}%.",
            )
        )
    if activity_statuses:
        score = _average([status.readiness_percent for status in activity_statuses])
        ready = sum(1 for status in activity_statuses if status.is_ready)
        components.append(
            ProgressionScoreComponent(
                id="activity_readiness",
                name="Activity readiness",
                score_percent=score,
                weight=0.3,
                weighted_score=round(score * 0.3, 2),
                detail=f"{ready}/{len(activity_statuses)} tracked activities are ready.",
            )
        )
    if achievement_statuses:
        score = _average([status.readiness_percent for status in achievement_statuses])
        complete = sum(1 for status in achievement_statuses if status.is_complete)
        components.append(
            ProgressionScoreComponent(
                id="achievement_progress",
                name="Achievement progress",
                score_percent=score,
                weight=0.15,
                weighted_score=round(score * 0.15, 2),
                detail=f"{complete}/{len(achievement_statuses)} tracked achievements are complete.",
            )
        )
    if collection_progress:
        score = _average([progress.readiness_percent for progress in collection_progress])
        complete = sum(1 for progress in collection_progress if progress.is_complete)
        components.append(
            ProgressionScoreComponent(
                id="collection_progress",
                name="Collection progress",
                score_percent=score,
                weight=0.15,
                weighted_score=round(score * 0.15, 2),
                detail=f"{complete}/{len(collection_progress)} tracked collections are complete.",
            )
        )
    trackable_recurring = [task for task in recurring_tasks if task.is_trackable]
    if trackable_recurring:
        score = _average([task.readiness_percent for task in trackable_recurring])
        complete = sum(1 for task in trackable_recurring if task.is_complete)
        components.append(
            ProgressionScoreComponent(
                id="recurring_task_progress",
                name="Recurring task progress",
                score_percent=score,
                weight=0.1,
                weighted_score=round(score * 0.1, 2),
                detail=(
                    f"{complete}/{len(trackable_recurring)} trackable recurring "
                    "tasks are complete."
                ),
            )
        )
    return components


def _recipe_recommendations(
    evaluations: list[RecipeEvaluation],
) -> list[AccountRecommendation]:
    if not evaluations:
        return []
    candidates = sorted(
        [evaluation for evaluation in evaluations if not evaluation.is_ready],
        key=lambda evaluation: (
            -evaluation.readiness_percent,
            _missing_entries(evaluation),
            evaluation.recipe.name,
        ),
    )
    if not candidates:
        ready = sorted(evaluations, key=lambda evaluation: evaluation.recipe.name)[0]
        return [
            _recommendation(
                id=f"recipe:{ready.recipe.id}",
                kind="recipe",
                title=f"Craft {ready.recipe.name}",
                priority_score=92,
                action=f"Run `gw2planner recipes evaluate {ready.recipe.id}` and craft it.",
                reason=f"{ready.recipe.name} is ready based on current effective costs.",
                source_id=ready.recipe.id,
                readiness_percent=ready.readiness_percent,
                tags=ready.recipe.tags,
            )
        ]
    best = candidates[0]
    missing = _missing_entries(best)
    return [
        _recommendation(
            id=f"recipe:{best.recipe.id}",
            kind="recipe",
            title=f"Work toward {best.recipe.name}",
            priority_score=min(60 + best.readiness_percent / 2, 94),
            action=f"Run `gw2planner recipes evaluate {best.recipe.id} --missing-only`.",
            reason=(
                f"{best.recipe.name} is the closest tracked legendary at "
                f"{best.readiness_percent:.2f}% readiness with {missing} missing entries."
            ),
            source_id=best.recipe.id,
            readiness_percent=best.readiness_percent,
            tags=best.recipe.tags,
        )
    ]


def _achievement_recommendations(
    statuses: list[AchievementGoalStatus],
) -> list[AccountRecommendation]:
    recommendations: list[AccountRecommendation] = []
    for status in statuses:
        if status.is_complete:
            continue
        missing = max(status.required_progress - status.current_progress, 0)
        recommendations.append(
            _recommendation(
                id=f"achievement:{status.id}",
                kind="achievement",
                title=f"Advance {status.name}",
                priority_score=80 - status.readiness_percent / 5,
                action=f"Work on achievement goal {status.achievement_id}.",
                reason=(
                    f"{status.name} is {status.readiness_percent:.2f}% complete; "
                    f"{missing:,} more progress needed."
                ),
                source_id=status.id,
                readiness_percent=status.readiness_percent,
                source_url=status.source_url,
                tags=status.tags,
            )
        )
    return recommendations


def _activity_recommendations(
    statuses: list[ActivityGoalStatus],
) -> list[AccountRecommendation]:
    recommendations: list[AccountRecommendation] = []
    for status in statuses:
        if status.is_ready:
            continue
        recommendations.append(
            _recommendation(
                id=f"activity:{status.id}",
                kind="activity",
                title=f"Complete {status.name}",
                priority_score=85 - status.readiness_percent / 4,
                action=status.action,
                reason=(
                    f"{status.name} is {status.readiness_percent:.2f}% ready; "
                    f"{status.missing_quantity:,} more needed."
                ),
                source_id=status.id,
                readiness_percent=status.readiness_percent,
                source_url=status.source_url,
                tags=status.tags,
            )
        )
    return recommendations


def _collection_recommendations(
    progress_entries: list[CollectionProgress],
) -> list[AccountRecommendation]:
    recommendations: list[AccountRecommendation] = []
    for progress in progress_entries:
        if progress.is_complete:
            continue
        missing = sum(1 for requirement in progress.requirements if not requirement.is_complete)
        unsupported = progress.unsupported_requirements
        priority_score = 78 - progress.readiness_percent / 5
        if unsupported:
            priority_score -= 10
        recommendations.append(
            _recommendation(
                id=f"collection:{progress.id}",
                kind="collection",
                title=f"Advance {progress.name}",
                priority_score=priority_score,
                action=f"Review `gw2planner activities collections --collection {progress.id}`.",
                reason=(
                    f"{progress.name} is {progress.readiness_percent:.2f}% complete with "
                    f"{missing} incomplete requirements and {unsupported} unsupported."
                ),
                source_id=progress.id,
                readiness_percent=progress.readiness_percent,
                source_url=progress.source_url,
                tags=progress.tags,
            )
        )
    return recommendations


def _recurring_task_recommendations(
    statuses: list[RecurringTaskStatus],
) -> list[AccountRecommendation]:
    recommendations: list[AccountRecommendation] = []
    for status in statuses:
        if status.is_complete:
            continue
        kind: RecommendationKind = "daily" if status.period == "daily" else "weekly"
        priority_score = 72 if status.period == "daily" else 68
        priority_score -= status.readiness_percent / 5 if status.is_trackable else 8
        recommendations.append(
            _recommendation(
                id=f"{status.period}:{status.id}",
                kind=kind,
                title=status.name,
                priority_score=priority_score,
                action=status.action,
                reason=_recurring_reason(status),
                source_id=status.id,
                readiness_percent=status.readiness_percent if status.is_trackable else None,
                source_url=status.source_url,
                tags=status.tags,
            )
        )
    return recommendations


def _starter_kit_recommendations(
    evaluations: list[StarterKitSetEvaluation],
) -> list[AccountRecommendation]:
    recommendations: list[AccountRecommendation] = []
    for evaluation in evaluations:
        if not evaluation.options:
            continue
        option = evaluation.options[0]
        if option.readiness_gain_percent <= 0:
            continue
        recommendations.append(
            _recommendation(
                id=f"starter-kit:{evaluation.set_id}:{option.legendary_recipe_id}",
                kind="starter_kit",
                title=f"Consider {option.legendary_name} from {evaluation.name}",
                priority_score=min(72 + option.readiness_gain_percent, 96),
                action=(
                    f"If evaluating {evaluation.name}, choose {option.legendary_name} "
                    f"with {option.recommended_gift_choice}."
                ),
                reason=(
                    f"This kit improves readiness by {option.readiness_gain_percent:.2f} "
                    f"points and covers {', '.join(option.covered_items)}."
                ),
                source_id=evaluation.set_id,
                readiness_percent=option.readiness_after_percent,
                impact_percent=option.readiness_gain_percent,
                source_url=evaluation.source_url,
                tags=["starter_kit", "legendary"],
            )
        )
    return recommendations


def _wizard_vault_recommendations(
    report: WizardVaultOptimizationReport | None,
) -> list[AccountRecommendation]:
    if report is None:
        return []
    recommendations: list[AccountRecommendation] = []
    for recommendation in report.recommendations:
        if recommendation.recommended_quantity <= 0:
            continue
        recommendations.append(
            _recommendation(
                id=f"wizard-vault:{recommendation.season_id}:{recommendation.reward_id}",
                kind="wizard_vault",
                title=f"Buy {recommendation.reward_name}",
                priority_score=min(82 + recommendation.priority_score / 10, 98),
                action=(
                    f"Buy {recommendation.recommended_quantity} for "
                    f"{recommendation.recommended_cost:,} Astral Acclaim."
                ),
                reason=recommendation.reason,
                source_id=recommendation.reward_id,
                impact_percent=None,
                source_url=recommendation.source_url,
                tags=recommendation.tags,
            )
        )
    return recommendations


def _recurring_reason(status: RecurringTaskStatus) -> str:
    if not status.is_trackable:
        return "This recurring task is source-defined but must be tracked manually."
    return (
        f"{status.name} is {status.readiness_percent:.2f}% complete; "
        f"{status.missing_quantity:,} more progress needed."
    )


def _recommendation(
    *,
    id: str,
    kind: RecommendationKind,
    title: str,
    priority_score: float,
    action: str,
    reason: str,
    source_id: str,
    readiness_percent: float | None = None,
    impact_percent: float | None = None,
    source_url: str | None = None,
    tags: list[str] | None = None,
) -> AccountRecommendation:
    rounded_priority = round(priority_score, 2)
    return AccountRecommendation(
        id=id,
        kind=kind,
        title=title,
        priority=_priority_label(rounded_priority),
        priority_score=rounded_priority,
        action=action,
        reason=reason,
        source_id=source_id,
        readiness_percent=readiness_percent,
        impact_percent=impact_percent,
        source_url=source_url,
        tags=tags or [],
    )


def _weighted_average(components: list[ProgressionScoreComponent]) -> float:
    total_weight = sum(component.weight for component in components)
    if not total_weight:
        return 0.0
    return round(sum(component.weighted_score for component in components) / total_weight, 2)


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _missing_entries(evaluation: RecipeEvaluation) -> int:
    return sum(1 for cost in evaluation.costs if cost.missing_quantity > 0)


def _priority_label(priority_score: float) -> RecommendationPriority:
    if priority_score >= 85:
        return "high"
    if priority_score >= 60:
        return "medium"
    return "low"
