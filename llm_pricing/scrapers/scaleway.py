from __future__ import annotations

from typing import Dict, List, Sequence

from bs4 import BeautifulSoup

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class ScalewayScraper(ProviderScraper):
    """Parse the Generative API pricing table and convert EUR rates to USD per million tokens."""

    provider_name = "scaleway"
    source_url = "https://www.scaleway.com/en/pricing/model-as-a-service/#generative-apis"

    _MODEL_MAP: Dict[str, str] = {
        "qwen3-235b-a22b-instruct-2507": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "gpt-oss-120b": "openai/gpt-oss-120b",
        "gemma-3-27b-it": "google/gemma-3-27b-it",
        "deepseek-r1-distill-llama-70b": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "qwen3-coder-30b-a3b-instruct": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "qwen2.5-coder-32b-instruct": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "llama-3.1-8b-instruct": "meta-llama/Llama-3.1-8B-Instruct",
        "llama-3.3-70b-instruct": "meta-llama/Llama-3.3-70B-Instruct",
    }

    _FX_URL = "https://open.er-api.com/v6/latest/EUR"

    def __init__(self, session=None) -> None:
        super().__init__(session=session)
        self._eur_to_usd: float | None = None

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        response = self.get(self.source_url)
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.find("table")
        if table is None or table.tbody is None:
            raise ValueError("Unable to locate Scaleway Generative API pricing table.")

        rate = self._get_eur_to_usd_rate()
        results: List[ModelPricing] = []
        for tr in table.tbody.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue

            slug = cells[0].strip()
            canonical = self._MODEL_MAP.get(slug)
            if not canonical:
                continue

            input_eur = self._parse_euro_price(cells[3])
            output_eur = self._parse_euro_price(cells[4])
            if input_eur is None and output_eur is None:
                continue

            input_usd = self._convert_to_usd(input_eur, rate)
            output_usd = self._convert_to_usd(output_eur, rate)

            notes_parts = [f"task: {cells[2]}"]
            notes_parts.append(f"original EUR input {cells[3]}")
            notes_parts.append(f"original EUR output {cells[4]}")
            notes_parts.append(f"EUR→USD rate {rate:.6f}")

            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical,
                    input_price_per_million=input_usd,
                    output_price_per_million=output_usd,
                    currency=self.currency,
                    unit=self.unit,
                    source_url=self.source_url,
                    notes="; ".join(notes_parts),
                )
            )

        return results

    def _parse_euro_price(self, text: str) -> float | None:
        if not text:
            return None
        normalized = text.lower()
        if "million tokens" not in normalized:
            return None
        if "free" in normalized:
            return 0.0
        return self.normalize_price(text)

    def _get_eur_to_usd_rate(self) -> float:
        if self._eur_to_usd is not None:
            return self._eur_to_usd
        response = self.get(self._FX_URL)
        data = response.json()
        try:
            if data.get("result") != "success":
                raise KeyError("result")
            rate = float(data["rates"]["USD"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Failed to retrieve EUR→USD exchange rate.") from exc
        self._eur_to_usd = rate
        return rate

    @staticmethod
    def _convert_to_usd(value: float | None, rate: float) -> float | None:
        if value is None:
            return None
        return round(value * rate, 6)


register_provider(ScalewayScraper.provider_name, ScalewayScraper)
