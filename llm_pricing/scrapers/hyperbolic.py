from __future__ import annotations

from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class HyperbolicScraper(ProviderScraper):
    """Read the carousel pricing cards from hyperbolic.ai and map to HF slugs."""
    provider_name = "hyperbolic"
    source_url = "https://www.hyperbolic.ai/inference"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        results: List[ModelPricing] = []
        for container in soup.select(".pricing__body__grid"):
            name_elem = container.find("p")
            price_elem = container.find("label")
            if not name_elem or not price_elem:
                continue
            model_name = name_elem.get_text(strip=True)
            canonical_name = self.canonicalize_model_name(model_name)
            if not canonical_name:
                continue
            price_text = price_elem.get_text(strip=True)
            input_price = output_price = None
            if " / " in price_text:
                input_text, _, rest = price_text.partition("/")
                input_price = self.normalize_price(input_text)
                if "input" in input_text.lower():
                    # price_text like "$0.40 / M tokens"
                    output_price = input_price
                if " / " in rest:
                    # e.g. "$0.1 input / $0.4 output"
                    output_price = self.normalize_price(rest)
            else:
                input_price = output_price = self.normalize_price(price_text)

            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical_name,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit=self.unit,
                    source_url=self.source_url,
                )
            )
        return results


register_provider(HyperbolicScraper.provider_name, HyperbolicScraper)
