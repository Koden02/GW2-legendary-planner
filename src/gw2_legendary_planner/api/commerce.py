from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import httpx

from gw2_legendary_planner.cache.local import ApiCache
from gw2_legendary_planner.models.commerce import CommercePrice


class CommercePriceError(RuntimeError):
    """Raised when commerce price data cannot be loaded from cache or API."""


class CommercePriceNotFoundError(CommercePriceError):
    """Raised when the GW2 API has no commerce price for an item id."""


class CommercePriceService:
    """Lazy, batched loader for GW2 trading-post price summaries."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.guildwars2.com",
        cache: ApiCache | None = None,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int = 900,
        timeout: float = 20.0,
        batch_size: int = 200,
        skip_missing: bool = True,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache or (
            ApiCache(cache_dir, ttl_seconds=cache_ttl_seconds) if cache_dir else None
        )
        self.timeout = timeout
        self.batch_size = batch_size
        self.skip_missing = skip_missing
        self.transport = transport
        self._memory_cache: dict[int, CommercePrice] = {}

    def get_price(self, item_id: int) -> CommercePrice:
        prices = self.get_prices([item_id])
        try:
            return prices[item_id]
        except KeyError as exc:
            raise CommercePriceNotFoundError(
                f"GW2 commerce price was not returned for item id {item_id}."
            ) from exc

    def get_prices(self, item_ids: Iterable[int]) -> dict[int, CommercePrice]:
        requested_ids = list(dict.fromkeys(item_ids))
        if not requested_ids:
            return {}

        prices: dict[int, CommercePrice] = {}
        missing_ids: list[int] = []
        for item_id in requested_ids:
            cached = self._get_cached_price(item_id)
            if cached:
                prices[item_id] = cached
            else:
                missing_ids.append(item_id)

        for batch in _chunks(missing_ids, self.batch_size):
            for price in self._fetch_prices_best_effort(batch):
                prices[price.id] = price
                self._memory_cache[price.id] = price
                self._cache_price(price)

        missing_after_fetch = [
            item_id for item_id in requested_ids if item_id not in prices
        ]
        if missing_after_fetch and not self.skip_missing:
            ids = ", ".join(str(item_id) for item_id in missing_after_fetch)
            raise CommercePriceNotFoundError(
                f"GW2 commerce prices were not returned for item ids: {ids}."
            )

        return {item_id: prices[item_id] for item_id in requested_ids if item_id in prices}

    def _get_cached_price(self, item_id: int) -> CommercePrice | None:
        if item_id in self._memory_cache:
            return self._memory_cache[item_id]
        if not self.cache:
            return None
        payload = self.cache.get("/v2/commerce/prices", {"id": str(item_id)})
        if payload is None:
            return None
        price = CommercePrice.model_validate(payload)
        self._memory_cache[price.id] = price
        return price

    def _cache_price(self, price: CommercePrice) -> None:
        if self.cache:
            self.cache.set(
                "/v2/commerce/prices",
                {"id": str(price.id)},
                price.model_dump(mode="json"),
            )

    def _fetch_prices_best_effort(self, item_ids: list[int]) -> list[CommercePrice]:
        try:
            return self._fetch_prices(item_ids)
        except CommercePriceNotFoundError:
            if not self.skip_missing:
                raise
            if len(item_ids) <= 1:
                return []
            prices: list[CommercePrice] = []
            for item_id in item_ids:
                prices.extend(self._fetch_prices_best_effort([item_id]))
            return prices

    def _fetch_prices(self, item_ids: list[int]) -> list[CommercePrice]:
        if not item_ids:
            return []

        url = f"{self.base_url}/v2/commerce/prices"
        params = {"ids": ",".join(str(item_id) for item_id in item_ids)}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {
                httpx.codes.BAD_REQUEST,
                httpx.codes.NOT_FOUND,
            }:
                raise CommercePriceNotFoundError(
                    "GW2 commerce price request did not find prices for item ids: "
                    f"{params['ids']}."
                ) from exc
            raise CommercePriceError(
                f"GW2 commerce price request failed: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise CommercePriceError(f"GW2 commerce price request failed: {exc}") from exc

        payload = response.json()
        if not isinstance(payload, list):
            raise CommercePriceError(
                "GW2 commerce price response had an unexpected payload shape."
            )
        return [CommercePrice.model_validate(price) for price in payload]


def _chunks(item_ids: list[int], size: int) -> list[list[int]]:
    return [item_ids[index : index + size] for index in range(0, len(item_ids), size)]
