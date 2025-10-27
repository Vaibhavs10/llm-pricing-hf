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

To also upload the refreshed JSON to the `reach-vb/inference-provider-pricing` dataset repo on Hugging Face, provide the `--upload` flag (ensure your `HF_TOKEN` is configured locally):

```bash
python3 scripts/scrape_all.py --upload
```

Use `--repo-id` and `--commit-message` to override the defaults if needed.

### Scheduled automation with Hugging Face Jobs

You can schedule daily refreshes directly from the Hugging Face Hub CLI (`hf`). The command below follows the [Jobs guide](https://huggingface.co/docs/huggingface_hub/en/guides/jobs) and assumes you have logged in with `hf auth login`:

```bash
hf jobs scheduled run "0 8 * * *" python:3.11 \
  --secrets HF_TOKEN=${HF_TOKEN:?set HF_TOKEN} \
  --flavor cpu-basic \
  bash -lc "
    git clone https://huggingface.co/Vaibhavs10/llm-pricing-hf repo &&
    cd repo &&
    pip install -e . &&
    python scripts/scrape_all.py --upload
  "
```

Notes:

- The `HF_TOKEN` environment variable must be exported locally before running the command; the CLI forwards it as a secret so the scheduled job can clone/push. Make sure the token has write access to both `Vaibhavs10/llm-pricing-hf` and `reach-vb/inference-provider-pricing`.
- The cron expression is interpreted in UTC; adjust it if you want a different schedule.

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
