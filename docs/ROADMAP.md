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

Intentionally deferred from Phase 2: dungeon gift planners, activity
optimization, trading-post or market pricing, shopping lists, and recommendation
scoring. Shopping lists and recommendation scoring are now handled by later
phase work; pricing is now starting in Phase 5 as an optional overlay.

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
automation, collection endpoint integration, and account-unlock endpoint
integration remain deferred until source data services exist for those concerns.

## Phase 4: Account Progression Planning - Complete

- Achievement planner.
- Collection planner.
- Daily planner.
- Weekly planner.
- Account progression score.
- "What should I do next?" recommendation engine.

Completed scope: account achievement export loading, data-defined achievement
progress reports, data-defined daily and weekly recurring task reports, account
progression scoring, and the first recommendation engine are implemented as a
composition layer over recipe readiness, achievement progress, activity
readiness, collection progress, recurring task progress, optional starter-kit
evaluations, and optional Wizard's Vault optimization data.

Post-Phase 4 refinement scope: connect richer source-backed achievement,
collection, daily, and weekly planner inputs. These should stay data-backed and
should not infer current rotating objectives without verifiable source data.

## Phase 5: Desktop Application - In Progress

- Desktop GUI.
- Live API synchronization.
- Shopping list generation.
- Automatic market price integration.
- Multi-account support.
- Plugin system.

Current scope: a desktop-ready browser dashboard is implemented as a GUI adapter
over existing account summary, focus, activity, progression score,
recommendation, and shopping-list outputs. It can be written as standalone HTML
or served locally with `gw2planner gui serve`. Served dashboards expose sync
status plus a refresh action for reloading account data from the selected source,
including inline refresh progress and failure details.
Price-free shopping-list generation is available from recipe effective costs and
can be exported as JSON or CSV. Optional shopping-list market price overlays can
fetch `/v2/commerce/prices` summaries for missing item requirements without
making recipes or recommendations price-aware. The dashboard can display those
price overlays when `--include-shopping-list-prices` is selected. Account
profile storage and profile-aware account loading are in place for local exports
or API-backed accounts.

Next scope: native packaging, richer live synchronization UX, fuller multi-account
profile UX, and plugin loading.
