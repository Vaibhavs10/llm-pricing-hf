from __future__ import annotations

from typing import Sequence

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class SambaNovaScraper(ProviderScraper):
    """Call the public SambaNova Cloud pricing API and align with HF slugs."""
    provider_name = "sambanova"
    source_url = "https://cloud.sambanova.ai/pricing"
    api_url = "https://cloud.sambanova.ai/api/pricing"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.api_url)
        data = response.json()
        prices = data.get("prices", [])

        results: list[ModelPricing] = []
        for item in prices:
            model_name = (
                item.get("display_name")
                or item.get("model_name")
                or item.get("model_id")
            )
            if not model_name:
                continue

            input_price = self._to_usd(item.get("input_token_price"))
            output_price = self._to_usd(item.get("output_token_price"))
            duration_price = self._to_usd(item.get("input_duration_price_per_hour"))

            notes = []
            family = item.get("family")
            if family:
                notes.append(f"family: {family}")
            if duration_price:
                notes.append(
                    f"audio billed at ${duration_price:.2f} per hour input duration"
                )

            canonical_name = self.canonicalize_model_name(model_name)
            if not canonical_name:
                continue
            if canonical_name != model_name:
                notes.append(f"original label: {model_name}")

            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical_name,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit=self.unit,
                    source_url=self.source_url,
                    notes="; ".join(notes) if notes else None,
                )
            )
        return results

    @staticmethod
    def _to_usd(value) -> float | None:
        if value in (None, "", "0"):
            return None
        try:
            cents = float(value)
        except (TypeError, ValueError):
            return None
        return round(cents / 100.0, 4)


register_provider(SambaNovaScraper.provider_name, SambaNovaScraper)
