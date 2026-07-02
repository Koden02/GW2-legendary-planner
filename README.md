# GW2 Legendary Planner

GW2 Legendary Planner is a desktop-ready Python library and CLI for answering:

> What is the highest-value thing my Guild Wars 2 account can work on next?

The first milestone focuses on legendary crafting account analysis. The code is
structured as a reusable library first and a command-line tool second, so future
GUI, automation, and planner surfaces can reuse the same API loading, inventory,
and planning engines.

## Status

Phase 2, Phase 3 activity planning, and Phase 4 progression planning are
complete. Phase 5 desktop work has started with a local browser dashboard. The
project currently supports:

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
- Evaluating Gift of Battle and Gift of Exploration activity readiness from
  account inventory.
- Tracking data-defined collection/checklist progress from account inventory,
  wallet, and legendary armory data.
- Tracking source-defined daily and weekly task progress from account
  achievements, wallet, inventory, and manual placeholders.
- Evaluating Legendary Weapon Starter Kit sets against account readiness without
  trading-post price assumptions.
- Validating, reporting, and optimizing packaged or external Wizard's Vault
  seasonal reward data.
- Scoring account progression and ranking next-step recommendations from the
  existing planner outputs.
- Building and locally serving a desktop-ready HTML dashboard over the same
  planner outputs.
- Exporting planner data as JSON or CSV.

The packaged recipe set is intentionally generation-one focused. Market pricing,
shopping lists, live rotating objective feeds, native packaging, and
multi-account workflows are planned for later Phase 5 slices.

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
uv run gw2planner activities report --input ./exports/
uv run gw2planner activities collections --input ./exports/ --data ./collections.json
uv run gw2planner activities gift-of-battle --input ./exports/
uv run gw2planner activities gift-of-exploration --input ./exports/
uv run gw2planner activities starter-kits --input ./exports/ --set 1
uv run gw2planner activities wizard-vault
uv run gw2planner activities wizard-vault --data ./wizard-vault-season.json
uv run gw2planner activities wizard-vault-optimize --input ./exports/ --data ./wizard-vault-season.json
uv run gw2planner activities wizard-vault-validate --data ./wizard-vault-season.json
uv run gw2planner progress achievements --input ./exports/ --data ./achievements.json
uv run gw2planner progress dailies --input ./exports/ --data ./recurring.json
uv run gw2planner progress weeklies --input ./exports/ --data ./recurring.json
uv run gw2planner progress score --input ./exports/ --achievements-data ./achievements.json --collections-data ./collections.json --recurring-data ./recurring.json
uv run gw2planner progress recommend --input ./exports/ --achievements-data ./achievements.json --collections-data ./collections.json --recurring-data ./recurring.json --wizard-vault-data ./wizard-vault-season.json --starter-kit-set 1
uv run gw2planner export activities --input ./exports/ --format csv
uv run gw2planner export achievements --input ./exports/ --data ./achievements.json --format csv
uv run gw2planner export collections --input ./exports/ --data ./collections.json --format csv
uv run gw2planner export recurring --input ./exports/ --data ./recurring.json --format csv
uv run gw2planner export progression --input ./exports/ --achievements-data ./achievements.json --collections-data ./collections.json --recurring-data ./recurring.json --format json
uv run gw2planner export starter-kits --input ./exports/ --set 1 --format csv
uv run gw2planner export wizard-vault --data ./wizard-vault-season.json --format json
uv run gw2planner export wizard-vault-optimization --input ./exports/ --data ./wizard-vault-season.json --format csv
uv run gw2planner gui build --input ./exports/ --achievements-data ./achievements.json --collections-data ./collections.json --recurring-data ./recurring.json --output dashboard.html
uv run gw2planner gui serve --input ./exports/ --achievements-data ./achievements.json --collections-data ./collections.json --recurring-data ./recurring.json --port 8765
uv run gw2planner doctor --input ./exports/
uv run gw2planner doctor --require-api-key
```

`--input` expects JSON files named after supported endpoints:

- `account.json`
- `account_wallet.json`
- `account_achievements.json`
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
scope, [docs/ACTIVITIES.md](docs/ACTIVITIES.md) for activity planner scope, and
[docs/ROADMAP.md](docs/ROADMAP.md) for planned phases.
