"""Somut GPU fiyat toplayicilari.

Her biri resmi kaynaktan okur. Fiyat yoksa bos liste doner (sahte fiyat uretilmez).
"""
from __future__ import annotations

import json
import re
from decimal import Decimal

from .gpu_base import GpuQuote, GpuSnapshot, _get, now_iso, save_snapshot, strip_tags, vram_of


def _hash(quotes: list[GpuQuote]) -> str:
    from .base import hash_payload

    return hash_payload([
        {"m": q.gpu_model, "p": str(q.price_per_hour), "k": q.price_kind,
         "c": q.gpu_count, "r": q.region}
        for q in quotes
    ])


class RunpodGpuCollector:
    """Runpod resmi GraphQL API: securePrice (on-demand) ve communityPrice."""

    slug = "runpod"
    name = "Runpod"
    website = "https://www.runpod.io"
    pricing_url = "https://www.runpod.io/pricing"
    kind = "cloud"
    endpoint = "https://api.runpod.io/graphql"

    QUERY = {"query": "query { gpuTypes { id displayName memoryInGb securePrice communityPrice } }"}

    def collect(self) -> GpuSnapshot:
        text, final_url = _get(self.endpoint, json_body=self.QUERY, timeout=40)
        payload = json.loads(text)
        gpus = ((payload.get("data") or {}).get("gpuTypes")) or []

        quotes: list[GpuQuote] = []
        for g in gpus:
            name = (g.get("displayName") or g.get("id") or "").strip()
            if not name:
                continue
            vram = g.get("memoryInGb") or vram_of(name)
            for field, kind in (("securePrice", "on_demand"), ("communityPrice", "community")):
                price = g.get(field)
                try:
                    value = Decimal(str(price))
                except Exception:
                    continue
                if value <= 0:
                    continue
                quotes.append(GpuQuote(
                    gpu_model=name, price_per_hour=value, price_kind=kind,
                    vram_gb=int(vram) if vram else None,
                    notes="Runpod GraphQL fiyati (vergi haric)",
                    raw={"id": g.get("id"), "field": field, "value": str(price)},
                ))

        return GpuSnapshot(
            provider_slug=self.slug, provider_name=self.name, website=self.website,
            pricing_url=self.pricing_url, kind=self.kind, fetched_at=now_iso(),
            content_hash=_hash(quotes), snapshot_path=save_snapshot(self.slug, text),
            quotes=quotes,
        )


class HyperstackGpuCollector:
    """Hyperstack resmi GPU sayfalari: 'Rent NVIDIA H100 SXM at $3.20/hr'."""

    slug = "hyperstack"
    name = "Hyperstack"
    website = "https://www.hyperstack.cloud"
    pricing_url = "https://www.hyperstack.cloud/gpu-pricing"
    kind = "cloud"

    PAGES = [
        ("https://www.hyperstack.cloud/nvidia-h100-sxm", "H100 SXM", 80),
        ("https://www.hyperstack.cloud/nvidia-h100-pcie", "H100 PCIe", 80),
        ("https://www.hyperstack.cloud/nvidia-h200-sxm", "H200 SXM", 141),
        ("https://www.hyperstack.cloud/nvidia-a100-sxm", "A100 SXM", 80),
        ("https://www.hyperstack.cloud/nvidia-a100", "A100 PCIe", 80),
        ("https://www.hyperstack.cloud/nvidia-l40", "L40", 48),
        ("https://www.hyperstack.cloud/nvidia-rtx-a6000", "RTX A6000", 48),
    ]

    PATTERN = re.compile(r"\$\s?([0-9]+(?:\.[0-9]+)?)\s*/\s*(?:hr|hour)", re.I)
    GENERIC = re.compile(r"\$\s?([0-9]+(?:\.[0-9]+)?)\s*/\s*hr", re.I)

    def collect(self) -> GpuSnapshot:
        quotes: list[GpuQuote] = []
        parts: list[str] = []
        for url, model, vram in self.PAGES:
            try:
                html, final_url = _get(url)
            except Exception:
                continue
            parts.append(html)
            text = strip_tags(html)
            first = model.split(" ")[0]
            m = re.search(
                r"Rent\s+NVIDIA\s+" + re.escape(first) + r"[^.]{0,120}?\$\s?([0-9.]+)\s*/\s*hr",
                text, re.I,
            )
            if not m:
                m = self.GENERIC.search(text)
            if not m:
                continue
            try:
                price = Decimal(m.group(1))
            except Exception:
                continue
            if price <= 0:
                continue
            quotes.append(GpuQuote(
                gpu_model=model, price_per_hour=price, vram_gb=vram,
                notes="Hyperstack on-demand liste fiyati",
                raw={"url": final_url, "matched": m.group(0)[:120]},
            ))

        return GpuSnapshot(
            provider_slug=self.slug, provider_name=self.name, website=self.website,
            pricing_url=self.pricing_url, kind=self.kind, fetched_at=now_iso(),
            content_hash=_hash(quotes),
            snapshot_path=save_snapshot(self.slug, "\n".join(parts)), quotes=quotes,
        )

class DataCrunchGpuCollector:
    """DataCrunch fiyat tablosu: '1x H100 SXM5 80GB ... $2.544/h ... $1.272/h' (on-demand / spot)."""

    slug = "datacrunch"
    name = "DataCrunch"
    website = "https://datacrunch.io"
    pricing_url = "https://datacrunch.io/pricing"
    kind = "cloud"

    # strip_tags ciktisi "·" ve &nbsp; kaynakli bosluklari karistirir:
    #   1x GB300 SXM6 288GB· · · ·32· · · ·225 GB· · · ·288 GB· · · ·$13.86/h· · · ·$6.929/h
    SEP = r"[\s\u00b7]+"
    ROW = re.compile(
        r"1x" + SEP + r"(?P<model>[A-Za-z0-9][A-Za-z0-9 ]*?(?:\s+\d{2,3}GB)?)" + SEP +
        r"(?:\d+" + SEP + r")?"
        r"(?:\d+\s*GB" + SEP + r")?"
        r"(?P<vram>\d{2,3})\s*GB" + SEP +
        r"\$\s?(?P<od>[0-9.]+)\s*/\s*h"
        r"(?:" + SEP + r"\$\s?(?P<spot>[0-9.]+)\s*/\s*h)?",
        re.I,
    )

    def collect(self) -> GpuSnapshot:
        html, final_url = _get(self.pricing_url)
        text = strip_tags(html)
        quotes: list[GpuQuote] = []
        for m in self.ROW.finditer(text):
            model = re.sub(r"\s+", " ", m.group("model")).strip(" \u00b7")
            vram_raw = m.group("vram")
            if not model or not vram_raw:
                continue
            vram = int(vram_raw)
            try:
                od = Decimal(m.group("od"))
            except Exception:
                continue
            if od <= 0:
                continue
            # model adi cogu satirda VRAM iceriyor ("GB300 SXM6 288GB"); tekrar eklemeyin.
            label = model if re.search(r"\d+GB$", model, re.I) else model + " " + str(vram) + "GB"
            quotes.append(GpuQuote(
                gpu_model=label, price_per_hour=od, vram_gb=vram, price_kind="on_demand",
                notes="DataCrunch on-demand", raw={"raw": m.group(0)[:160]},
            ))
            spot = m.group("spot")
            if spot:
                try:
                    sp = Decimal(spot)
                except Exception:
                    sp = None
                if sp and sp > 0:
                    quotes.append(GpuQuote(
                        gpu_model=label, price_per_hour=sp, vram_gb=vram, price_kind="spot",
                        notes="DataCrunch spot", raw={"raw": m.group(0)[:160]},
                    ))

        return GpuSnapshot(
            provider_slug=self.slug, provider_name=self.name, website=self.website,
            pricing_url=self.pricing_url, kind=self.kind, fetched_at=now_iso(),
            content_hash=_hash(quotes), snapshot_path=save_snapshot(self.slug, html),
            quotes=quotes,
        )


class LambdaGpuCollector:
    """Lambda 1-Click Clusters tablosu: PRICE/GPU/HR + minimum sure (2 hafta+)."""

    slug = "lambda"
    name = "Lambda"
    website = "https://lambda.ai"
    pricing_url = "https://lambda.ai/pricing"
    kind = "cloud"

    # strip_tags sonrasi satir bicimi:
    #   NVIDIA H100·2 weeks – 1 year·16·$6.16
    ROW = re.compile(
        r"NVIDIA\s+(?P<model>HGX B200|H100|B200|H200|GH200)\s*\u00b7\s*"
        r"(?P<duration>[^\u00b7]{2,40}?)\s*\u00b7\s*(?P<count>\d+)\+?\s*\u00b7\s*"
        r"\$\s?(?P<price>[0-9.]+)",
        re.I,
    )

    # Instance satiri: NVIDIA H100 SXM·80 GB·104·900 GiB·11 TiB SSD·$4.69
    INSTANCE = re.compile(
        r"NVIDIA\s+(?P<model>[A-Za-z0-9 ]+?)\s*\u00b7\s*(?P<vram>\d{2,3})\s*GB"
        r"(?:\s*\u00b7[^\$]{0,80}?)\$\s?(?P<price>[0-9.]+)",
        re.I,
    )

    def collect(self) -> GpuSnapshot:
        html, final_url = _get(self.pricing_url)
        text = strip_tags(html)
        quotes: list[GpuQuote] = []
        seen: set[tuple[str, str]] = set()

        # 1) 1-Click Clusters (rezerve, minimum sure)
        for m in self.ROW.finditer(text):
            model = m.group("model").strip()
            duration = m.group("duration").strip()
            count = int(m.group("count"))
            key = (model, duration)
            if key in seen:
                continue
            seen.add(key)
            try:
                price = Decimal(m.group("price"))
            except Exception:
                continue
            if price <= 0:
                continue
            min_hours = Decimal("336") if "2 weeks" in duration.lower() else None
            quotes.append(GpuQuote(
                gpu_model=model + " (" + str(count) + "+ GPU kluster)",
                price_per_hour=price, price_kind="reserved", gpu_count=count,
                min_lease_hours=min_hours,
                notes="Lambda 1-Click Clusters; sure: " + duration,
                raw={"raw": m.group(0)[:180]},
            ))

        # 2) Instance fiyatlari (on-demand, saatlik)
        best: dict[tuple[str, int], Decimal] = {}
        for m in self.INSTANCE.finditer(text):
            model = re.sub(r"\s+", " ", m.group("model")).strip()
            vram = int(m.group("vram"))
            try:
                price = Decimal(m.group("price"))
            except Exception:
                continue
            if price <= 0:
                continue
            key = (model, vram)
            if key not in best or price < best[key]:
                best[key] = price
        for (model, vram), price in best.items():
            quotes.append(GpuQuote(
                gpu_model=model + " " + str(vram) + "GB", price_per_hour=price,
                vram_gb=vram, price_kind="on_demand",
                notes="Lambda on-demand instance (en dusuk konfigurasyon)",
                raw={"model": model, "vram": vram, "price": str(price)},
            ))

        return GpuSnapshot(
            provider_slug=self.slug, provider_name=self.name, website=self.website,
            pricing_url=self.pricing_url, kind=self.kind, fetched_at=now_iso(),
            content_hash=_hash(quotes), snapshot_path=save_snapshot(self.slug, html),
            quotes=quotes,
        )


class VastAiGpuCollector:
    """Vast.ai pazaryeri: bundle API medyan fiyatlari (dogrulanmis hostlar)."""

    slug = "vastai"
    name = "Vast.ai"
    website = "https://vast.ai"
    pricing_url = "https://vast.ai/pricing"
    kind = "marketplace"
    endpoint = "https://console.vast.ai/api/v0/bundles/?q=%7B%22verified%22%3A%7B%22eq%22%3Atrue%7D%7D"

    MIN_SAMPLES = 3

    def collect(self) -> GpuSnapshot:
        text, final_url = _get(self.endpoint, timeout=45)
        payload = json.loads(text)
        offers = payload.get("offers") or []

        buckets: dict[str, list[Decimal]] = {}
        for offer in offers:
            name = (offer.get("gpu_name") or "").strip()
            if not name:
                continue
            try:
                total = Decimal(str(offer.get("dph_total")))
                count = int(offer.get("num_gpus") or 1)
            except Exception:
                continue
            if total <= 0 or count <= 0:
                continue
            buckets.setdefault(name, []).append((total / count).quantize(Decimal("0.0001")))

        quotes: list[GpuQuote] = []
        for name, values in buckets.items():
            if len(values) < self.MIN_SAMPLES:
                continue
            values.sort()
            median = values[len(values) // 2]
            quotes.append(GpuQuote(
                gpu_model=name, price_per_hour=median, price_kind="community",
                vram_gb=vram_of(name),
                notes="Vast.ai medyan (dogrulanmis hostlar, " + str(len(values)) + " ilan)",
                raw={"samples": len(values), "min": str(values[0]), "max": str(values[-1])},
            ))

        return GpuSnapshot(
            provider_slug=self.slug, provider_name=self.name, website=self.website,
            pricing_url=self.pricing_url, kind=self.kind, fetched_at=now_iso(),
            content_hash=_hash(quotes), snapshot_path=save_snapshot(self.slug, text),
            quotes=quotes,
        )


GPU_COLLECTORS = [
    RunpodGpuCollector,
    HyperstackGpuCollector,
    DataCrunchGpuCollector,
    LambdaGpuCollector,
    VastAiGpuCollector,
]