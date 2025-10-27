from __future__ import annotations

import json
import re
from typing import Any, Iterable, Iterator

import requests

from bs4 import BeautifulSoup


NEXT_CHUNK_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\);', re.S)
HF_MODELS_URL = "https://huggingface.co/inference/models"
_HF_MODELS_CACHE: dict[str, list[str]] | None = None

_PAREN_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
HF_PROVIDER_ALIASES = {
    "zhipu": "zai-org",
    "hf-inference": "hf-inference",
}


def iter_next_data(html: str) -> Iterator[Any]:
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script"):
        text = script.get_text()
        if not text or "self.__next_f.push" not in text:
            continue
        for match in NEXT_CHUNK_PATTERN.finditer(text):
            payload = match.group(1)
            if not payload:
                continue
            try:
                _, json_escaped = payload.split(":", 1)
            except ValueError:
                continue
            json_str = bytes(json_escaped, "utf-8").decode("unicode_escape")
            try:
                yield json.loads(json_str)
            except json.JSONDecodeError:
                continue


def find_in_next_data(html: str, predicate) -> Any:
    for chunk in iter_next_data(html):
        result = _deep_find(chunk, predicate)
        if result is not None:
            return result
    return None


def _deep_find(obj: Any, predicate) -> Any:
    if predicate(obj):
        return obj
    if isinstance(obj, dict):
        for value in obj.values():
            found = _deep_find(value, predicate)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find(item, predicate)
            if found is not None:
                return found
    return None


def clean_money(text: str) -> float | None:
    digits = "".join(ch for ch in text if ch in "0123456789.")
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def extract_table_rows(soup: BeautifulSoup, header_labels: Iterable[str]) -> list[list[str]]:
    headers = [label.lower() for label in header_labels]
    rows: list[list[str]] = []
    for table in soup.find_all("table"):
        th_text = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers or all(label in th_text for label in headers):
            body = table.find("tbody")
            if not body:
                continue
            for tr in body.find_all("tr"):
                rows.append([td.get_text(" ", strip=True) for td in tr.find_all("td")])
    return rows


def _normalize_name(value: str) -> str:
    value = _PAREN_RE.sub(" ", value or "")
    value = _NON_ALNUM_RE.sub(" ", value.lower())
    return " ".join(value.split())


def _load_hf_models() -> dict[str, list[str]]:
    global _HF_MODELS_CACHE
    if _HF_MODELS_CACHE is not None:
        return _HF_MODELS_CACHE

    try:
        response = requests.get(HF_MODELS_URL, headers={"User-Agent": "llm-pricing-scraper/0.1 (+https://huggingface.co)"}, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        _HF_MODELS_CACHE = {}
        return _HF_MODELS_CACHE

    soup = BeautifulSoup(response.text, "lxml")
    data: dict[str, list[str]] = {}
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        model = cells[0].get_text(" ", strip=True)
        provider = cells[1].get_text(" ", strip=True).lower()
        if not model or not provider:
            continue
        data.setdefault(provider, []).append(model)

    _HF_MODELS_CACHE = data
    return _HF_MODELS_CACHE


def get_hf_models_for_provider(provider: str) -> list[str]:
    models = _load_hf_models()
    provider_key = HF_PROVIDER_ALIASES.get(provider.lower(), provider.lower())
    return models.get(provider_key, [])


def _build_provider_canonical_data(provider: str) -> list[tuple[str, str, str, set[str]]]:
    data: list[tuple[str, str, str, set[str]]] = []
    for model in get_hf_models_for_provider(provider):
        norm_full = _normalize_name(model)
        last_segment = model.split("/")[-1] if "/" in model else model
        norm_last = _normalize_name(last_segment)
        tokens = set(norm_last.split())
        data.append((model, norm_full, norm_last, tokens))
    return data


_CANONICAL_CACHE: dict[str, list[tuple[str, str, str, set[str]]]] = {}


def canonicalize_model_name(provider: str, raw_name: str) -> str | None:
    provider_key = HF_PROVIDER_ALIASES.get((provider or "").lower(), (provider or "").lower())
    if provider_key not in _CANONICAL_CACHE:
        _CANONICAL_CACHE[provider_key] = _build_provider_canonical_data(provider_key)

    canonical_options = _CANONICAL_CACHE.get(provider_key, [])
    if not canonical_options:
        return None

    norm_raw = _normalize_name(raw_name)
    if not norm_raw:
        return None

    raw_tokens = set(norm_raw.split())
    best_match: str | None = None
    best_score = 0.0

    for model, norm_full, norm_last, token_set in canonical_options:
        if norm_raw == norm_full or norm_raw == norm_last:
            return model
        if norm_raw in norm_full or norm_raw in norm_last:
            return model
        if norm_full in norm_raw or norm_last in norm_raw:
            return model
        if raw_tokens and token_set:
            intersection = len(raw_tokens & token_set)
            if not intersection:
                continue
            score = intersection / len(raw_tokens)
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = model

    return best_match
