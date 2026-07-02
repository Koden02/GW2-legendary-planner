from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.planner.activities import ActivityGoalStatus
from gw2_legendary_planner.planner.collections import CollectionProgress
from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation
from gw2_legendary_planner.planner.recipe_validator import RecipeValidationReport
from gw2_legendary_planner.planner.recipes import Recipe
from gw2_legendary_planner.planner.starter_kits import StarterKitSetEvaluation
from gw2_legendary_planner.planner.wizards_vault import (
    WizardVaultOptimizationReport,
    WizardVaultSeason,
    WizardVaultValidationReport,
)
from gw2_legendary_planner.reports.summary import AccountSummary


def model_to_json(data: BaseModel | Iterable[BaseModel]) -> str:
    if isinstance(data, BaseModel):
        return data.model_dump_json(indent=2)
    return json.dumps([entry.model_dump(mode="json") for entry in data], indent=2)


def write_json(path: Path, data: BaseModel | Iterable[BaseModel] | dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        if isinstance(data, BaseModel):
            handle.write(data.model_dump_json(indent=2))
        elif isinstance(data, dict):
            json.dump(data, handle, indent=2, sort_keys=True)
        else:
            json.dump([entry.model_dump(mode="json") for entry in data], handle, indent=2)
        handle.write("\n")


def inventory_rows(inventory: Inventory) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for item in sorted(inventory.items.values(), key=lambda entry: entry.item_id):
        rows.append(
            {
                "item_id": item.item_id,
                "quantity": item.quantity,
                "locations": "; ".join(
                    _format_location(location.model_dump(exclude_none=True))
                    for location in item.locations
                ),
            }
        )
    return rows


def focus_rows(entries: Iterable[FocusEntry]) -> list[dict[str, str | int]]:
    return [
        {
            "id": entry.id,
            "kind": entry.kind,
            "name": entry.name,
            "category": entry.category,
            "quantity": entry.quantity,
            "locations": "; ".join(
                _format_location(location.model_dump(exclude_none=True))
                for location in entry.locations
            ),
            "note": entry.note or "",
            "tags": ",".join(entry.tags),
        }
        for entry in entries
    ]


def summary_rows(summary: AccountSummary) -> list[dict[str, str | int]]:
    return [
        {"metric": "account_name", "value": summary.account_name or ""},
        {"metric": "gold", "value": str(summary.gold)},
        {"metric": "gems", "value": summary.gems},
        {"metric": "characters", "value": len(summary.characters)},
        {"metric": "crafting_disciplines", "value": len(summary.crafting_disciplines)},
        {"metric": "legendary_armory_entries", "value": summary.legendary_armory_entries},
        {"metric": "legendary_armory_total", "value": summary.legendary_armory_total},
        {"metric": "unique_item_count", "value": summary.unique_item_count},
        {"metric": "total_item_count", "value": summary.total_item_count},
    ]


def activity_rows(statuses: Iterable[ActivityGoalStatus]) -> list[dict[str, str | int | float]]:
    return [
        {
            "id": status.id,
            "name": status.name,
            "category": status.category,
            "activity_kind": status.activity_kind,
            "target_kind": status.target_kind,
            "target_id": status.target_id,
            "required_quantity": status.required_quantity,
            "available_quantity": status.available_quantity,
            "missing_quantity": status.missing_quantity,
            "readiness_percent": status.readiness_percent,
            "is_ready": "yes" if status.is_ready else "no",
            "action": status.action,
            "locations": "; ".join(
                _format_location(location.model_dump(exclude_none=True))
                for location in status.locations
            ),
            "note": status.note or "",
            "source_url": status.source_url or "",
            "tags": ",".join(status.tags),
        }
        for status in statuses
    ]


def collection_rows(
    progress_entries: Iterable[CollectionProgress],
) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for progress in progress_entries:
        if not progress.requirements:
            rows.append(
                {
                    "collection_id": progress.id,
                    "collection_name": progress.name,
                    "category": progress.category,
                    "readiness_percent": progress.readiness_percent,
                    "is_complete": "yes" if progress.is_complete else "no",
                    "completed_requirements": progress.completed_requirements,
                    "total_requirements": progress.total_requirements,
                    "unsupported_requirements": progress.unsupported_requirements,
                    "requirement_id": "",
                    "requirement_name": "",
                    "target_kind": "",
                    "target_id": "",
                    "required_quantity": "",
                    "available_quantity": "",
                    "missing_quantity": "",
                    "requirement_ready": "",
                    "supported": "",
                    "locations": "",
                    "note": "",
                    "source_url": progress.source_url,
                    "tags": ",".join(progress.tags),
                }
            )
            continue
        for requirement in progress.requirements:
            rows.append(
                {
                    "collection_id": progress.id,
                    "collection_name": progress.name,
                    "category": progress.category,
                    "readiness_percent": progress.readiness_percent,
                    "is_complete": "yes" if progress.is_complete else "no",
                    "completed_requirements": progress.completed_requirements,
                    "total_requirements": progress.total_requirements,
                    "unsupported_requirements": progress.unsupported_requirements,
                    "requirement_id": requirement.id,
                    "requirement_name": requirement.name,
                    "target_kind": requirement.target_kind,
                    "target_id": requirement.target_id,
                    "required_quantity": requirement.required_quantity,
                    "available_quantity": requirement.available_quantity,
                    "missing_quantity": requirement.missing_quantity,
                    "requirement_ready": "yes" if requirement.is_complete else "no",
                    "supported": "yes" if requirement.is_supported else "no",
                    "locations": "; ".join(
                        _format_location(location.model_dump(exclude_none=True))
                        for location in requirement.locations
                    ),
                    "note": requirement.note or "",
                    "source_url": requirement.source_url or progress.source_url,
                    "tags": ",".join([*progress.tags, *requirement.tags]),
                }
            )
    return rows


def recipe_rows(recipes: Iterable[Recipe]) -> list[dict[str, str | int]]:
    return [
        {
            "id": recipe.id,
            "name": recipe.name,
            "output_kind": recipe.output_kind,
            "output_id": recipe.output_id,
            "output_quantity": recipe.output_quantity,
            "requirements": len(recipe.requirements),
            "tags": ",".join(recipe.tags),
        }
        for recipe in recipes
    ]


def starter_kit_rows(
    evaluations: Iterable[StarterKitSetEvaluation],
) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for evaluation in evaluations:
        for option in evaluation.options:
            rows.append(
                {
                    "set_id": evaluation.set_id,
                    "set_number": evaluation.set_number,
                    "set_name": evaluation.name,
                    "astral_acclaim_cost": evaluation.astral_acclaim_cost,
                    "legendary_recipe_id": option.legendary_recipe_id,
                    "legendary_name": option.legendary_name,
                    "readiness_before_percent": option.readiness_before_percent,
                    "readiness_after_percent": option.readiness_after_percent,
                    "readiness_gain_percent": option.readiness_gain_percent,
                    "missing_before": option.missing_before,
                    "missing_after": option.missing_after,
                    "recommended_gift_choice": option.recommended_gift_choice,
                    "covered_items": "; ".join(option.covered_items),
                    "source_url": option.source_url,
                }
            )
    return rows


def wizard_vault_rows(
    seasons: Iterable[WizardVaultSeason],
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for season in seasons:
        if not season.rewards:
            rows.append(
                {
                    "season_id": season.id,
                    "season_name": season.name,
                    "status": season.status,
                    "starts_on": season.starts_on.isoformat() if season.starts_on else "",
                    "ends_on": season.ends_on.isoformat() if season.ends_on else "",
                    "season_last_verified": season.last_verified.isoformat(),
                    "reward_id": "",
                    "reward_name": "",
                    "reward_kind": "",
                    "astral_acclaim_cost": "",
                    "purchase_limit": "",
                    "item_id": "",
                    "currency_id": "",
                    "reward_last_verified": "",
                    "source_url": season.source_url,
                    "tags": "",
                    "note": "",
                }
            )
            continue
        for reward in season.rewards:
            rows.append(
                {
                    "season_id": season.id,
                    "season_name": season.name,
                    "status": season.status,
                    "starts_on": season.starts_on.isoformat() if season.starts_on else "",
                    "ends_on": season.ends_on.isoformat() if season.ends_on else "",
                    "season_last_verified": season.last_verified.isoformat(),
                    "reward_id": reward.id,
                    "reward_name": reward.name,
                    "reward_kind": reward.reward_kind,
                    "astral_acclaim_cost": reward.astral_acclaim_cost,
                    "purchase_limit": reward.purchase_limit or "",
                    "item_id": reward.item_id or "",
                    "currency_id": reward.currency_id or "",
                    "reward_last_verified": reward.last_verified.isoformat(),
                    "source_url": reward.source_url,
                    "tags": ",".join(reward.tags),
                    "note": reward.note or "",
                }
            )
    return rows


def wizard_vault_validation_rows(
    report: WizardVaultValidationReport,
) -> list[dict[str, str | int]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "season_id": issue.season_id or "",
            "reward_id": issue.reward_id or "",
            "message": issue.message,
        }
        for issue in report.issues
    ]


def wizard_vault_optimization_rows(
    report: WizardVaultOptimizationReport,
) -> list[dict[str, str | int]]:
    return [
        {
            "season_id": recommendation.season_id,
            "season_name": recommendation.season_name,
            "reward_id": recommendation.reward_id,
            "reward_name": recommendation.reward_name,
            "reward_kind": recommendation.reward_kind,
            "astral_acclaim_cost": recommendation.astral_acclaim_cost,
            "purchase_limit": recommendation.purchase_limit or "",
            "priority_score": recommendation.priority_score,
            "is_affordable": "yes" if recommendation.is_affordable else "no",
            "affordable_quantity": recommendation.affordable_quantity,
            "recommended_quantity": recommendation.recommended_quantity,
            "recommended_cost": recommendation.recommended_cost,
            "remaining_after_purchase": recommendation.remaining_after_purchase,
            "reason": recommendation.reason,
            "source_url": recommendation.source_url,
            "tags": ",".join(recommendation.tags),
        }
        for recommendation in report.recommendations
    ]


def recipe_cost_rows(
    evaluation: RecipeEvaluation,
    *,
    missing_only: bool = False,
) -> list[dict[str, str | int | float]]:
    return [
        {
            "kind": cost.kind,
            "id": cost.id,
            "name": cost.name or "",
            "required_quantity": cost.required_quantity,
            "available_quantity": cost.available_quantity,
            "missing_quantity": cost.missing_quantity,
            "readiness_percent": round(cost.readiness * 100, 2),
            "acquisition": cost.acquisition.label if cost.acquisition else "",
            "acquisition_kind": cost.acquisition.kind if cost.acquisition else "",
            "acquisition_note": cost.acquisition.note if cost.acquisition else "",
            "source_url": cost.acquisition.source_url if cost.acquisition else "",
        }
        for cost in evaluation.costs
        if not missing_only or cost.missing_quantity > 0
    ]


def recipe_graph_rows(evaluation: RecipeEvaluation) -> list[dict[str, str | int]]:
    nodes_by_id = {node.id: node for node in evaluation.dependency_graph.nodes}
    return [
        {
            "parent": nodes_by_id[edge.parent_id].label,
            "child": nodes_by_id[edge.child_id].label,
            "child_kind": nodes_by_id[edge.child_id].kind,
            "quantity": nodes_by_id[edge.child_id].quantity,
            "status": nodes_by_id[edge.child_id].status,
        }
        for edge in evaluation.dependency_graph.edges
    ]


def recipe_validation_rows(report: RecipeValidationReport) -> list[dict[str, str | int]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "recipe_id": issue.recipe_id or "",
            "requirement_index": (
                issue.requirement_index if issue.requirement_index is not None else ""
            ),
            "message": issue.message,
        }
        for issue in report.issues
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(rows_to_csv(rows))


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _format_location(location: dict[str, Any]) -> str:
    source = location.pop("source")
    quantity = location.pop("quantity")
    details = ", ".join(f"{key}={value}" for key, value in location.items())
    return f"{source} x{quantity}" + (f" ({details})" if details else "")
