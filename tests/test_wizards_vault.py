from datetime import date
from pathlib import Path

import pytest

from gw2_legendary_planner.models.account import WalletEntry
from gw2_legendary_planner.models.snapshot import AccountSnapshot
from gw2_legendary_planner.planner.wizards_vault import (
    WizardVaultDataError,
    WizardVaultReward,
    WizardVaultSeason,
    filter_wizard_vault_seasons,
    load_wizard_vault_seasons,
    load_wizard_vault_seasons_from_path,
    optimize_wizard_vault_rewards,
    validate_wizard_vault_seasons,
)

WIZARD_VAULT_FIXTURE = Path(__file__).parent / "fixtures" / "wizards_vault" / "sample_season.json"


def test_packaged_wizard_vault_data_starts_empty_and_valid() -> None:
    seasons = load_wizard_vault_seasons()
    report = validate_wizard_vault_seasons(seasons, current_date=date(2026, 7, 2))

    assert seasons == []
    assert report.is_valid
    assert report.issues == []


def test_load_wizard_vault_seasons_from_path() -> None:
    seasons = load_wizard_vault_seasons_from_path(WIZARD_VAULT_FIXTURE)

    assert len(seasons) == 1
    assert seasons[0].id == "sample-season"
    assert seasons[0].rewards[0].name == "Legendary Weapon Starter Kit"


def test_load_wizard_vault_seasons_from_path_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(WizardVaultDataError, match="does not exist"):
        load_wizard_vault_seasons_from_path(tmp_path / "missing.json")


def test_load_wizard_vault_seasons_from_path_reports_malformed_json(tmp_path: Path) -> None:
    data_path = tmp_path / "vault.json"
    data_path.write_text("[", encoding="utf-8")

    with pytest.raises(WizardVaultDataError, match="malformed JSON"):
        load_wizard_vault_seasons_from_path(data_path)


def test_load_wizard_vault_seasons_from_path_reports_wrong_payload_shape(tmp_path: Path) -> None:
    data_path = tmp_path / "vault.json"
    data_path.write_text("{}", encoding="utf-8")

    with pytest.raises(WizardVaultDataError, match="must be a JSON array"):
        load_wizard_vault_seasons_from_path(data_path)


def test_wizard_vault_validator_accepts_source_verified_reward_data() -> None:
    season = _season()

    report = validate_wizard_vault_seasons([season], current_date=date(2026, 7, 2))

    assert report.is_valid
    assert report.issues == []


def test_wizard_vault_validator_reports_stale_current_data_and_bad_shapes() -> None:
    season = _season(
        starts_on=date(2026, 9, 1),
        ends_on=date(2026, 8, 1),
        last_verified=date(2026, 1, 1),
        source_url="wiki.guildwars2.com/wiki/Wizard%27s_Vault",
        rewards=[
            _reward(id="legendary-kit", source_url="wiki.guildwars2.com/wiki/Reward"),
            _reward(id="legendary-kit", astral_acclaim_cost=0),
        ],
    )

    report = validate_wizard_vault_seasons([season], current_date=date(2026, 7, 2))
    codes = {issue.code for issue in report.issues}

    assert not report.is_valid
    assert "invalid_season_dates" in codes
    assert "invalid_season_source_url" in codes
    assert "stale_current_season" in codes
    assert "duplicate_reward_id" in codes
    assert "invalid_reward_cost" in codes
    assert "invalid_reward_source_url" in codes


def test_wizard_vault_filtering_can_select_rewards_by_tag() -> None:
    seasons = [
        _season(
            rewards=[
                _reward(id="legendary-kit", tags=["legendary", "starter_kit"]),
                _reward(id="gold", name="Bag of Coins", reward_kind="currency", tags=["gold"]),
            ],
        )
    ]

    filtered = filter_wizard_vault_seasons(seasons, tags={"starter-kit"})

    assert len(filtered) == 1
    assert [reward.id for reward in filtered[0].rewards] == ["legendary-kit"]


def test_wizard_vault_optimizer_prioritizes_affordable_legendary_rewards() -> None:
    snapshot = AccountSnapshot(wallet=[WalletEntry(id=63, value=1200)])
    season = _season(
        rewards=[
            _reward(id="legendary-kit", tags=["legendary", "starter_kit"]),
            _reward(
                id="utility",
                name="Revive Orb",
                reward_kind="item",
                astral_acclaim_cost=50,
                purchase_limit=5,
                tags=["utility"],
            ),
        ],
    )

    report = optimize_wizard_vault_rewards(snapshot, [season])

    assert report.astral_acclaim_balance == 1200
    assert report.remaining_astral_acclaim == 200
    assert [entry.reward_id for entry in report.recommendations] == ["legendary-kit"]
    assert report.recommendations[0].recommended_quantity == 1
    assert report.recommendations[0].is_affordable is True


def test_wizard_vault_optimizer_reports_unaffordable_reward() -> None:
    snapshot = AccountSnapshot(wallet=[WalletEntry(id=63, value=200)])
    season = _season()

    report = optimize_wizard_vault_rewards(snapshot, [season])

    assert report.remaining_astral_acclaim == 200
    assert report.recommendations[0].is_affordable is False
    assert report.recommendations[0].recommended_quantity == 0
    assert "Need 800 more Astral Acclaim" in report.recommendations[0].reason


def _season(
    *,
    id: str = "sample-season",
    name: str = "Sample Season",
    status: str = "current",
    starts_on: date | None = date(2026, 6, 1),
    ends_on: date | None = date(2026, 9, 1),
    source_url: str = "https://wiki.guildwars2.com/wiki/Wizard%27s_Vault",
    last_verified: date = date(2026, 7, 1),
    rewards: list[WizardVaultReward] | None = None,
) -> WizardVaultSeason:
    return WizardVaultSeason(
        id=id,
        name=name,
        status=status,
        starts_on=starts_on,
        ends_on=ends_on,
        source_url=source_url,
        last_verified=last_verified,
        rewards=rewards if rewards is not None else [_reward()],
    )


def _reward(
    *,
    id: str = "legendary-kit",
    name: str = "Legendary Weapon Starter Kit",
    reward_kind: str = "starter_kit",
    astral_acclaim_cost: int = 1000,
    purchase_limit: int | None = 1,
    item_id: int | None = 103847,
    source_url: str = "https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit",
    last_verified: date = date(2026, 7, 1),
    tags: list[str] | None = None,
) -> WizardVaultReward:
    return WizardVaultReward(
        id=id,
        name=name,
        reward_kind=reward_kind,
        astral_acclaim_cost=astral_acclaim_cost,
        purchase_limit=purchase_limit,
        item_id=item_id,
        source_url=source_url,
        last_verified=last_verified,
        tags=tags if tags is not None else ["legendary", "starter_kit"],
    )
