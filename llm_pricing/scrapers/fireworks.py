from __future__ import annotations

import re
from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


INPUT_OUTPUT_PATTERN = re.compile(
    r"\$?(?P<input>\d+(?:\.\d+)?)\s*(?:/M|\sper)?\s*input(?:,|\s+)(?:\$?(?P<output>\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
SINGLE_PRICE_PATTERN = re.compile(r"\$?(?P<price>\d+(?:\.\d+)?)")


class FireworksScraper(ProviderScraper):
    provider_name = "fireworks-ai"
    source_url = "https://fireworks.ai/pricing"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        tables = soup.find_all("table")
        if not tables:
            return []

        table = tables[0]
        results: List[ModelPricing] = []
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            model_name = cells[0].get_text(" ", strip=True)
            price_text = cells[1].get_text(" ", strip=True)

            canonical_name = self.canonicalize_model_name(model_name)
            if not canonical_name:
                continue

            input_price = None
            output_price = None
            match = INPUT_OUTPUT_PATTERN.search(price_text)
            if match:
                input_price = float(match.group("input"))
                if match.group("output"):
                    output_price = float(match.group("output"))
            else:
                single = SINGLE_PRICE_PATTERN.search(price_text)
                if single:
                    value = float(single.group("price"))
                    input_price = output_price = value

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


register_provider(FireworksScraper.provider_name, FireworksScraper)
