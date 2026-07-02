from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from gw2_legendary_planner.cache.local import ApiCache
from gw2_legendary_planner.models.snapshot import AccountSnapshot

ACCOUNT_ENDPOINTS: Mapping[str, str] = {
    "account": "/v2/account",
    "wallet": "/v2/account/wallet",
    "achievements": "/v2/account/achievements",
    "materials": "/v2/account/materials",
    "bank": "/v2/account/bank",
    "shared_inventory": "/v2/account/inventory",
    "legendary_armory": "/v2/account/legendaryarmory",
    "characters": "/v2/characters",
}


class GW2ApiError(RuntimeError):
    """Raised when the Guild Wars 2 API returns an unusable response."""


class GW2ApiClient:
    """Small authenticated Guild Wars 2 API client."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.guildwars2.com",
        cache: ApiCache | None = None,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.cache = cache
        self.timeout = timeout
        self.transport = transport

    def get(self, endpoint: str, params: Mapping[str, str] | None = None) -> Any:
        request_params = dict(params or {})
        if self.cache:
            cached = self.cache.get(endpoint, request_params)
            if cached is not None:
                return cached

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(url, params=request_params, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GW2ApiError(
                f"GW2 API request failed for {endpoint}: "
                f"{exc.response.status_code} {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GW2ApiError(f"GW2 API request failed for {endpoint}: {exc}") from exc

        payload = response.json()
        if self.cache:
            self.cache.set(endpoint, request_params, payload)
        return payload

    def load_account_snapshot(self) -> AccountSnapshot:
        payloads: dict[str, Any] = {}
        for name, endpoint in ACCOUNT_ENDPOINTS.items():
            params = {"ids": "all"} if name == "characters" else None
            payloads[name] = self.get(endpoint, params=params)
        return AccountSnapshot.from_raw(payloads)
