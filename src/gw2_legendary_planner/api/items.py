from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import httpx

from gw2_legendary_planner.cache.local import ApiCache
from gw2_legendary_planner.models.items import ItemMetadata


class ItemMetadataError(RuntimeError):
    """Raised when item metadata cannot be loaded from cache or the GW2 API."""


class ItemMetadataService:
    """Lazy, batched item metadata loader with optional per-item local caching."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.guildwars2.com",
        cache: ApiCache | None = None,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int = 86_400,
        timeout: float = 20.0,
        batch_size: int = 200,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache or (
            ApiCache(cache_dir, ttl_seconds=cache_ttl_seconds) if cache_dir else None
        )
        self.timeout = timeout
        self.batch_size = batch_size
        self.transport = transport
        self._memory_cache: dict[int, ItemMetadata] = {}

    def get_item(self, item_id: int) -> ItemMetadata:
        items = self.get_items([item_id])
        try:
            return items[item_id]
        except KeyError as exc:
            message = f"Item metadata was not returned for item id {item_id}."
            raise ItemMetadataError(message) from exc

    def get_items(self, item_ids: Iterable[int]) -> dict[int, ItemMetadata]:
        requested_ids = list(dict.fromkeys(item_ids))
        if not requested_ids:
            return {}

        items: dict[int, ItemMetadata] = {}
        missing_ids: list[int] = []
        for item_id in requested_ids:
            cached = self._get_cached_item(item_id)
            if cached:
                items[item_id] = cached
            else:
                missing_ids.append(item_id)

        for batch in _chunks(missing_ids, self.batch_size):
            for item in self._fetch_items(batch):
                items[item.id] = item
                self._memory_cache[item.id] = item
                self._cache_item(item)

        missing_after_fetch = [item_id for item_id in requested_ids if item_id not in items]
        if missing_after_fetch:
            ids = ", ".join(str(item_id) for item_id in missing_after_fetch)
            raise ItemMetadataError(f"Item metadata was not returned for item ids: {ids}.")

        return {item_id: items[item_id] for item_id in requested_ids}

    def _get_cached_item(self, item_id: int) -> ItemMetadata | None:
        if item_id in self._memory_cache:
            return self._memory_cache[item_id]
        if not self.cache:
            return None
        payload = self.cache.get("/v2/items", {"id": str(item_id)})
        if payload is None:
            return None
        item = ItemMetadata.model_validate(payload)
        self._memory_cache[item.id] = item
        return item

    def _cache_item(self, item: ItemMetadata) -> None:
        if self.cache:
            self.cache.set("/v2/items", {"id": str(item.id)}, item.model_dump(mode="json"))

    def _fetch_items(self, item_ids: list[int]) -> list[ItemMetadata]:
        if not item_ids:
            return []

        url = f"{self.base_url}/v2/items"
        params = {"ids": ",".join(str(item_id) for item_id in item_ids)}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ItemMetadataError(
                f"GW2 item metadata request failed: {exc.response.status_code} "
                f"{exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ItemMetadataError(f"GW2 item metadata request failed: {exc}") from exc

        payload = response.json()
        if not isinstance(payload, list):
            raise ItemMetadataError("GW2 item metadata response had an unexpected payload shape.")
        return [ItemMetadata.model_validate(item) for item in payload]


def _chunks(item_ids: list[int], size: int) -> list[list[int]]:
    return [item_ids[index : index + size] for index in range(0, len(item_ids), size)]
