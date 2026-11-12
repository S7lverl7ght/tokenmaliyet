from __future__ import annotations

from sqlalchemy import select

from .db import SessionLocal
from .models import DataSource, Provider

PROVIDERS = [
    ("openai", "OpenAI", "https://openai.com", "https://openai.com/api/pricing/"),
    ("anthropic", "Anthropic", "https://www.anthropic.com", "https://www.anthropic.com/pricing"),
    ("gemini", "Google Gemini", "https://ai.google.dev", "https://ai.google.dev/gemini-api/docs/pricing"),
    ("deepseek", "DeepSeek", "https://www.deepseek.com", "https://api-docs.deepseek.com/quick_start/pricing"),
    ("openrouter", "OpenRouter", "https://openrouter.ai", "https://openrouter.ai/api/v1/models"),
]

SOURCES = {
    "openai": ("OpenAI API Pricing Page", "official_doc", "http_html", "direct"),
    "anthropic": ("Anthropic API Pricing Page", "official_doc", "http_html", "direct"),
    "gemini": ("Gemini API Pricing Docs", "official_doc", "http_html", "direct"),
    "deepseek": ("DeepSeek API Pricing Docs", "official_doc", "http_html", "direct"),
    "openrouter": ("OpenRouter Models API", "official_api", "http_json", "marketplace"),
}


def run() -> None:
    with SessionLocal() as db:
        for slug, name, site, pricing in PROVIDERS:
            provider = db.scalar(select(Provider).where(Provider.slug == slug))
            if provider is None:
                provider = Provider(slug=slug, name=name, website=site, pricing_url=pricing)
                db.add(provider)
                db.flush()
            label, stype, method, channel = SOURCES[slug]
            existing = db.scalar(select(DataSource).where(DataSource.source_url == pricing))
            if existing is None:
                db.add(
                    DataSource(
                        provider_id=provider.id, label=label, source_url=pricing, source_type=stype,
                        retrieval_method=method, sales_channel=channel, is_official=True,
                    )
                )
        db.commit()
        print(f"seeded {len(PROVIDERS)} providers and sources")


if __name__ == "__main__":
    run()
