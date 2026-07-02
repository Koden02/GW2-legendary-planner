# GW2 Legendary Planner

GW2 Legendary Planner is a desktop-ready Python library and CLI for answering:

> What is the highest-value thing my Guild Wars 2 account can work on next?

The first milestone focuses on legendary crafting account analysis. The code is
structured as a reusable library first and a command-line tool second, so future
GUI, automation, and planner surfaces can reuse the same API loading, inventory,
and planning engines.

## Status

Phase 2 is complete. The project currently supports:

- Loading account data from local JSON exports or the authenticated Guild Wars 2 API.
- Flattening account-wide inventory from material storage, bank, shared inventory,
  character bags, character inventories, and character equipment.
- Producing account summaries with currency, character, crafting, legendary armory,
  and item-count totals.
- Producing a data-driven legendary focus report for high-signal legendary materials,
  wallet currencies, starter kits, and representative precursor entries.
- Evaluating all generation-one top-level legendary weapon recipes plus selected
  weapon-gift, shared, and API-verified crafting subrecipes with readiness
  percentage, missing requirements, acquisition hints, and dependency graph output.
- Exporting summary, inventory, focus, and recipe evaluation data as JSON or CSV.

The packaged recipe set is intentionally generation-one focused. Activity
planners, market pricing, shopping lists, and GUI work are planned for later
phases.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Installation

```powershell
uv sync --dev
```

## CLI

```powershell
uv run gw2planner analyze --input ./exports/
uv run gw2planner analyze --api-key $env:GW2_API_KEY
uv run gw2planner export inventory --input ./exports/ --format csv --output inventory.csv
uv run gw2planner export summary --input ./exports/ --format json
uv run gw2planner export focus --input ./exports/ --format csv
uv run gw2planner recipes list
uv run gw2planner recipes list --tag generation_1 --tag sword
uv run gw2planner recipes show legendary.twilight
uv run gw2planner recipes evaluate legendary.twilight --input ./exports/
uv run gw2planner recipes evaluate legendary.twilight --input ./exports/ --missing-only
uv run gw2planner recipes evaluate legendary.twilight --input ./exports/ --graph
uv run gw2planner recipes validate
uv run gw2planner doctor --input ./exports/
uv run gw2planner doctor --require-api-key
```

`--input` expects JSON files named after supported endpoints:

- `account.json`
- `account_wallet.json`
- `account_materials.json`
- `account_bank.json`
- `account_inventory.json`
- `account_legendaryarmory.json`
- `characters.json`

The loader also accepts common aliases such as `wallet.json`, `bank.json`, and
`characters_all.json`.

## Library Usage

```python
from pathlib import Path

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.legendary_focus import build_legendary_focus_report
from gw2_legendary_planner.reports.summary import build_account_summary

snapshot = LocalExportLoader(Path("exports")).load()
inventory = InventoryAggregator().aggregate(snapshot)
summary = build_account_summary(snapshot, inventory)
focus_report = build_legendary_focus_report(snapshot, inventory)
```

## Development

```powershell
uv sync --dev
uv run ruff check .
uv run pytest
uv run gw2planner recipes validate
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and
[docs/PLANNERS.md](docs/PLANNERS.md) for project structure, extension rules, and
developer workflows. See [docs/RECIPES.md](docs/RECIPES.md) for recipe data
scope and [docs/ROADMAP.md](docs/ROADMAP.md) for planned phases.
