#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_pricing import list_providers
from llm_pricing.registry import get_provider_scraper
import llm_pricing.providers  # noqa: F401


def main() -> None:
    session = requests.Session()
    all_results = []
    for provider_name in list_providers():
        scraper_cls = get_provider_scraper(provider_name)
        scraper = scraper_cls(session=session)
        print(f"Scraping {provider_name}…")
        entries = scraper.scrape()
        for entry in entries:
            all_results.append(entry.__dict__)
        print(f"  {len(entries)} pricing entries captured.")

    output_path = Path("pricing_data.json")
    output_path.write_text(json.dumps(all_results, indent=2))
    print(f"Wrote {len(all_results)} records to {output_path}")


if __name__ == "__main__":
    main()
