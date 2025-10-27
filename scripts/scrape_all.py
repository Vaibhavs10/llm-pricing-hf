#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_pricing import list_providers
from llm_pricing.registry import get_provider_scraper
import llm_pricing.providers  # noqa: F401


DEFAULT_REPO_ID = "reach-vb/inference-provider-pricing"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape provider pricing and optionally upload to Hugging Face.")
    parser.add_argument(
        "--upload",
        action="store_true",
        help=f"Upload the generated pricing_data.json to the {DEFAULT_REPO_ID} dataset repository.",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help="Target Hugging Face dataset repo id (default: %(default)s).",
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Custom commit message when uploading to Hugging Face.",
    )
    return parser.parse_args()


def upload_to_hf(output_path: Path, repo_id: str, commit_message: str | None) -> None:
    from huggingface_hub import HfApi

    api = HfApi()
    message = commit_message or f"Update pricing_data.json ({datetime.now(timezone.utc).isoformat(timespec='seconds')})"
    print(f"Uploading {output_path} to {repo_id}…")
    api.upload_file(
        path_or_fileobj=str(output_path),
        path_in_repo=output_path.name,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=message,
    )
    print("Upload complete.")


def main() -> None:
    args = parse_args()

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

    if args.upload:
        try:
            upload_to_hf(output_path, args.repo_id, args.commit_message)
        except Exception as exc:  # pragma: no cover - surfaced to CLI
            print(f"Failed to upload to Hugging Face: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
