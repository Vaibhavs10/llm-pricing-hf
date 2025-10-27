from __future__ import annotations

from collections.abc import Iterable
from typing import Dict, Type

from .scrapers.base import ProviderScraper


_REGISTRY: Dict[str, Type[ProviderScraper]] = {}


def register_provider(name: str, scraper_cls: Type[ProviderScraper]) -> None:
    key = name.lower()
    if key in _REGISTRY:
        raise ValueError(f"Provider '{name}' already registered.")
    _REGISTRY[key] = scraper_cls


def get_provider_scraper(name: str) -> Type[ProviderScraper]:
    key = name.lower()
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"Unknown provider '{name}'. Known providers: {sorted(_REGISTRY)}") from exc


def list_providers() -> Iterable[str]:
    return sorted(_REGISTRY)
