# Recipe Data

The packaged recipe database is intentionally scoped. It now covers all
generation-one top-level legendary weapon forge recipes and selected shared
subrecipes.

Current seed recipes:

- all 20 generation-one top-level legendary weapons
- all 20 generation-one weapon-specific Mystic Forge gifts
- API-verified shared crafting recipes such as `gift.metal`, `gift.wood`,
  `gift.energy`, paired gifts, statues, and vials
- `gift.mastery`
- `gift.fortune`
- `gift.might`
- `gift.magic`
- generation-three seed coverage for `legendary.aurenes_fang` and
  `legendary.aurenes_insight`
- generation-three shared Aurene components for Gift of Jade Mastery, Gift of
  Cantha, Gift of the Dragon Empire, and Draconic Tribute

Shared source pages used for the initial seed set:

- https://wiki.guildwars2.com/wiki/Twilight
- https://wiki.guildwars2.com/wiki/Gift_of_Mastery
- https://wiki.guildwars2.com/wiki/Gift_of_Fortune
- https://wiki.guildwars2.com/wiki/Gift_of_Might
- https://wiki.guildwars2.com/wiki/Gift_of_Magic
- https://wiki.guildwars2.com/wiki/Aurene%27s_Fang
- https://wiki.guildwars2.com/wiki/Aurene%27s_Insight
- https://wiki.guildwars2.com/wiki/Gift_of_Jade_Mastery
- https://wiki.guildwars2.com/wiki/Draconic_Tribute

Generation-one top-level item, precursor, and weapon-gift IDs were verified
against the GW2 Wiki pages and `/v2/items`.

Generation-three seed item IDs and Mystic Forge template ingredients were
verified against the GW2 Wiki API page content. This is not complete Gen 3
coverage yet; it exists to prove the metadata and dashboard filtering model.
Aurene variant skins should be represented later as unlock or collection goals,
not as duplicate base legendary weapon recipes.

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
uv run gw2planner recipes shopping-list legendary.bolt --input ./exports/ --include-prices
uv run gw2planner recipes shopping-list legendary.bolt legendary.twilight --input ./exports/ --format csv
uv run gw2planner export shopping-list legendary.bolt --input ./exports/ --format json
```

Base shopping lists do not include trading-post prices, automatic vendor costs,
or purchase optimization. `--include-prices` runs a separate commerce-price
overlay for item requirements after the price-free shopping list is built.

## Current Limits

Top-level legendary recipes recurse into `Gift of Mastery`, `Gift of Fortune`,
`Gift of Might`, `Gift of Magic`, weapon-specific Mystic Forge gifts, and
API-backed shared crafting recipes.

Dungeon gifts and karma/vendor purchases are still represented as terminal
requirements. Their acquisition planners belong in later phases. Trading-post
price estimates are an optional report overlay, not recipe data.

## Data Rules

- Add recipes as data in `src/gw2_legendary_planner/data/legendary_recipes.json`.
- Include stable IDs, names, quantities, and tags.
- Add recipe metadata for new legendary families: `generation`, `family`,
  `expansion`, `weapon_type`, `variant_group`, and `source_urls` where known.
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
