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

## Activity Planner Foundation

Phase 3 activity planners live in focused modules under `planner/`. They use
data definitions and the shared account snapshot/inventory engine.

Current activity commands:

```powershell
uv run gw2planner activities report --input tests/fixtures/exports
uv run gw2planner activities report --input tests/fixtures/exports --tag wvw
uv run gw2planner activities collections --input tests/fixtures/exports --data tests/fixtures/collections/sample_collections.json
uv run gw2planner activities gift-of-battle --input tests/fixtures/exports
uv run gw2planner activities gift-of-exploration --input tests/fixtures/exports
uv run gw2planner activities starter-kits --input tests/fixtures/exports --set 1
uv run gw2planner activities wizard-vault
uv run gw2planner activities wizard-vault --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner activities wizard-vault-optimize --input tests/fixtures/exports --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner activities wizard-vault-validate --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner export activities --input tests/fixtures/exports --format csv
uv run gw2planner export collections --input tests/fixtures/exports --data tests/fixtures/collections/sample_collections.json --format csv
uv run gw2planner export starter-kits --input tests/fixtures/exports --set 1 --format csv
uv run gw2planner export wizard-vault --data tests/fixtures/wizards_vault/sample_season.json --format json
uv run gw2planner export wizard-vault-optimization --input tests/fixtures/exports --data tests/fixtures/wizards_vault/sample_season.json --format csv
```

Starter-kit evaluation reuses the recipe evaluator with virtual kit-provided
items, so recipe requirements stay in one place.

Collection tracking uses data-defined requirement lists and the shared inventory,
wallet, and legendary armory state. Unsupported future target kinds are reported
in output rather than hidden.

Wizard's Vault optimizers should reuse this reporting shape but load seasonal
data from source-verifiable data files or services. The current CLI supports
external JSON snapshots through `--data` and ranks legendary-relevant rewards
against the account's Astral Acclaim balance. Do not encode current seasonal
offerings directly in command handlers.

## Progression Planner

Phase 4 provides a composition layer in `planner/progression.py`. It reuses
existing planner outputs and emits a weighted progression score plus ranked
recommendations.

```powershell
uv run gw2planner progress achievements --input tests/fixtures/exports --data tests/fixtures/achievements/sample_achievements.json
uv run gw2planner progress dailies --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress weeklies --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress score --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress recommend --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --wizard-vault-data tests/fixtures/wizards_vault/sample_season.json --starter-kit-set 1
uv run gw2planner export achievements --input tests/fixtures/exports --data tests/fixtures/achievements/sample_achievements.json --format csv
uv run gw2planner export recurring --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json --format csv
uv run gw2planner export progression --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --format json
```

Recommendation ranking is intentionally source-limited. It can use recipe
readiness, achievements, activities, collections, recurring daily/weekly tasks,
starter-kit set evaluations that the caller chooses, and Wizard's Vault season
data that the caller provides. It does not rank by trading-post value,
unverified current seasonal availability, or inferred live daily/weekly
rotations.

## New Planner Checklist

1. Define result models.
2. Accept `AccountSnapshot` and `Inventory` as inputs.
3. Add optional service dependencies explicitly.
4. Keep static planner data under `data/` or a planner-specific data package.
5. Add fixture data that covers present, missing, and malformed account states.
6. Add report/export adapters only after planner models are stable.
