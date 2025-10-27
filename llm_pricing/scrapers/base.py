from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils import canonicalize_model_name


DEFAULT_TIMEOUT = 30


@dataclass(frozen=True)
class ModelPricing:
    provider: str
    model: str
    input_price_per_million: Optional[float]
    output_price_per_million: Optional[float]
    currency: str
    unit: str
    source_url: str
    notes: Optional[str] = None


class ProviderScraper(abc.ABC):
    """
    Base class for provider pricing scrapers.
    """

    provider_name: str
    source_url: str
    currency: str = "USD"
    unit: str = "per million tokens"

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def get(self, url: str, *, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", "llm-pricing-scraper/0.1 (+https://huggingface.co)")
        response = self.session.get(url, timeout=timeout, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    @abc.abstractmethod
    def fetch_pricing(self) -> Sequence[ModelPricing]:
        """
        Return a sequence of pricing entries for the provider.
        """

    def scrape(self) -> Sequence[ModelPricing]:
        return self.fetch_pricing()

    @staticmethod
    def normalize_price(value: str) -> Optional[float]:
        digits = "".join(ch for ch in value if ch in "0123456789.")
        if not digits:
            return None
        try:
            return float(digits)
        except ValueError:
            return None

    def canonicalize_model_name(self, model_name: str) -> Optional[str]:
        return canonicalize_model_name(self.provider_name, model_name)


def flatten(pricing_groups: Iterable[Iterable[ModelPricing]]) -> list[ModelPricing]:
    items: list[ModelPricing] = []
    for group in pricing_groups:
        items.extend(group)
    return items
