from gw2_legendary_planner.cache.local import ApiCache


def test_api_cache_round_trips_payload(tmp_path) -> None:
    cache = ApiCache(tmp_path, ttl_seconds=60)

    cache.set("/v2/example", {"ids": "all"}, [{"id": 1}])

    assert cache.get("/v2/example", {"ids": "all"}) == [{"id": 1}]
    assert cache.get("/v2/example", {"ids": "different"}) is None
