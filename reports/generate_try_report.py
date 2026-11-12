"""Kazanc urunu #1: Turkiye icin AI API maliyet karsilastirma raporu (Excel).

Sadece approved fiyatlar kullanilir; her satirda kaynak URL ve gozlem zamani bulunur.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import DataSource, ExchangeRate, Model, PriceObservation, Provider  # noqa: E402

# Calisma profilleri: tipik bir TR isletmesinin gercek kullanim karisimi
PROFILES = [
    ("Musteri destek botu (gunluk 2.000 sohbet)", 1_500_000, 400_000),   # input/output tokens / gun
    ("Kod asistani (10 gelistirici)", 3_000_000, 900_000),
    ("Dokuman ozetleme (gunluk 500 dosya)", 6_000_000, 800_000),
    ("Icerik uretimi (gunluk 200 blog)", 800_000, 1_600_000),
]

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
SUB_FILL = PatternFill("solid", fgColor="D9E2F3")


def _latest_by_dimension(rows):
    out = {}
    # Onayli kayitlar en yeniden eskiye siralidir. Ayni model+boyut icin DAIMA
    # standart/off-peak dilimi tercih edilir; peak fiyati raporda karistirilmaz.
    priority = {"off_peak": 0, "standard": 0, None: 0, "peak": 1}
    for obs, model, provider, source in rows:
        key = (obs.model_id, obs.price_dimension)
        current = out.get(key)
        if current is None or priority.get(obs.peak_period, 2) < priority.get(current[0].peak_period, 2):
            out[key] = (obs, model, provider, source)
    return out


def build() -> Path:
    with SessionLocal() as db:
        fx = db.scalars(
            select(ExchangeRate).where(ExchangeRate.quote_currency == "TRY").order_by(desc(ExchangeRate.effective_at))
        ).first()
        rate = float(fx.rate) if fx else 0.0

        rows = db.execute(
            select(PriceObservation, Model, Provider, DataSource)
            .join(Model, Model.id == PriceObservation.model_id)
            .join(Provider, Provider.id == Model.provider_id)
            .join(DataSource, DataSource.id == PriceObservation.source_id)
            .where(PriceObservation.status == "approved")
            .order_by(desc(PriceObservation.observed_at))
        ).all()
        latest = _latest_by_dimension(rows)

        # Sadece metin (token) modelleri: karsilastirma icin dogru kume
        by_model: dict[int, dict] = {}
        for (model_id, dimension), (obs, model, provider, source) in latest.items():
            if obs.normalized_usd_per_1m is None:
                continue
            if dimension not in ("input", "output", "cache_read"):
                continue
            entry = by_model.setdefault(
                model_id,
                {"model": model, "provider": provider, "source": source, "dims": {},
                 "observed_at": obs.observed_at, "peak": obs.peak_period == "peak"},
            )
            entry["dims"][dimension] = float(obs.normalized_usd_per_1m)

        # Sadece dogrudan (first-party) API fiyatlari: elma-elma karsilastirma
        direct = [
            e for e in by_model.values()
            if e["source"].sales_channel == "direct"
            and "input" in e["dims"] and "output" in e["dims"]
            # yalnizca metin/cikti modelleri: gorsel-TTS gibi birim karisikligi disarida kalir
            and not any(k in e["model"].canonical_id for k in ("image", "tts", "audio", "live", "omni", "transcribe", "robotics", "veo"))
        ]

        wb = Workbook()
        ws0 = wb.active
        ws0.title = "Ozet ve Tasarruf Firsatlari"
        ws0.column_dimensions["A"].width = 46
        ws0.column_dimensions["B"].width = 30
        ws0.column_dimensions["C"].width = 30
        ws0.column_dimensions["D"].width = 15
        ws0.column_dimensions["E"].width = 44

        def title(row: int, text: str) -> None:
            cell = ws0.cell(row=row, column=1, value=text)
            cell.font = Font(bold=True, size=13, color="1F3864")
            cell.fill = SUB_FILL

        title(1, "AI MALIYET MERKEZI - TURKIYE API MALIYET RAPORU")
        ws0.cell(row=2, column=1, value=f"Rapor tarihi: {dt.datetime.now().strftime('%d.%m.%Y %H:%M')}")
        ws0.cell(row=3, column=1, value=f"USD/TRY: {rate} (kaynak: {fx.source_url if fx else '-'}, "
                                        f"{fx.effective_at.date().isoformat() if fx else '-'})")
        ws0.cell(row=4, column=1, value=f"Onayli fiyat gozlemi: {sum(1 for _ in rows)} | "
                                        f"Dogrudan API modeli: {len(direct)} | Pazaryeri (OpenRouter) modeli: "
                                        f"{len(by_model) - len(direct)}")
        ws0.cell(row=6, column=1, value="Ayni is yuku, farkli model tercihleri (aylik TRY) - 100M girdi + 25M cikti token")
        ws0.cell(row=6, column=1).font = Font(bold=True)
        for col, head in enumerate(["Senaryo", "Mevcut (pahali)", "Alternatif", "Aylik fark", "Yillik kazanc"], start=1):
            c = ws0.cell(row=7, column=col, value=head)
            c.fill = HEADER_FILL
            c.font = Font(bold=True, color="FFFFFF")

        def price_of(model_id: str) -> tuple[float, float] | None:
            entry = next((e for e in direct if e["model"].canonical_id == model_id), None)
            if entry is None:
                return None
            return entry["dims"]["input"], entry["dims"]["output"]

        IN_TOK, OUT_TOK = 100_000_000, 25_000_000
        for idx, (label, cur, alt) in enumerate([
            ("Kod asistani - ust segment model", "claude-sonnet-4.5", "deepseek-v4-pro"),
            ("Dokuman analizi - pro segment", "gemini-3.1-pro-preview", "deepseek-v4-pro"),
            ("Icerik uretimi - premium model", "claude-opus-5.5", "gpt-6-1-sol"),
            ("Musteri destek - orta segment", "gemini-2.5-pro", "deepseek-flash"),
            ("Yuksek hacim - en ucuz cikis", "claude-sonnet-4.5", "gpt-6-luna"),
        ], start=8):
            a, b = price_of(cur), price_of(alt)
            if not a or not b:
                continue
            ca = (a[0] * IN_TOK + a[1] * OUT_TOK) / 1_000_000 * rate
            cb = (b[0] * IN_TOK + b[1] * OUT_TOK) / 1_000_000 * rate
            ws0.cell(row=idx, column=1, value=label)
            ws0.cell(row=idx, column=2, value=f"{cur}: {ca:,.0f} TRY")
            ws0.cell(row=idx, column=3, value=f"{alt}: {cb:,.0f} TRY")
            ws0.cell(row=idx, column=4, value=round(ca - cb)).number_format = "#,##0" 
            ws0.cell(row=idx, column=5, value=f"{round((ca - cb) * 12):,} TRY (%{round((1 - cb / ca) * 100)} tasarruf)")

        ws0.cell(row=14, column=1, value="Not: Fiyatlar resmi saglayici sayfalarindan otomatik toplanir, QA onayindan gecer. "
                                         "Kalite/gecikme farklari bu tabloda olculmez; tasarruf firsati olarak okunmalidir.")
        ws0.cell(row=14, column=1).font = Font(italic=True, size=9)

        ws = wb.create_sheet("Fiyat Karsilastirma")
        headers = [
            "Saglayici", "Model", "Girdi USD/1M", "Cikti USD/1M",
            "Cache okuma USD/1M", "Girdi TRY/1M", "Cikti TRY/1M",
            "Kaynak URL", "Gozlem zamani",
        ]
        ws.append(headers)
        for idx, cell in enumerate(ws[1], start=1):
            cell.fill = HEADER_FILL
            cell.font = Font(bold=True, color="FFFFFF")
            ws.column_dimensions[get_column_letter(idx)].width = 26 if idx != 8 else 52

        ordered = sorted(
            by_model.values(),
            key=lambda e: (e["source"].sales_channel != "direct",
                           e["dims"].get("input", 999), e["dims"].get("output", 999)),
        )
        for entry in ordered:
            dims = entry["dims"]
            inp, out = dims.get("input"), dims.get("output")
            if inp is None or out is None:
                continue
            ws.append([
                entry["provider"].name,
                entry["model"].canonical_id + (" [peak]" if entry["peak"] else ""),
                inp, out, dims.get("cache_read"),
                round(inp * rate, 2), round(out * rate, 2),
                entry["source"].source_url,
                entry["observed_at"].strftime("%d.%m.%Y %H:%M"),
            ])
        ws.freeze_panes = "A2"

        # --- Sayfa 2: gercek is yuku senaryolari (en ucuz 8 + en guclu 8 model) ---
        direct_sorted = sorted(direct, key=lambda e: (e["dims"]["input"], e["dims"]["output"]))
        cheapest = direct_sorted[:6]                                      # ilk 6: dogrudan saglayici ucuz modeller
        frontier = [e for e in reversed(direct_sorted) if e not in cheapest][:6]
        market = [e for e in ordered if e["source"].sales_channel != "direct"][:4]  # pazaryeri referansi
        picked = cheapest + frontier + market
        ws2 = wb.create_sheet("Aylik Maliyet Senaryolari")
        # Oneri tablosu: TUM dogrudan saglayici modelleri arasindan senaryo bazli en iyi secim
        best_per_row: list[tuple[str, dict, float]] = []
        monthly_costs: dict[str, dict[str, float]] = {}
        for name, in_tok, out_tok in PROFILES:
            costs = {}
            for entry in direct:
                dims = entry["dims"]
                monthly_usd = (dims["input"] * in_tok + dims["output"] * out_tok) * 30 / 1_000_000
                costs[entry["model"].canonical_id] = round(monthly_usd * rate, 0)
            monthly_costs[name] = costs
            if costs:
                best_model = min(costs, key=costs.get)
                best_entry = next(e for e in direct if e["model"].canonical_id == best_model)
                best_per_row.append((name, best_entry, costs[best_model]))

        # --- Sayfa 2a: senaryo bazli oneri tablosu ---
        ws2.cell(row=1, column=1, value="SENARYO BAZLI EN UYGUN MODEL (dogrudan saglayici, aylik TRY)")
        ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
        ws2.cell(row=1, column=1).font = Font(bold=True, size=12, color="1F3864")
        ws2.cell(row=1, column=1).fill = SUB_FILL
        heads = ["Senaryo", "Onerilen model", "Saglayici", "Aylik TRY",
                 "En pahali alternatif (TRY)", "Oneri gerekcesi"]
        widths = [42, 28, 15, 14, 22, 62]
        for col, (head, width) in enumerate(zip(heads, widths), start=1):
            c = ws2.cell(row=2, column=col, value=head)
            c.fill = HEADER_FILL
            c.font = Font(bold=True, color="FFFFFF", size=9)
            c.alignment = Alignment(wrap_text=True, vertical="center")
            ws2.column_dimensions[get_column_letter(col)].width = width
        ws2.row_dimensions[2].height = 30

        row = 3
        for name, entry, cost in best_per_row:
            costs_all = monthly_costs[name]
            worst_model = max(costs_all, key=costs_all.get)
            ws2.cell(row=row, column=1, value=name)
            ws2.cell(row=row, column=2, value=entry["model"].canonical_id)
            ws2.cell(row=row, column=3, value=entry["provider"].name)
            c = ws2.cell(row=row, column=4, value=cost)
            c.number_format = "#,##0"
            c.font = Font(bold=True)
            c = ws2.cell(row=row, column=5, value=costs_all[worst_model])
            c.number_format = "#,##0"
            ws2.cell(row=row, column=6,
                     value=f"{worst_model} yerine {entry['model'].canonical_id} secilirse "
                           f"{costs_all[worst_model] - cost:,.0f} TRY/ay tasarruf")
            row += 1

        ws2.cell(row=row + 1, column=1,
                 value=f"USD/TRY {rate} - kaynak: {fx.source_url if fx else '-'} "
                       f"({fx.effective_at.date().isoformat() if fx else 'yok'}). "
                       f"Kalite/gecikme farki olculmedi; bu tablo tasarruf firsatidir.").font = Font(italic=True, size=9)

        # --- Sayfa 2b: detay matris + grafik ---
        ws2b = wb.create_sheet("Senaryo Matrisi ve Grafik")
        ws2b.cell(row=1, column=1, value="DETAY: senaryo x model aylik TRY").font = Font(bold=True, size=12, color="1F3864")
        header_row = 3
        ws2b.cell(row=header_row, column=1, value="Senaryo (aylik TRY)")
        for idx, e in enumerate(picked, start=2):
            c = ws2b.cell(row=header_row, column=idx, value=e["model"].canonical_id[:26])
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for idx in range(1, 2 + len(picked)):
            cell = ws2b.cell(row=header_row, column=idx)
            cell.fill = HEADER_FILL
            cell.font = Font(bold=True, color="FFFFFF", size=9)
            ws2b.column_dimensions[get_column_letter(idx)].width = 15 if idx > 1 else 34
        ws2b.row_dimensions[header_row].height = 46

        for name, in_tok, out_tok in PROFILES:
            r = ws2b.max_row + 1
            ws2b.cell(row=r, column=1, value=name)
            for idx, entry in enumerate(picked, start=2):
                ws2b.cell(row=r, column=idx,
                          value=monthly_costs[name].get(entry["model"].canonical_id))

        # --- Sayfa 3: veri kalitesi / kaynak izlenebiliriligi ---
        ws3 = wb.create_sheet("Kaynaklar ve Metodoloji")
        for line in [
            ["AI Maliyet Merkezi V0.1 - kaynakli fiyat verisi"],
            ["Rapor tarihi", dt.datetime.now().strftime("%d.%m.%Y %H:%M")],
            ["Kural", "Yalnizca QA'dan gecmis (approved) fiyatlar kullanilir."],
            ["Kural", "Fiyat birimi ve para birimi kaynaktaki haliyle saklanir; USD/1M karsilastirmasi ayri kolondur."],
            ["Kural", "OpenRouter satirlari pazaryeri fiyatidir; model sahibinin dogrudan fiyati ile ayni kabul edilmez."],
            ["Kural", "DeepSeek peak/off-peak ayri tutulur; raporda off-peak (standart) baz alinir."],
            [],
            ["Saglayici", "Kaynak URL", "Son gozlem"],
        ]:
            ws3.append(line)
        ws3.column_dimensions["A"].width = 22
        ws3.column_dimensions["B"].width = 80
        ws3.column_dimensions["C"].width = 22
        providers = db.scalars(select(Provider).order_by(Provider.name)).all()
        for p in providers:
            last = db.scalars(
                select(PriceObservation)
                .join(DataSource, DataSource.id == PriceObservation.source_id)
                .where(DataSource.provider_id == p.id, PriceObservation.status == "approved")
                .order_by(desc(PriceObservation.observed_at))
            ).first()
            ws3.append([p.name, p.pricing_url, last.observed_at.strftime("%d.%m.%Y %H:%M") if last else "-"])

        # --- Yazdirma/PDF ayarlari: tasinabilir, az sayfali cikti ---
        from openpyxl.worksheet.properties import PageSetupProperties

        ws0.page_setup.orientation = "landscape"
        ws0.page_setup.fitToWidth = 1
        ws0.page_setup.fitToHeight = 0
        ws0.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws0.print_area = "A1:E14"

        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.print_area = f"A1:I{min(ws.max_row, 121)}"   # ilk 120 model: PDF icin yeterli
        ws.print_title_rows = "1:1"

        for sheet in (ws2, ws2b):
            sheet.page_setup.orientation = "landscape"
            sheet.page_setup.fitToWidth = 1
            sheet.page_setup.fitToHeight = 0
            sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws2.print_area = f"A1:F{ws2.max_row}"
        ws2b.print_area = f"A1:Q{ws2b.max_row}"

        ws3.page_setup.orientation = "landscape"
        ws3.page_setup.fitToWidth = 1
        ws3.page_setup.fitToHeight = 0
        ws3.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)

        # --- Grafik: senaryo x model aylik TRY ---
        from openpyxl.chart import BarChart, Reference

        chart = BarChart()
        chart.type = "col"
        chart.title = "Aylik maliyet (TRY) - senaryo bazinda"
        chart.y_axis.title = "TRY / ay"
        chart.x_axis.title = "Senaryo"
        chart_cols = 1 + len(cheapest) + len(frontier)   # sadece dogrudan saglayici modelleri
        data = Reference(ws2b, min_col=2, max_col=chart_cols,
                         min_row=header_row, max_row=header_row + len(PROFILES))
        cats = Reference(ws2b, min_col=1, min_row=header_row + 1, max_row=header_row + len(PROFILES))
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        chart.height = 11
        chart.width = 22
        wsc = wb.create_sheet("Grafik")
        wsc.sheet_view.showGridLines = False
        wsc.add_chart(chart, "A1")
        wsc.page_setup.orientation = "landscape"
        wsc.page_setup.fitToWidth = 1
        wsc.page_setup.fitToHeight = 1
        from openpyxl.worksheet.properties import PageSetupProperties as _PSP
        wsc.sheet_properties.pageSetUpPr = _PSP(fitToPage=True)
        wsc.print_area = "A1:Q26"

        out = ROOT / "reports" / f"AI_Maliyet_Raporu_{dt.date.today().isoformat()}.xlsx"
        out.parent.mkdir(parents=True, exist_ok=True)
        wb.save(out)
        return out


if __name__ == "__main__":
    path = build()
    print(f"rapor: {path}")
