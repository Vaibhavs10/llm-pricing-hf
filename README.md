# LLM Pricing Scrapers

Collect per-million-token input/output pricing for selected Hugging Face inference providers by scraping their official pricing pages.

## Requirements

- Python 3.9 – 3.12
- Poetry (optional) or `pip` for dependencies

Install dependencies with Poetry:

```bash
poetry install
```

Or with `pip`:

```bash
python3 -m pip install -r requirements.txt
```

> Note: this project declares dependencies in `pyproject.toml`; generate a `requirements.txt` with `poetry export` if you prefer `pip` only workflows.

## Usage

Run all available scrapers and persist their output to `pricing_data.json`:

```bash
python3 scripts/scrape_all.py
```

The script instantiates every registered provider scraper and aggregates their `ModelPricing` results into a single JSON list. Each record contains:

- `provider` – provider slug from Hugging Face
- `model` – provider-specific model or plan name
- `input_price_per_million` / `output_price_per_million` – numeric USD prices when available
- `unit` and `currency`
- `source_url`
- optional `notes`

## Current Coverage

Scrapers are implemented for:

- Cerebras
- Cohere
- Fireworks.ai
- Groq
- Hyperbolic
- Nebius
- Novita
- Nscale
- PublicAI (Inference.net)
- SambaNova
- Scaleway
- Together AI
- Zhipu (zai-org)

Each scraper uses static HTML parsing or embedded JSON extraction tailored to the provider's public pricing page.

### TODO

Scrapers still need to be implemented for: Hugging Face Inference Infrastructure.

## Extending

1. Create a new module in `llm_pricing/scrapers/` with a subclass of `ProviderScraper`.
2. Register the scraper by calling `register_provider` in the module body.
3. Import the module in `llm_pricing/providers.py` so it is discoverable.
4. Add provider-specific parsing logic that returns `ModelPricing` instances.

Run `python3 scripts/scrape_all.py` to verify the new provider integrates correctly.
