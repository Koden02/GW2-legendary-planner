# Planner Extension Guide

Planner modules answer account-progression questions on top of shared account
state. They should not load API data, parse local exports, or render output.

## Inputs

Use these stable inputs:

- `AccountSnapshot` for account, wallet, character, and armory data.
- `Inventory` for account-wide item quantities and locations.
- `ItemMetadataService` when item names, rarity, type, icon, or flags are needed.
- Future repositories such as `RecipeRepository` for planner-specific data.

## Outputs

Return Pydantic models from planner code. Report modules, CLI commands, and
future GUI screens should format those models separately.

## Recipe Engine Preparation

Phase 2 should build on these interfaces in `planner/recipes.py`:

- `RecipeRequirement`
- `AcquisitionHint`
- `Recipe`
- `RecipeProvider`
- `RecipeRepository`
- `Goal`
- `DependencyNode`

Recipe evaluation now lives in `planner/recipe_evaluator.py`. It consumes the
repository contracts and returns readiness, missing requirements, and a dependency
graph. Recommendation scoring should still be added separately later.
Acquisition hints are carried through effective-cost output as source context,
but they are not treated as planner recommendations.

Current recipe commands:

```powershell
uv run gw2planner recipes list
uv run gw2planner recipes list --tag weapon_gift
uv run gw2planner recipes show legendary.twilight
uv run gw2planner recipes evaluate legendary.twilight --input tests/fixtures/exports
uv run gw2planner recipes evaluate legendary.twilight --input tests/fixtures/exports --missing-only
uv run gw2planner recipes evaluate legendary.twilight --input tests/fixtures/exports --graph
```

## New Planner Checklist

1. Define result models.
2. Accept `AccountSnapshot` and `Inventory` as inputs.
3. Add optional service dependencies explicitly.
4. Keep static planner data under `data/` or a planner-specific data package.
5. Add fixture data that covers present, missing, and malformed account states.
6. Add report/export adapters only after planner models are stable.
