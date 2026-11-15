"""Ses / gorsel / video uretim maliyeti hesaplama.

Neden: rapor 8. tur arastirmasi (ARASTIRMA_VRAM_MEDYA.md) ses maliyeti
hesaplayicisinin en yuksek ROI'li ozellik oldugunu gosterdi:
  - ElevenLabs affiliate %22 (VRAM/GPU tarafinda %3)
  - TR'de "seslendirme yapay zeka" aramasi 51.5, "vram hesaplama" 0.0
  - Rekabet tek sayfalik ve markasiz

Fiyatlar data/media_prices.json icinde; her kayit kaynak URL tasir.
Uydurma fiyat YOK: dosyada olmayan model hesaplanmaz.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = ROOT / "data" / "media_prices.json"


@dataclass(frozen=True)
class MediaPrice:
    provider: str
    model: str
    unit: str
    usd_per_unit: float
    source: str
    note: str

    @property
    def key(self) -> str:
        return f"{self.provider}|{self.model}"


def load_prices() -> dict[str, list[MediaPrice]]:
    """Fiyat dosyasini okur. Dosya yoksa bos sozluk doner (uydurma yok)."""
    if not DATA_FILE.exists():
        return {}
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    out: dict[str, list[MediaPrice]] = {}
    for group in ("tts", "stt", "image", "video"):
        items = []
        for r in raw.get(group, []):
            items.append(MediaPrice(
                provider=r["provider"],
                model=r["model"],
                unit=r["unit"],
                usd_per_unit=float(r["usd_per_unit"]),
                source=r["source"],
                note=r.get("note", ""),
            ))
        out[group] = items
    return out


def options_for(group: str) -> list[dict]:
    """Select icin {value, label} listesi."""
    return [
        {"value": p.key, "label": f"{p.provider} · {p.model}", "unit": p.unit,
         "usd_per_unit": p.usd_per_unit, "note": p.note, "source": p.source}
        for p in load_prices().get(group, [])
    ]


def cost(group: str, key: str, quantity: float) -> dict | None:
    """Belirli bir miktar icin USD maliyet.

    quantity birimi modele gore degisir:
      tts  -> 1000 karakter sayisi (unit "1K karakter") veya 1M karakter
      stt  -> dakika veya saat
      image-> gorsel adedi
      video-> saniye
    Birim uyumsuzlugu olursa None doner; cagiran uygun birimle cagirmali.
    """
    for p in load_prices().get(group, []):
        if p.key != key:
            continue
        q = max(0.0, float(quantity))
        if group == "tts" or group == "stt":
            # unit "1K karakter" / "1M karakter" / "dakika" / "saat"
            if "1K" in p.unit:
                units = q / 1000.0
            elif "1M" in p.unit:
                units = q / 1_000_000.0
            else:
                units = q
        else:
            units = q
        return {
            "provider": p.provider,
            "model": p.model,
            "unit": p.unit,
            "usd_per_unit": p.usd_per_unit,
            "quantity": q,
            "units": units,
            "usd": units * p.usd_per_unit,
            "source": p.source,
        }
    return None


def compare(group: str, quantity: float) -> list[dict]:
    """Ayni miktar icin tum secenekleri fiyata gore sirali dondur."""
    rows = []
    for p in load_prices().get(group, []):
        r = cost(group, p.key, quantity)
        if r:
            rows.append(r)
    return sorted(rows, key=lambda r: r["usd"])
