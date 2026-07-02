from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class ProfileError(RuntimeError):
    """Raised when account profiles cannot be loaded or resolved."""


class AccountProfile(BaseModel):
    """Stored account profile for reusable account-source settings."""

    name: str
    api_key: str | None = None
    api_key_env: str | None = None
    input_dir: Path | None = None
    cache_dir: Path | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Profile name cannot be blank.")
        if not PROFILE_NAME_PATTERN.fullmatch(stripped):
            raise ValueError(
                "Profile name may only contain letters, numbers, dots, dashes, and underscores."
            )
        return stripped

    def resolved_api_key(self, fallback: str | None = None) -> str | None:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.getenv(self.api_key_env)
        return fallback


class ProfileConfig(BaseModel):
    """Serializable profile store format."""

    default_profile: str | None = None
    profiles: dict[str, AccountProfile] = Field(default_factory=dict)


class ProfileStore:
    """JSON-backed account profile store."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ProfileConfig:
        if not self.path.exists():
            return ProfileConfig()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return ProfileConfig.model_validate(payload)
        except json.JSONDecodeError as exc:
            raise ProfileError(
                f"Profile file contains malformed JSON: {self.path}."
            ) from exc
        except ValidationError as exc:
            raise ProfileError(f"Profile file is invalid: {exc.errors()[0]['msg']}") from exc

    def save(self, config: ProfileConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            config.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    def list_profiles(self) -> list[AccountProfile]:
        config = self.load()
        return [
            config.profiles[name]
            for name in sorted(config.profiles, key=lambda value: value.lower())
        ]

    def get_profile(self, name: str | None = None) -> AccountProfile | None:
        config = self.load()
        resolved_name = name or config.default_profile
        if not resolved_name:
            return None
        try:
            return config.profiles[resolved_name]
        except KeyError as exc:
            raise ProfileError(f"Unknown profile: {resolved_name}") from exc

    def upsert_profile(self, profile: AccountProfile, *, make_default: bool = False) -> None:
        config = self.load()
        config.profiles[profile.name] = profile
        if make_default or not config.default_profile:
            config.default_profile = profile.name
        self.save(config)

    def remove_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ProfileError(f"Unknown profile: {name}")
        del config.profiles[name]
        if config.default_profile == name:
            config.default_profile = next(iter(sorted(config.profiles)), None)
        self.save(config)

    def set_default(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ProfileError(f"Unknown profile: {name}")
        config.default_profile = name
        self.save(config)
