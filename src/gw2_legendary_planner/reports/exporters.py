from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from gw2_legendary_planner.inventory.models import Inventory
from gw2_legendary_planner.planner.legendary_focus import FocusEntry
from gw2_legendary_planner.planner.recipe_evaluator import RecipeEvaluation
from gw2_legendary_planner.planner.recipe_validator import RecipeValidationReport
from gw2_legendary_planner.planner.recipes import Recipe
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
