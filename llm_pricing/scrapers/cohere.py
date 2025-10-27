from __future__ import annotations

import json
from typing import List, Sequence

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper
from ..utils import clean_money


def _extract_pricing_groups(html: str):
    decoded = bytes(html, "utf-8").decode("unicode_escape")
    marker = '"pricingGroups":'
    start = decoded.find(marker)
    if start == -1:
        return []
    start = decoded.find("[", start)
    if start == -1:
        return []
    depth = 0
    end = start
    for idx in range(start, len(decoded)):
        ch = decoded[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    segment = decoded[start:end + 3]
    try:
        data, _ = json.JSONDecoder().raw_decode(segment)
        return data
    except json.JSONDecodeError:
        return []


class CohereScraper(ProviderScraper):
    provider_name = "cohere"
    source_url = "https://cohere.com/pricing"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        pricing_groups = _extract_pricing_groups(response.text)
        if not pricing_groups:
            return []
        results: List[ModelPricing] = []
        for group in pricing_groups:
            for model in group.get("models", []):
                model_name = model.get("modelName") or model.get("title") or model.get("description", "").split(".")[0]
                for pricing in model.get("pricings", []):
                    per = pricing.get("overridePer") or model.get("per") or ""
                    price_unit = per or self.unit
                    input_price = pricing.get("inputPrice")
                    output_price = pricing.get("outputPrice")
                    if isinstance(input_price, str):
                        input_price = clean_money(input_price)
                    if isinstance(output_price, str):
                        output_price = clean_money(output_price)
                    results.append(
                        ModelPricing(
                            provider=self.provider_name,
                            model=model_name.strip(),
                            input_price_per_million=input_price if isinstance(input_price, (int, float)) else None,
                            output_price_per_million=output_price if isinstance(output_price, (int, float)) else None,
                            currency=self.currency,
                            unit=price_unit or self.unit,
                            source_url=self.source_url,
                        )
                    )
        return results


register_provider(CohereScraper.provider_name, CohereScraper)
