# Recipe Data

The packaged recipe database is intentionally scoped. It now covers all
generation-one top-level legendary weapon forge recipes and selected shared
subrecipes.

Current seed recipes:

- all 20 generation-one top-level legendary weapons
- `legendary.twilight`
- `legendary.sunrise`
- `legendary.bolt`
- all 20 generation-one weapon-specific Mystic Forge gifts
- `weapon_gift.bolt`
- `weapon_gift.twilight`
- `weapon_gift.the_bifrost`
- API-verified shared crafting recipes such as `gift.metal`, `gift.wood`,
  `gift.energy`, paired gifts, statues, and vials
- `gift.mastery`
- `gift.fortune`
- `gift.might`
- `gift.magic`

Shared source pages used for the initial seed set:

- https://wiki.guildwars2.com/wiki/Twilight
- https://wiki.guildwars2.com/wiki/Gift_of_Mastery
- https://wiki.guildwars2.com/wiki/Gift_of_Fortune
- https://wiki.guildwars2.com/wiki/Gift_of_Might
- https://wiki.guildwars2.com/wiki/Gift_of_Magic

Generation-one top-level item, precursor, and weapon-gift IDs were verified
against the GW2 Wiki pages and `/v2/items`.

Shared crafting recipe ingredients were verified against official
`/v2/recipes/search?output=...` and `/v2/recipes` responses.

Weapon-specific Mystic Forge gift ingredients were verified from the GW2 Wiki
`{{Recipe}}` blocks because the official recipes API does not expose those
Mystic Forge recipes.

Terminal requirements may include `acquisition` hints. These hints are
source-context labels for reports, not optimization rules. They currently cover
high-signal generation-one requirements such as Gift of Battle, Gift of
Exploration, Bloodstone Shard, Obsidian Shard, Icy Runestone, Mystic Clover, and
Gift of Ascalon.

## Shopping Lists

Shopping lists are generated from recipe effective costs. They aggregate one or
more selected recipe evaluations, count account inventory once against the
combined target, and report missing quantities with acquisition hints.

```powershell
uv run gw2planner recipes shopping-list legendary.bolt --input ./exports/
uv run gw2planner recipes shopping-list legendary.bolt legendary.twilight --input ./exports/ --format csv
uv run gw2planner export shopping-list legendary.bolt --input ./exports/ --format json
```

Shopping lists do not include trading-post prices, automatic vendor costs, or
purchase optimization. Those belong to later market-data work.

## Current Limits

Top-level legendary recipes recurse into `Gift of Mastery`, `Gift of Fortune`,
`Gift of Might`, `Gift of Magic`, weapon-specific Mystic Forge gifts, and
API-backed shared crafting recipes.

Dungeon gifts, karma/vendor purchases, and trading-post price estimates are still
represented as terminal requirements. Their acquisition planners belong in later
phases.

## Data Rules

- Add recipes as data in `src/gw2_legendary_planner/data/legendary_recipes.json`.
- Include stable IDs, names, quantities, and tags.
- Add acquisition hints for terminal account-bound, vendor, reward-track,
  dungeon, or world-completion requirements when the source is stable and
  source-verifiable.
- Keep recipe evaluation logic in `planner/recipe_evaluator.py`.
- Add tests for every new recipe family or graph behavior.
- Run `gw2planner recipes validate` before committing recipe data changes.
- Do not add trading-post price assumptions to recipe data.

## Validation

Recipe data validation catches:

- duplicate recipe IDs
- duplicate recipe outputs
- blank recipe names
- invalid output or requirement quantities
- item/currency requirements with non-integer IDs
- missing requirement display names
- acquisition hints with blank labels or invalid source URLs
- recipe dependency cycles

Use:

```powershell
uv run gw2planner recipes validate
uv run gw2planner recipes validate --format json
uv run gw2planner recipes validate --format csv
```
