from __future__ import annotations

import re
from typing import Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


PRICE_PATTERN = re.compile(
    r"\$?\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<kind>input|output)",
    flags=re.IGNORECASE,
)


class NscaleScraper(ProviderScraper):
    """Pair the serverless pricing legend with stats rows to capture per-model fees."""
    provider_name = "nscale"
    source_url = "https://www.nscale.com/product/serverless"

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")

        legend_items = [
            item.get_text(strip=True)
            for item in soup.select(
                ".pt-legend-list .pt-legend-item .text-mono-small-regular"
            )
        ]
        stat_items = soup.select(".pt-stats-item")

        if not legend_items or len(legend_items) != len(stat_items):
            raise ValueError(
                "Unexpected Nscale pricing layout: legend and stats counts differ"
            )

        results: list[ModelPricing] = []
        for model_name, stat in zip(legend_items, stat_items):
            provider_text = self._extract_text(
                stat.select_one(".pt-stat.is-hidden .text-mono-small-regular")
            )
            category_text = self._extract_text(
                stat.select_one(
                    ".pt-stat:not(.is-hidden):not(.is-price) .text-mono-small-regular"
                )
            )
            price_block = stat.select_one(".pt-stat.is-price")
            price_line = self._extract_text(
                price_block.select_one(".text-mono-small-bold")
                if price_block
                else None
            )
            unit_line = self._extract_text(
                price_block.select_one(".text-mono-small-regular")
                if price_block
                else None
            )

            input_price, output_price = self._parse_price_line(price_line)
            unit = self._normalize_unit(unit_line)

            notes_parts = []
            if provider_text:
                notes_parts.append(f"provider: {provider_text}")
            if category_text:
                notes_parts.append(f"category: {category_text}")
            notes = "; ".join(notes_parts) if notes_parts else None
            canonical_name = self.canonicalize_model_name(model_name)
            if not canonical_name:
                continue
            if canonical_name != model_name and notes:
                notes = f"{notes}; original label: {model_name}"
            elif canonical_name != model_name:
                notes = f"original label: {model_name}"

            if input_price is None and output_price is None:
                continue

            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical_name,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit=unit,
                    source_url=self.source_url,
                    notes=notes,
                )
            )
        return results

    @staticmethod
    def _extract_text(node) -> str:
        if node is None:
            return ""
        return node.get_text(" ", strip=True)

    @staticmethod
    def _parse_price_line(price_line: str) -> tuple[float | None, float | None]:
        if not price_line:
            return None, None

        price_line = price_line.replace("\xa0", " ")
        input_price = output_price = None
        for match in PRICE_PATTERN.finditer(price_line):
            value = float(match.group("value"))
            kind = match.group("kind").lower()
            if kind.startswith("in"):
                input_price = value
            elif kind.startswith("out"):
                output_price = value

        # If only a single price is provided, treat it as both input/output
        if input_price is None and output_price is not None:
            input_price = output_price
        if output_price is None and input_price is not None:
            output_price = input_price

        return input_price, output_price

    def _normalize_unit(self, unit_line: str | None) -> str:
        if not unit_line:
            return self.unit
        unit_line = unit_line.strip().lower()
        if "per 1m" in unit_line or "per 1 m" in unit_line:
            return "per million tokens"
        if "per m token" in unit_line:
            return "per million tokens"
        if "per million" in unit_line:
            return "per million tokens"
        return unit_line


register_provider(NscaleScraper.provider_name, NscaleScraper)
