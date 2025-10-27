from __future__ import annotations

import re
from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


VALUE_PATTERN = re.compile(r"\$?\s*(\d+(?:\.\d+)?)")


class GroqScraper(ProviderScraper):
    """Scrape Groq's pricing tables and align each row with HF model slugs."""
    provider_name = "groq"
    source_url = "https://groq.com/pricing/"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        tables = soup.find_all("table")
        if not tables:
            return []

        results: List[ModelPricing] = []
        for table in tables:
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if "ai model" not in headers or "input token price" not in " ".join(headers):
                continue
            for row in table.find("tbody").find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
                if len(cells) < 4:
                    continue
                model_name = cells[0].replace("AI Model", "").strip()
                canonical_name = self.canonicalize_model_name(model_name)
                if not canonical_name:
                    continue
                input_value = VALUE_PATTERN.search(cells[2])
                output_value = VALUE_PATTERN.search(cells[3])
                results.append(
                    ModelPricing(
                        provider=self.provider_name,
                        model=canonical_name,
                        input_price_per_million=float(input_value.group(1)) if input_value else None,
                        output_price_per_million=float(output_value.group(1)) if output_value else None,
                        currency=self.currency,
                        unit=self.unit,
                        source_url=self.source_url,
                    )
                )
        return results


register_provider(GroqScraper.provider_name, GroqScraper)
