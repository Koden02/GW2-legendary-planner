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
```

If `uv` is installed but not on PATH in the active shell, use:

```powershell
py -3.13 -m uv run ruff check .
py -3.13 -m uv run pytest
py -3.13 -m uv run gw2planner recipes validate
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
uv run gw2planner recipes validate
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
