# Activity Planner Data

Activity planners describe account-progression tasks that produce legendary
components or unlocks. They are separate from recipe evaluation.

Current implemented goals:

- `gift_of_battle`
- `gift_of_exploration`
- Legendary Weapon Starter Kit set evaluation
- Wizard's Vault seasonal reward data validation and reporting
- Wizard's Vault reward optimization from source-provided season data
- Data-defined collection/checklist tracking

The Gift activity planner answers:

- how many target items the account already has
- where those items are stored
- how many more are needed for the activity goal
- whether the goal is ready for the next legendary craft
- what activity produces the item

The starter-kit planner answers:

- which generation-one legendary weapons are available in a starter-kit set
- how much account readiness improves if the kit covers the precursor and weapon gift
- whether Gift of Might or Gift of Magic is the stronger choice for the account
- which kit-provided items are being simulated

The Wizard's Vault optimizer answers:

- how much Astral Acclaim the account currently has
- which source-provided season rewards are tagged as legendary-relevant
- whether the account can afford each reward
- how many of each ranked reward the account can buy with its current balance

The collection tracker answers:

- which data-defined collection requirements are already satisfied
- how much item, currency, or legendary-armory progress the account has
- which requirements need future account data sources before they can be
  evaluated

## Data Rules

Activity goal definitions live in
`src/gw2_legendary_planner/data/activity_goals.json`.
Starter-kit set definitions live in
`src/gw2_legendary_planner/data/starter_kit_sets.json`.
Collection definitions live in
`src/gw2_legendary_planner/data/collection_goals.json`.
The initial rotation catalog was sourced from the GW2 Wiki Legendary Weapon
Starter Kit page.
Wizard's Vault seasonal reward data lives in
`src/gw2_legendary_planner/data/wizards_vault_seasons.json`.
That packaged file intentionally starts empty. Maintainers and users can load a
source-verified season snapshot without modifying packaged data by passing
`--data ./wizard-vault-season.json` to Wizard's Vault commands.

Wizard's Vault season entries must include:

- season id and name
- status
- source URL
- last verified date
- rewards with Astral Acclaim cost, purchase limit, source URL, last verified
  date, and tags

Minimal external data file:

```json
[
  {
    "id": "sample-season",
    "name": "Sample Wizard's Vault Season",
    "status": "historical",
    "starts_on": "2026-04-01",
    "ends_on": "2026-06-30",
    "source_url": "https://wiki.guildwars2.com/wiki/Wizard%27s_Vault",
    "last_verified": "2026-07-01",
    "rewards": [
      {
        "id": "legendary-starter-kit",
        "name": "Legendary Weapon Starter Kit",
        "reward_kind": "starter_kit",
        "astral_acclaim_cost": 1000,
        "purchase_limit": 1,
        "item_id": 103847,
        "source_url": "https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit",
        "last_verified": "2026-07-01",
        "tags": ["legendary", "starter_kit"]
      }
    ]
  }
]
```

Each definition should include:

- stable goal id
- target kind and target id
- required quantity
- activity kind
- action text
- source URL
- tags for filtering

Collection definitions support these target kinds today:

- `item`
- `currency`
- `achievement`
- `legendary_armory`

They can also represent future `collection` and `account_unlock` targets. Those
requirements are reported as unsupported until the matching account data sources
exist.

## Current Limits

Gift of Battle and Gift of Exploration readiness can be evaluated from inventory
alone. They do not estimate time to complete, map completion percentage, WvW
reward-track progress, boosters, or reward-track potion usage.

Starter-kit evaluation uses readiness improvement, not trading-post value. It
does not choose based on current buy/sell prices and does not claim that a set is
currently available unless a caller filters to that set.

Wizard's Vault reward optimization uses Astral Acclaim balance and
legendary-relevance tags. It does not use trading-post prices, gold conversion,
or claimed current-season availability unless that availability is present in
the caller-provided season data. The packaged Wizard's Vault season file
intentionally starts empty to avoid stale current-season claims.

## Commands

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
