from __future__ import annotations

import unicodedata
from typing import Dict, List, Sequence

from ..registry import register_provider
from .base import ModelPricing, ProviderScraper


class CerebrasScraper(ProviderScraper):
    """Query the Cerebras pricing Sanity CMS page for developer tier per-model USD token rates."""

    provider_name = "cerebras"
    source_url = "https://www.cerebras.ai/pricing"

    _CMS_QUERY_URL = "https://e4qjo92p.apicdn.sanity.io/v2025-02-19/data/query/production"
    _GROQ_QUERY = r'''
*[_type=="page" && slug.current=="pricing"][0]{
  slices[]{
    _type,
    body[]{
      ...,
      _type == "table" => {
        _type,
        rows[]{
          cells
        }
      },
      _type == "block" => {
        _type,
        style,
        children[]{
          text
        }
      }
    }
  }
}
'''

    _MODEL_MAP: Dict[str, str] = {
        "GPT OSS 120B": "openai/gpt-oss-120b",
        "Llama 4 Scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        "Llama 3.1 8B": "meta-llama/Llama-3.1-8B-Instruct",
        "Llama 3.3 70B": "meta-llama/Llama-3.3-70B-Instruct",
        "Qwen 3 32B": "Qwen/Qwen3-32B",
        "Qwen 3 235B Instruct": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "Qwen 3 235B Thinking": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "Qwen 3 480B Coder": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    }

    def fetch_pricing(self) -> Sequence[ModelPricing]:
        payload = self.get(self._CMS_QUERY_URL, params={"query": self._GROQ_QUERY})
        data = payload.json()
        page = data.get("result")
        if not page:
            raise ValueError("Cerebras pricing query returned no results.")
        if isinstance(page, list):
            page = page[0]

        table_rows, footnotes = self._extract_table_rows(page)
        if not table_rows:
            raise ValueError("Unable to locate Cerebras developer pricing table.")

        results: List[ModelPricing] = []
        for cells in table_rows:
            if len(cells) < 4:
                continue
            model_label = cells[0]
            speed = cells[1]
            input_text = cells[2]
            output_text = cells[3]

            base_name, markers = self._strip_footnotes(model_label)
            canonical_name = self._MODEL_MAP.get(base_name)
            if not canonical_name:
                canonical_name = self.canonicalize_model_name(base_name)
            if not canonical_name:
                continue

            input_price = self.normalize_price(input_text)
            output_price = self.normalize_price(output_text)
            if input_price is None and output_price is None:
                continue

            notes_parts: List[str] = []
            if speed:
                notes_parts.append(f"speed: {speed}")
            for marker in markers:
                footnote = footnotes.get(marker)
                if footnote:
                    notes_parts.append(f"{marker} {footnote}")
            if canonical_name != base_name:
                notes_parts.append(f"original label: {model_label}")

            results.append(
                ModelPricing(
                    provider=self.provider_name,
                    model=canonical_name,
                    input_price_per_million=input_price,
                    output_price_per_million=output_price,
                    currency=self.currency,
                    unit=self.unit,
                    source_url=self.source_url,
                    notes="; ".join(notes_parts) if notes_parts else None,
                )
            )

        return results

    def _extract_table_rows(self, page: dict) -> tuple[list[list[str]], dict[str, str]]:
        rows: list[list[str]] = []
        footnotes: dict[str, str] = {}

        for slice_ in page.get("slices", []):
            if slice_.get("_type") != "textSlice":
                continue
            for block in slice_.get("body", []):
                block_type = block.get("_type")
                if block_type == "table":
                    for idx, row in enumerate(block.get("rows", [])):
                        cells = [self._clean_text(cell) for cell in row.get("cells", [])]
                        if idx == 0:
                            # Skip header row
                            continue
                        rows.append(cells)
                elif block_type == "block":
                    text = self._clean_text("".join(child.get("text", "") for child in block.get("children", [])))
                    if text.startswith("*"):
                        marker, remainder = self._split_marker(text)
                        if marker and remainder:
                            footnotes[marker] = remainder
        return rows, footnotes

    @staticmethod
    def _clean_text(value: str | None) -> str:
        if not value:
            return ""
        cleaned = "".join(
            ch
            for ch in value
            if unicodedata.category(ch) not in {"Cf", "Cc"}
        )
        return cleaned.replace("\xa0", " ").strip()

    @staticmethod
    def _strip_footnotes(label: str) -> tuple[str, list[str]]:
        if not label:
            return "", []
        base = label.strip()
        markers: list[str] = []
        while base.endswith("*"):
            star_count = len(base) - len(base.rstrip("*"))
            marker = "*" * star_count
            markers.append(marker)
            base = base.rstrip("*").rstrip()
        return base, markers

    @staticmethod
    def _split_marker(text: str) -> tuple[str, str]:
        idx = 0
        while idx < len(text) and text[idx] == "*":
            idx += 1
        marker = text[:idx]
        remainder = text[idx:].strip()
        return marker, remainder


register_provider(CerebrasScraper.provider_name, CerebrasScraper)
