from pathlib import Path

import httpx

from gw2_legendary_planner.api.items import ItemMetadataService
from gw2_legendary_planner.cache.local import ApiCache


def test_item_metadata_service_fetches_batches_and_caches_items(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        assert request.url.params["ids"] == "1,2"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": "Item One",
                    "rarity": "Rare",
                    "type": "CraftingMaterial",
                    "icon": "https://example.test/1.png",
                    "flags": ["AccountBound"],
                },
                {
                    "id": 2,
                    "name": "Item Two",
                    "rarity": "Exotic",
                    "type": "Weapon",
                    "flags": [],
                },
            ],
        )

    service = ItemMetadataService(
        base_url="https://api.test",
        cache=ApiCache(tmp_path, ttl_seconds=60),
        transport=httpx.MockTransport(handler),
    )

    first = service.get_items([1, 2])
    second = service.get_item(1)

    assert first[1].name == "Item One"
    assert first[2].rarity == "Exotic"
    assert second.name == "Item One"
    assert len(requests) == 1


def test_item_metadata_service_uses_disk_cache_without_fetching(tmp_path: Path) -> None:
    cache = ApiCache(tmp_path, ttl_seconds=60)
    cache.set(
        "/v2/items",
        {"id": "1"},
        {
            "id": 1,
            "name": "Cached Item",
            "rarity": "Basic",
            "type": "CraftingMaterial",
            "flags": [],
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected request: {request.url}")

    service = ItemMetadataService(
        base_url="https://api.test",
        cache=cache,
        transport=httpx.MockTransport(handler),
    )

    assert service.get_item(1).name == "Cached Item"
