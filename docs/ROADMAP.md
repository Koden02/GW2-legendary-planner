# Roadmap

## Phase 1: Foundation - Complete

- API loader for local JSON exports and direct API access.
- Account-wide inventory aggregation with location tracking.
- Account summary report.
- Legendary focus report for high-signal components.
- JSON, CSV, and Rich terminal output.
- CLI, tests, fixture data, and developer documentation.

## Phase 2: Legendary Recipe Planning - Complete

- Legendary recipe database.
- Effective crafting cost.
- Legendary readiness percentage.
- Recipe dependency graph.

Completed scope: recipe engine, repository/provider abstractions, dependency
graph model, readiness evaluation, all generation-one top-level legendary weapon
recipes, generation-one weapon-specific Mystic Forge gift recipes, selected
shared subrecipes, API-verified shared crafting gift/component recipes, recipe
data validation, CLI recipe reports, and source-context acquisition hints for
high-signal terminal requirements.

Intentionally deferred: dungeon gift planners, activity optimization,
trading-post or market pricing, shopping lists, and recommendation scoring.
Those belong to later phases.

## Phase 3: Legendary Activity Planners - Complete

- Wizard's Vault optimization.
- Starter Kit optimizer.
- Gift of Exploration planner.
- Gift of Battle planner.
- Collection tracking.

Current scope: implemented the activity planner model, packaged activity-goal
definitions, Rich/CSV/JSON reporting, readiness planners for Gift of Battle and
Gift of Exploration, a Legendary Weapon Starter Kit rotation catalog, and
account-aware starter-kit set evaluation. Wizard's Vault seasonal reward data
models, external JSON loading, reporting, validation, and an Astral
Acclaim-based legendary reward optimizer are also in place, with no current
seasonal reward claims packaged yet. Collection/checklist tracking is implemented
for item, currency, and legendary armory targets, with unsupported future target
kinds reported explicitly.

Deferred scope: Wizard's Vault price-derived value, current-season availability
automation, achievement endpoint integration, and account-unlock endpoint
integration remain deferred until source data services exist for those concerns.

## Phase 4: Account Progression Planning

- Achievement planner.
- Collection planner.
- Daily planner.
- Weekly planner.
- Account progression score.
- "What should I do next?" recommendation engine.

## Phase 5: Desktop Application

- Desktop GUI.
- Live API synchronization.
- Shopping list generation.
- Automatic market price integration.
- Multi-account support.
- Plugin system.
