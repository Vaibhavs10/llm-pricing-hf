from __future__ import annotations

from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class NovitaScraper(ProviderScraper):
    """Parse Novita's pricing tables and retain only HF-listed models."""
    provider_name = "novita"
    source_url = "https://novita.ai/pricing"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        results: List[ModelPricing] = []
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if not headers or "model name" not in headers:
                continue
            body = table.find("tbody")
            if not body:
                continue
            for row in body.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
                if len(cells) < 4:
                    continue
                model_name = cells[0]
                canonical_name = self.canonicalize_model_name(model_name)
                if not canonical_name:
                    continue
                input_price = self.normalize_price(cells[2])
                output_price = self.normalize_price(cells[3])
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


register_provider(NovitaScraper.provider_name, NovitaScraper)
