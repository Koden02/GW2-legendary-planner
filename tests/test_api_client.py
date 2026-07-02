import httpx

from gw2_legendary_planner.api.client import GW2ApiClient


def test_api_client_loads_account_snapshot_from_supported_endpoints() -> None:
    payloads = {
        "/v2/account": {"name": "Api.1234"},
        "/v2/account/wallet": [{"id": 1, "value": 10000}],
        "/v2/account/materials": [{"id": 19976, "count": 1}],
        "/v2/account/bank": [],
        "/v2/account/inventory": [],
        "/v2/account/legendaryarmory": [],
        "/v2/characters": [{"name": "Api Character"}],
    }
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        seen_paths.append(request.url.path)
        if request.url.path == "/v2/characters":
            assert request.url.params["ids"] == "all"
        return httpx.Response(200, json=payloads[request.url.path])

    client = GW2ApiClient(
        "test-token",
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )

    snapshot = client.load_account_snapshot()

    assert snapshot.account.name == "Api.1234"
    assert snapshot.wallet_value(1) == 10000
    assert snapshot.materials[0].id == 19976
    assert snapshot.characters[0].name == "Api Character"
    assert seen_paths == list(payloads)
