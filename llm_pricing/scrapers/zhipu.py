from __future__ import annotations

from typing import Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


DOC_ALIAS_MAP = {
    "zai-org/GLM-4.6": "GLM-4.6",
    "zai-org/GLM-4.6-FP8": "GLM-4.6",
    "zai-org/GLM-4.5": "GLM-4.5",
    "zai-org/GLM-4.5V": "GLM-4.5V",
    "zai-org/GLM-4.5V-FP8": "GLM-4.5V",
    "zai-org/GLM-4.5-Air": "GLM-4.5-Air",
}


class ZhipuScraper(ProviderScraper):
    """Read Zhipu's Mintlify pricing table and map entries to HF zai-org slugs."""
    provider_name = "zhipu"
    source_url = "https://docs.z.ai/guides/overview/pricing"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")

        pricing_table = soup.find("table")
        if pricing_table is None:
            raise ValueError("Unable to locate pricing table on Zhipu docs page.")

        doc_prices: dict[str, tuple[float | None, float | None]] = {}
        body = pricing_table.find("tbody")
        if not body:
            return []

        for row in body.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            if len(cells) < 5:
                continue
            doc_name, input_price, _, _, output_price = cells[:5]
            doc_prices[doc_name] = (
                self._parse_price(input_price),
                self._parse_price(output_price),
            )

        results: list[ModelPricing] = []
        for hf_name, doc_name in DOC_ALIAS_MAP.items():
            pricing = doc_prices.get(doc_name)
            if pricing is None:
                # Skip models with no publicly documented pricing.
                continue
            canonical_name = self.canonicalize_model_name(hf_name)
            if not canonical_name:
                continue
            input_price, output_price = pricing
            notes = None
            if doc_name != hf_name.split("/", 1)[-1]:
                notes = f"Pricing matched from base model '{doc_name}' listing."
            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical_name,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit="per million tokens",
                    source_url=self.source_url,
                    notes=notes,
                )
            )

        return results

    @staticmethod
    def _parse_price(value: str) -> float | None:
        if not value:
            return None
        value = value.strip().lower()
        if value in {"-", "—"}:
            return None
        if "free" in value:
            return 0.0
        value = value.replace("$", "")
        try:
            return float(value)
        except ValueError:
            return None


register_provider(ZhipuScraper.provider_name, ZhipuScraper)
