from __future__ import annotations

import json
from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class NebiusScraper(ProviderScraper):
    """Extract pricing from Nebius' embedded Apollo state for AI Studio."""
    provider_name = "nebius"
    source_url = "https://nebius.com/prices-ai-studio"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        script_tag = next(
            (
                script
                for script in soup.find_all("script")
                if script.string and script.string.strip().startswith('{"props"')
            ),
            None,
        )
        if not script_tag:
            return []
        props = json.loads(script_tag.string)
        state = props["props"]["pageProps"]["__APOLLO_STATE__"]
        page_key = next(k for k in state if k.startswith('pages:{') and '"id":"146"' in k)
        content = json.loads(state[page_key]["content"])

        results: List[ModelPricing] = []
        for block in content.get("blocks", []):
            if block.get("type") != "tabs-highlight-table-block":
                continue
            for tab in block.get("items", []):
                rows = tab.get("table", {}).get("content", [])
                if not rows:
                    continue
                header, *entries = rows
                last_model = None
                for entry in entries:
                    if len(entry) < 4:
                        continue
                    model, flavor, input_value, output_value = entry[:4]
                    if model:
                        last_model = model
                    if not last_model:
                        continue
                    model_label = f"{last_model} ({flavor})" if flavor else last_model
                    canonical_name = self.canonicalize_model_name(model_label)
                    if not canonical_name:
                        continue
                    input_price = self.normalize_price(input_value)
                    output_price = self.normalize_price(output_value)
                    if input_price is None and output_price is None:
                        continue
                    notes = None
                    if canonical_name != model_label:
                        notes = f"variant: {model_label}"
                    results.append(
                        ModelPricing(
                            provider=self.provider_name,
                            model=canonical_name,
                            input_price_per_million=input_price,
                            output_price_per_million=output_price,
                            currency=self.currency,
                            unit=self.unit,
                            source_url=self.source_url,
                            notes=notes,
                        )
                    )
        return results


register_provider(NebiusScraper.provider_name, NebiusScraper)
