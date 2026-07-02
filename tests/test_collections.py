from pathlib import Path

import pytest

from gw2_legendary_planner.api.local import LocalExportLoader
from gw2_legendary_planner.inventory.aggregator import InventoryAggregator
from gw2_legendary_planner.planner.collections import (
    CollectionDataError,
    evaluate_collections,
    filter_collections,
    load_collection_definitions,
    load_collection_definitions_from_path,
)

EXPORT_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "exports"
COLLECTION_FIXTURE = (
    Path(__file__).parent / "fixtures" / "collections" / "sample_collections.json"
)


def test_packaged_collection_data_starts_empty() -> None:
    assert load_collection_definitions() == []


def test_load_collection_definitions_from_path() -> None:
    definitions = load_collection_definitions_from_path(COLLECTION_FIXTURE)

    assert len(definitions) == 1
    assert definitions[0].id == "sample-legendary-readiness"
    assert definitions[0].requirements[0].name == "Gift of Battle"


def test_load_collection_definitions_from_path_reports_malformed_json(tmp_path: Path) -> None:
    data_path = tmp_path / "collections.json"
    data_path.write_text("[", encoding="utf-8")

    with pytest.raises(CollectionDataError, match="malformed JSON"):
        load_collection_definitions_from_path(data_path)


def test_evaluate_collections_tracks_supported_and_unsupported_requirements() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definitions = load_collection_definitions_from_path(COLLECTION_FIXTURE)

    progress = evaluate_collections(snapshot, inventory, definitions=definitions)[0]
    requirements = {requirement.id: requirement for requirement in progress.requirements}

    assert progress.completed_requirements == 3
    assert progress.unsupported_requirements == 1
    assert progress.is_complete is False
    assert 99 < progress.readiness_percent < 100
    assert requirements["gift-of-battle"].available_quantity == 1
    assert requirements["gift-of-exploration"].available_quantity == 2
    assert requirements["astral-acclaim"].available_quantity == 1200
    assert requirements["unsupported-achievement"].is_supported is False


def test_filter_collections_selects_by_id_and_tag() -> None:
    snapshot = LocalExportLoader(EXPORT_FIXTURE_DIR).load()
    inventory = InventoryAggregator().aggregate(snapshot)
    definitions = load_collection_definitions_from_path(COLLECTION_FIXTURE)
    progress_entries = evaluate_collections(snapshot, inventory, definitions=definitions)

    assert filter_collections(progress_entries, collection_ids={"sample-legendary-readiness"})
    assert filter_collections(progress_entries, tags={"legendary"})
    assert not filter_collections(progress_entries, tags={"missing"})
