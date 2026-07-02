from pathlib import Path

import httpx

from gw2_legendary_planner.api.commerce import CommercePriceService
from gw2_legendary_planner.cache.local import ApiCache


def test_commerce_price_service_fetches_batches_and_caches_prices(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        assert request.url.params["ids"] == "1,2"
        return httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "whitelisted": True,
                    "buys": {"quantity": 100, "unit_price": 90},
                    "sells": {"quantity": 40, "unit_price": 120},
                },
                {
                    "id": 2,
                    "whitelisted": True,
                    "buys": {"quantity": 10, "unit_price": 900},
                    "sells": {"quantity": 2, "unit_price": 1200},
                },
            ],
        )

    service = CommercePriceService(
        base_url="https://api.test",
        cache=ApiCache(tmp_path, ttl_seconds=60),
        transport=httpx.MockTransport(handler),
    )

    first = service.get_prices([1, 2])
    second = service.get_price(1)

    assert first[1].sells.unit_price == 120
    assert first[2].buys.quantity == 10
    assert second.buys.unit_price == 90
    assert len(requests) == 1


def test_commerce_price_service_uses_disk_cache_without_fetching(tmp_path: Path) -> None:
    cache = ApiCache(tmp_path, ttl_seconds=60)
    cache.set(
        "/v2/commerce/prices",
        {"id": "1"},
        {
            "id": 1,
            "whitelisted": True,
            "buys": {"quantity": 5, "unit_price": 100},
            "sells": {"quantity": 8, "unit_price": 150},
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected request: {request.url}")

    service = CommercePriceService(
        base_url="https://api.test",
        cache=cache,
        transport=httpx.MockTransport(handler),
    )

    assert service.get_price(1).sells.unit_price == 150


def test_commerce_price_service_skips_unpriced_items_after_batch_404() -> None:
    requested_ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        ids = request.url.params["ids"]
        requested_ids.append(ids)
        if ids == "1":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 1,
                        "whitelisted": True,
                        "buys": {"quantity": 5, "unit_price": 100},
                        "sells": {"quantity": 8, "unit_price": 150},
                    }
                ],
            )
        return httpx.Response(404, json={"text": "invalid id"})

    service = CommercePriceService(
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )

    prices = service.get_prices([1, 999])

    assert list(prices) == [1]
    assert requested_ids == ["1,999", "1", "999"]
