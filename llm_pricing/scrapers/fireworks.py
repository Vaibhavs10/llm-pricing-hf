from __future__ import annotations

import re
from typing import List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from ..utils import match_hf_models
from .base import ModelPricing, ProviderScraper


INPUT_OUTPUT_PATTERN = re.compile(
    r"\$?(?P<input>\d+(?:\.\d+)?)\s*(?:/M|\sper)?\s*input(?:,|\s+)(?:\$?(?P<output>\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
SINGLE_PRICE_PATTERN = re.compile(r"\$?(?P<price>\d+(?:\.\d+)?)")


class FireworksScraper(ProviderScraper):
    """Parse tiered pricing table and map Fireworks tiers to HF model slugs."""

    provider_name = "fireworks-ai"
    source_url = "https://fireworks.ai/pricing"
    TIER_MODEL_MAP = {
        "DeepSeek V3 family": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-V3-0324",
            "deepseek-ai/DeepSeek-V3.1",
        ],
        "DeepSeek R1 0528": [
            "deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-R1-0528",
        ],
        "GLM-4.5": [
            "zai-org/GLM-4.5",
        ],
        "Meta Llama 3.1 405B": [
            "meta-llama/Llama-3.1-405B-Instruct",
        ],
        "Meta Llama 4 Maverick (Basic)": [
            "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        ],
        "Meta Llama 4 Scout (Basic)": [
            "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        ],
        "Qwen3 235B Family and GLM-4.5 Air": [
            "Qwen/Qwen3-235B-A22B",
            "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "Qwen/Qwen3-235B-A22B-Thinking-2507",
            "zai-org/GLM-4.5-Air",
        ],
        "Qwen3 30B and Qwen Coder Flash": [
            "Qwen/Qwen3-30B-A3B",
            "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        ],
        "Qwen3 Coder 480B": [
            "Qwen/Qwen3-Coder-480B-A35B-Instruct",
        ],
        "MoE 56.1B - 176B parameters (e.g. Mixtral 8x22B)": [
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
        ],
    }

    @staticmethod
    def _extract_prices(text: str) -> tuple[float | None, float | None]:
        if match := INPUT_OUTPUT_PATTERN.search(text):
            input_price = float(match.group("input"))
            output_str = match.group("output")
            output_price = float(output_str) if output_str else input_price
            return input_price, output_price
        if single := SINGLE_PRICE_PATTERN.search(text):
            value = float(single.group("price"))
            return value, value
        return None, None

    @staticmethod
    def _split_label(label: str) -> list[str]:
        cleaned = label.replace("Family", "")
        parts = re.split(r"\band\b|,|\/|\+|&", cleaned)
        return [part.strip() for part in parts if part.strip()]

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        tables = soup.find_all("table")
        if not tables:
            return []

        table = tables[0]
        entries: dict[str, ModelPricing] = {}
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            tier_label = cells[0].get_text(" ", strip=True)
            price_text = cells[1].get_text(" ", strip=True)

            input_price, output_price = self._extract_prices(price_text)
            if input_price is None and output_price is None:
                continue

            candidate_models = set(self.TIER_MODEL_MAP.get(tier_label, []))
            if not candidate_models:
                primary = self.canonicalize_model_name(tier_label)
                if primary:
                    candidate_models.add(primary)

            for part in self._split_label(tier_label):
                for match in match_hf_models(self.provider_name, part, min_score=0.75):
                    candidate_models.add(match)

            if not candidate_models:
                continue

            notes = f"tier: {tier_label}"
            for model in candidate_models:
                if model in entries:
                    continue
                entries[model] = ModelPricing(
                    provider=self.provider_name,
                    model=model,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit=self.unit,
                    source_url=self.source_url,
                    notes=notes,
                )

        return list(entries.values())


register_provider(FireworksScraper.provider_name, FireworksScraper)
