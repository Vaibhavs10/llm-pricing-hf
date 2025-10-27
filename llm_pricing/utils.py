from __future__ import annotations

import json
import re
from typing import Any, Iterable, Iterator

from bs4 import BeautifulSoup


NEXT_CHUNK_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\);', re.S)


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
