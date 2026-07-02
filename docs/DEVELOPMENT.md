# Development

## Setup

```powershell
uv sync --dev
```

This project targets Python 3.13+.

## Checks

```powershell
uv run ruff check .
uv run pytest
uv run gw2planner recipes validate
uv run gw2planner activities wizard-vault-validate
```

If `uv` is installed but not on PATH in the active shell, use:

```powershell
py -3.13 -m uv run ruff check .
py -3.13 -m uv run pytest
py -3.13 -m uv run gw2planner recipes validate
py -3.13 -m uv run gw2planner activities wizard-vault-validate
```

## Continuous Integration

CI runs on pushes to `main` and on every pull request. The workflow:

1. Checks out the repository.
2. Installs Python 3.13.
3. Installs and caches `uv`.
4. Runs `uv sync --dev`.
5. Runs `uv run ruff check .`.
6. Runs `uv run pytest`.
7. Runs `uv run gw2planner recipes validate`.
8. Runs `uv run gw2planner activities wizard-vault-validate`.

The workflow file is `.github/workflows/ci.yml`.

## Local Fixture Analysis

```powershell
uv run gw2planner analyze --input tests/fixtures/exports
uv run gw2planner export inventory --input tests/fixtures/exports --format csv
uv run gw2planner export summary --input tests/fixtures/exports --format json
uv run gw2planner export focus --input tests/fixtures/exports --format csv
uv run gw2planner recipes list
uv run gw2planner recipes list --tag generation_1 --tag weapon
uv run gw2planner recipes evaluate legendary.twilight --input tests/fixtures/exports
uv run gw2planner recipes evaluate legendary.twilight --input tests/fixtures/exports --missing-only
uv run gw2planner recipes shopping-list legendary.bolt legendary.twilight --input tests/fixtures/exports
uv run gw2planner recipes validate
uv run gw2planner activities report --input tests/fixtures/exports
uv run gw2planner activities collections --input tests/fixtures/exports --data tests/fixtures/collections/sample_collections.json
uv run gw2planner export activities --input tests/fixtures/exports --format csv
uv run gw2planner export collections --input tests/fixtures/exports --data tests/fixtures/collections/sample_collections.json --format csv
uv run gw2planner activities starter-kits --input tests/fixtures/exports --set 1
uv run gw2planner export starter-kits --input tests/fixtures/exports --set 1 --format csv
uv run gw2planner activities wizard-vault
uv run gw2planner activities wizard-vault --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner activities wizard-vault-optimize --input tests/fixtures/exports --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner activities wizard-vault-validate --data tests/fixtures/wizards_vault/sample_season.json
uv run gw2planner progress achievements --input tests/fixtures/exports --data tests/fixtures/achievements/sample_achievements.json
uv run gw2planner progress dailies --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress weeklies --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress score --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json
uv run gw2planner progress recommend --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --wizard-vault-data tests/fixtures/wizards_vault/sample_season.json --starter-kit-set 1
uv run gw2planner export wizard-vault --data tests/fixtures/wizards_vault/sample_season.json --format json
uv run gw2planner export wizard-vault-optimization --input tests/fixtures/exports --data tests/fixtures/wizards_vault/sample_season.json --format csv
uv run gw2planner export achievements --input tests/fixtures/exports --data tests/fixtures/achievements/sample_achievements.json --format csv
uv run gw2planner export recurring --input tests/fixtures/exports --data tests/fixtures/recurring/sample_tasks.json --format csv
uv run gw2planner export progression --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --format json
uv run gw2planner export shopping-list legendary.bolt --input tests/fixtures/exports --format csv
uv run gw2planner gui build --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --shopping-list-recipe legendary.bolt --output gw2planner-dashboard.html
uv run gw2planner gui serve --input tests/fixtures/exports --achievements-data tests/fixtures/achievements/sample_achievements.json --collections-data tests/fixtures/collections/sample_collections.json --recurring-data tests/fixtures/recurring/sample_tasks.json --shopping-list-recipe legendary.bolt --port 8765
uv run gw2planner doctor --input tests/fixtures/exports
```

## API Key

Use one of:

```powershell
uv run gw2planner analyze --api-key "<key>"
$env:GW2PLANNER_API_KEY = "<key>"
uv run gw2planner analyze
```

The key needs permission for the account endpoints used by this milestone:

- account
- wallet
- progression, for account achievements
- inventories
- characters
- unlocks, if future planners add unlock analysis

## Coding Standards

- Keep modules library-first. CLI code should orchestrate, not own domain logic.
- Keep inventory neutral. It should only answer quantity, location, character, and
  storage-source questions.
- Keep planner logic out of report exporters.
- Prefer Pydantic models for data crossing package boundaries.
- Prefer typed, explicit errors with friendly CLI handling.
- Add tests for successful behavior and the most likely user-facing failure mode.
- Use Ruff before committing.

## Adding Planner Data

Keep planner data out of `inventory/`.

For new legendary focus items, add entries to
`src/gw2_legendary_planner/data/legendary_focus_items.json` and add tests that
prove the planner detects those entries from an `Inventory` or wallet snapshot.

For recipes, add models and evaluation logic under `planner/`, recipe data under
`data/`, then evaluate them against the shared inventory engine. See
`docs/RECIPES.md` for data-source rules.

## Adding Recipe Data

Recipe JSON lives in `src/gw2_legendary_planner/data/legendary_recipes.json`.
Keep entries small, explicit, and source-verifiable:

- use stable item or currency IDs
- include display names for human-facing output
- tag generation, category, and planner relevance
- include source-verifiable acquisition hints for stable terminal requirements
- add tests for repository lookup and evaluation behavior
- run `gw2planner recipes validate`

Do not add market-price assumptions to recipe data. Price integration belongs to
a later phase.

## Adding Activity Planner Data

Activity planner definitions live in
`src/gw2_legendary_planner/data/activity_goals.json`.
Collection definitions live in
`src/gw2_legendary_planner/data/collection_goals.json`.
Starter-kit set definitions live in
`src/gw2_legendary_planner/data/starter_kit_sets.json`.
Wizard's Vault seasonal reward definitions live in
`src/gw2_legendary_planner/data/wizards_vault_seasons.json`.
External source-verified season snapshots can be loaded with
`--data ./wizard-vault-season.json` and should use the same schema as packaged
data.

- use stable item, currency, achievement, collection, or account-unlock IDs
- include action text that tells the user what activity produces the target
- include source URLs for human-verifiable data
- keep seasonal Wizard's Vault availability data separate from planner code
- add tests for ready and missing account states

Starter-kit evaluation should keep using recipe definitions and virtual
kit-provided inventory instead of duplicating recipe requirements.

Collection tracking should stay data-defined and source-verifiable. Inventory,
wallet, and legendary armory targets are supported now. Achievement, collection,
and account-unlock targets should remain explicit unsupported requirements until
the matching API loader inputs exist.

Wizard's Vault seasonal data must include source URLs and last-verified dates.
Current-season data is treated as invalid if it is stale.
Wizard's Vault optimization uses source-provided reward tags and the account's
Astral Acclaim wallet balance. Do not add price-derived value claims until the
market data phase exists.

## Adding Progression Recommendations

Progression recommendations live in `planner/progression.py`.

- compose existing planner outputs instead of re-implementing their checks
- keep recommendation reasons explicit and source-limited
- do not rank by market price until market data services exist
- require caller-provided data for seasonal or rotating content
- add tests for score components, ranking, and CLI/export output
