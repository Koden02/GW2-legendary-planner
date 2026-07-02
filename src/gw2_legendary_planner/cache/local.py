from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class ApiCache:
    """Simple JSON file cache for GW2 API responses."""

    def __init__(self, cache_dir: Path, *, ttl_seconds: int = 3600) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, endpoint: str, params: dict[str, str]) -> Any | None:
        path = self._path_for(endpoint, params)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        if time.time() - record.get("created_at", 0) > self.ttl_seconds:
            return None
        return record.get("payload")

    def set(self, endpoint: str, params: dict[str, str], payload: Any) -> None:
        path = self._path_for(endpoint, params)
        record = {
            "created_at": time.time(),
            "endpoint": endpoint,
            "params": params,
            "payload": payload,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)

    def _path_for(self, endpoint: str, params: dict[str, str]) -> Path:
        key = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"
