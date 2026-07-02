from pathlib import Path

import pytest

from gw2_legendary_planner.config.profiles import (
    AccountProfile,
    ProfileError,
    ProfileStore,
)


def test_profile_store_round_trips_profiles_and_default(tmp_path: Path, monkeypatch) -> None:
    profile_file = tmp_path / "profiles.json"
    store = ProfileStore(profile_file)
    input_dir = tmp_path / "exports"
    cache_dir = tmp_path / "cache" / "main"
    monkeypatch.setenv("GW2_MAIN_API_KEY", "secret")

    profile = AccountProfile(
        name="main",
        api_key_env="GW2_MAIN_API_KEY",
        input_dir=input_dir,
        cache_dir=cache_dir,
    )
    store.upsert_profile(profile, make_default=True)

    loaded = store.get_profile()

    assert loaded is not None
    assert loaded.name == "main"
    assert loaded.input_dir == input_dir
    assert loaded.cache_dir == cache_dir
    assert loaded.resolved_api_key() == "secret"
    assert store.list_profiles()[0].name == "main"


def test_profile_store_remove_updates_default(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path / "profiles.json")
    store.upsert_profile(AccountProfile(name="main"), make_default=True)
    store.upsert_profile(AccountProfile(name="alt"), make_default=False)

    store.remove_profile("main")

    assert store.get_profile() is not None
    assert store.get_profile().name == "alt"


def test_profile_store_reports_malformed_json(tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.json"
    profile_file.write_text("{", encoding="utf-8")

    with pytest.raises(ProfileError, match="malformed JSON"):
        ProfileStore(profile_file).load()
