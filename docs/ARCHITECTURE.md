# Architecture

GW2 Legendary Planner is organized as a library-first application. CLI, future
desktop UI, and future automation surfaces should call the same library services.

## Package Layout

- `api/` handles Guild Wars 2 API communication and local JSON export loading.
  It also owns reusable API-backed services such as item metadata and commerce
  price lookup.
- `models/` contains Pydantic models for API payloads and normalized snapshots.
- `inventory/` flattens account storage into account-wide item quantities and
  location records.
- `planner/` contains planner-specific data and logic. Legendary focus detection
  recipe evaluation, and activity readiness live here, not inside the inventory
  engine.
- `reports/` adapts domain results to Rich tables, CSV, and JSON.
- `cache/` provides local API response caching.
- `config/` reads settings and API key configuration.
- `diagnostics.py` contains doctor checks for local setup and export validity.
- `tests/` covers loader, inventory, summary, planner, and export behavior.

## Dependency Flow

```mermaid
flowchart TD
    CLI["Typer CLI"] --> API["api loaders and services"]
    CLI --> Reports["reports"]
    API --> Models["models"]
    API --> Cache["cache"]
    API --> Snapshot["AccountSnapshot"]
    Snapshot --> Inventory["inventory engine"]
    Inventory --> Planner["planner modules"]
    Snapshot --> Planner
    APIItems["ItemMetadataService"] --> Cache
    APIItems --> ItemModels["ItemMetadata"]
    APICommerce["CommercePriceService"] --> Cache
    APICommerce --> CommerceModels["CommercePrice"]
    Planner --> Reports
    Reports --> Output["Rich, JSON, CSV"]
    Diagnostics["doctor diagnostics"] --> API
    Diagnostics --> Config["config"]
```

The dependency direction should stay one-way:

1. API and local loaders create validated data models.
2. Inventory turns snapshots into neutral account item state.
3. Planner modules ask inventory and metadata services domain questions.
4. Reports format already-computed models.

## Boundaries

Inventory aggregation does not know about legendary recipes, item importance, or
recommendations. It only answers:

- Which item IDs exist on the account?
- How many exist?
- Where are they located?
- Which characters hold them?
- Which storage sources contain them?

Planner modules consume inventory and account snapshots to answer domain
questions. Reports consume planner outputs and summaries to format them for a
human or file.

## Local Export Validation

Local JSON exports are validated before they become an `AccountSnapshot`.
Validation catches:

- missing required endpoint exports
- malformed JSON
- wrong top-level payload shapes
- unsupported v1-style export filenames
- Pydantic schema failures

CLI commands catch `LocalExportError` and print fix-oriented messages instead of
tracebacks.

## Item Metadata

`ItemMetadataService` is a reusable API service for `/v2/items`.

It supports:

- `get_item(item_id)` for lazy single-item lookup
- `get_items(item_ids)` for batched lookup
- in-memory reuse during one process
- optional per-item local cache using `ApiCache`
- configurable cache expiration through the cache instance or constructor

The inventory engine stores item IDs and locations only. Metadata enrichment is a
separate service so future planners and UIs can opt in without changing
aggregation behavior.

## Commerce Pricing

`CommercePriceService` is a reusable API service for `/v2/commerce/prices`.

It supports:

- `get_price(item_id)` for lazy single-item lookup
- `get_prices(item_ids)` for batched lookup
- in-memory reuse during one process
- optional per-item local cache using `ApiCache`
- best-effort skipping of unpriced or unmarketable item ids

`planner/market.py` owns the optional shopping-list price overlay. Recipe data,
inventory aggregation, and recipe evaluation remain price-free. Market price
reports use current trading-post summaries to estimate missing item buy cost and
sell value, but recommendation ranking does not consume prices yet.

## Data-Driven Planning

Legendary focus items are stored in `src/gw2_legendary_planner/data/`.
Legendary recipes are stored in `src/gw2_legendary_planner/data/` and loaded
through repository/provider abstractions.
Legendary activity goals are stored in `src/gw2_legendary_planner/data/` and
evaluated against the same account snapshot and inventory engine.
Collection definitions are stored in `src/gw2_legendary_planner/data/` or loaded
from external JSON files and evaluated against neutral account state.

Recipe work follows this pattern:

1. Define validated data models in `planner/`.
2. Store recipe data as package data.
3. Evaluate recipes against `Inventory`, wallet currencies, and account state.
4. Return planner models that can be rendered by any UI.

The current packaged recipe set is intentionally generation-one focused. It
exists to validate the engine shape before broader recipe coverage, activity
planners, market pricing, and recommendation scoring are added.

## Recipe Engine

The recipe engine has three separable pieces:

- `RecipeProvider` loads recipe definitions from one source.
- `RecipeRepository` indexes recipes by recipe id and output item/currency.
- `RecipeEvaluator` evaluates a recipe against `AccountSnapshot` and `Inventory`.
- `planner/shopping_list.py` aggregates recipe effective costs into a
  price-free shopping list for one or more selected goals.
- `planner/market.py` can optionally enrich a shopping list with commerce
  prices without changing recipe evaluation.

Evaluation returns:

- readiness percentage
- effective missing requirement quantities
- recursive requirement evaluations
- a serializable dependency graph

The evaluator does not query market prices and does not make recommendations.
Those belong to later planner phases.

Shopping-list generation consumes `RecipeEvaluation.costs`. It does not
duplicate recipe traversal and it does not query trading-post or market prices.
Market enrichment is a separate opt-in pass over the finished shopping list.

## Activity Planners

Activity planners model account-progress tasks such as reward tracks and world
completion. The current Phase 3 planner evaluates readiness for Gift of Battle
and Gift of Exploration by checking inventory quantities and locations.

Activity planners return serializable status models with:

- required quantity
- available quantity
- missing quantity
- readiness percentage
- action text
- source URL and tags

Legendary Weapon Starter Kit evaluation is data-backed by a rotation catalog and
reuses the recipe evaluator with virtual kit-provided items. It does not query
trading-post prices.

Collection tracking is data-backed. Item, currency, and legendary armory targets
are evaluated today. Achievement, collection, and account-unlock targets are
represented as unsupported requirements until the matching account data sources
exist.

Wizard's Vault optimization is data-backed. It should not hardcode seasonal
availability in CLI code. Wizard's Vault seasonal reward data lives in
`src/gw2_legendary_planner/data/wizards_vault_seasons.json` or in external
source-verified JSON snapshots loaded through the reusable Wizard's Vault data
service. The optimizer ranks legendary-relevant rewards against the account's
Astral Acclaim balance. Price-derived value and current-season claims remain
outside the optimizer until source data services exist for those concerns.

## Progression Planning

Phase 4 progression planning composes existing planner outputs instead of
duplicating their logic. `planner/achievements.py` evaluates data-defined
achievement goals from `/v2/account/achievements`. `planner/recurring.py`
evaluates source-defined daily and weekly tasks against achievements, wallet
currencies, inventory items, or explicit manual placeholders. `planner/progression.py`
consumes recipe readiness, achievement progress, activity readiness, optional
collection progress, optional recurring task progress, optional starter-kit
evaluations, and optional Wizard's Vault optimization reports.

The progression layer returns:

- a weighted account progression score
- score components with explanatory details
- ranked recommendations for "what should I do next?"

The recommendation engine does not query market prices, live seasonal schedules,
or infer current daily/weekly objective rotations. Live feeds require dedicated
source data services before they should affect ranking.

## Adding New Planners

New planners should live in `planner/` or a planner-specific subpackage. A planner
should:

- accept `AccountSnapshot`, `Inventory`, and optional API services as inputs
- return Pydantic result models
- keep rendering out of planner code
- keep API calls behind service abstractions
- include fixture-based tests for common account states

Do not put planner-specific knowledge in `inventory/`, `api/local.py`, or report
exporters.

## GUI Layer

The Phase 5 GUI foundation lives under `gui/`. It adapts existing planner
outputs into a desktop-ready browser dashboard without moving business logic
into the presentation layer.

The current flow is:

```mermaid
flowchart LR
    Snapshot["AccountSnapshot"] --> Inventory["Inventory"]
    Inventory --> Planners["Planner reports"]
    Snapshot --> Planners
    Planners --> Payload["DashboardPayload"]
    Payload --> HTML["Standalone HTML dashboard"]
    HTML --> Server["Local preview server"]
```

`gui/dashboard.py` owns the dashboard view model and HTML rendering, including
optional shopping-list and shopping-list price views supplied by the CLI.
`gui/server.py` owns local preview serving and exposes `/api/status` plus
`/api/refresh` when a refresh provider is configured by `gw2planner gui serve`.
CLI commands may load account data and pass planner outputs into the GUI layer,
but GUI code should not call GW2 API endpoints, parse inventory sources,
evaluate recipes, or fetch commerce prices directly.
