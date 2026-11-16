"""Haftalik bulten icerigini Supabase gecmisinden uretir.

Neden Supabase: GitHub Actions Postgres'i her calismada sifirlanir; gecmis
yalnizca Supabase'de kalici (ayni gerekce alert_changes_supabase.py icin de gecerli).

Cikti: data/bulten_payload.json  ->  POST /api/bulten-gonder govdesi

Kullanim:
    python scripts/bulten_icerik.py --out data/bulten_payload.json --days 7
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from alert_changes_supabase import dsn_from_env  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "bulten_payload.json"))
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    out_path = Path(args.out)
    dsn = dsn_from_env()
    if not dsn:
        print("SUPABASE baglantisi yok -> bos rapor yazildi")
        out_path.write_text(json.dumps({"empty": True, "items": []}, ensure_ascii=False), encoding="utf-8")
        return 0

    try:
        import psycopg
    except ImportError:
        print("psycopg yok -> bos rapor")
        out_path.write_text(json.dumps({"empty": True, "items": []}, ensure_ascii=False), encoding="utf-8")
        return 0

    # Son N gunun fiyat degisimleri: her model+kalem icin ilk ve son gozlem.
    sql = """
        with win as (
          select model_key, price_dimension,
                 first_value(amount) over w as first_amt,
                 last_value(amount)  over w as last_amt,
                 min(observed_at)    over w as first_at,
                 max(observed_at)    over w as last_at,
                 row_number()        over (partition by model_key, price_dimension order by observed_at desc) as rn
          from price_history
          where observed_at >= now() - make_interval(days => %s)
            and status = 'approved'
          window w as (partition by model_key, price_dimension order by observed_at
                       rows between unbounded preceding and unbounded following)
        )
        select model_key, price_dimension, first_amt, last_amt, first_at, last_at
        from win where rn = 1
    """

    items = []
    try:
        with psycopg.connect(dsn, connect_timeout=25) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (args.days,))
                for model_key, dim, first_amt, last_amt, _fa, _la in cur.fetchall():
                    if dim not in ("input", "output"):
                        continue
                    first_amt = float(first_amt or 0)
                    last_amt = float(last_amt or 0)
                    if first_amt <= 0:
                        continue
                    pct = (last_amt - first_amt) / first_amt * 100
                    if abs(pct) < 1.0:
                        continue
                    items.append({
                        "model": str(model_key),
                        "change_pct": round(pct, 1),
                        "old_price": round(first_amt, 4),
                        "new_price": round(last_amt, 4),
                        "direction": "up" if pct > 0 else "down",
                    })
    except Exception as exc:  # noqa: BLE001
        print(f"Supabase okunamadi: {str(exc)[:150]}")
        out_path.write_text(json.dumps({"empty": True, "items": []}, ensure_ascii=False), encoding="utf-8")
        return 0

    # En buyuk hareketler onde; en fazla 12 satir.
    items.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    items = items[:12]

    if not items:
        payload = {"empty": True, "items": [],
                   "subject": "TokenMaliyet: bu hafta fiyat değişimi yok"}
    else:
        ups = sum(1 for i in items if i["direction"] == "up")
        downs = len(items) - ups
        head = (
            f"Bu hafta {len(items)} fiyat hareketi: {downs} düşüş, {ups} artış."
            if downs >= ups else
            f"Bu hafta {len(items)} fiyat hareketi: {ups} artış, {downs} düşüş."
        )
        payload = {
            "empty": False,
            "subject": f"TokenMaliyet haftalık rapor: {len(items)} fiyat hareketi",
            "headline": head,
            "items": items,
            "note": "Fiyatlar liste fiyatıdır; vergi ve indirimler hariçtir.",
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] {len(items)} hareket -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
