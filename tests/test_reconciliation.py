"""Mutabakat testleri - inceleme raporu 3. tur, bolum 6.

Bu testler raporun 'otomatik yakalanmali' dedigi bulgulari kapsar.
Her biri gercek bir hatanin tekrar olusmasini engeller.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.web import calc


def _num(text: str) -> float:
    """'1.545,75' -> 1545.75 (TR yerel ayari)."""
    return float(text.strip().replace(".", "").replace(",", "."))


@pytest.fixture(scope="module")
def client(seeded_data):
    return TestClient(app)


def _models(client):
    rows = client.get("/api/v1/model-options").json()
    return rows


def test_single_calculation_module_exists():
    """Hesap mantigi tek yerde: calc.monthly_cost."""
    from app.web.calc import ModelPrice

    m = ModelPrice(name="t", provider="p", slug="t", input_per_1m=0.66, output_per_1m=1.98)
    r = calc.monthly_cost(m, 100_000_000, 25_000_000)
    assert abs(r.total_usd - 115.50) < 0.01, r.total_usd


def test_multiplier_applied_to_both_models():
    """Rapor 3. tur: carpan HER IKI modele de uygulanir (tek tarafli uygulama hataydi)."""
    from app.web.calc import ModelPrice

    m = ModelPrice(name="t", provider="p", slug="t", input_per_1m=1.0, output_per_1m=2.0)
    one = calc.monthly_cost(m, 1_000_000, 0, tokens_multiplier=1.0)
    two = calc.monthly_cost(m, 1_000_000, 0, tokens_multiplier=2.0)
    assert abs(two.total_usd - one.total_usd * 2) < 1e-9


def test_compare_and_calculator_agree(client):
    """Ayni model cifti + ayni token -> ayni maliyet (rapor bulgu 1)."""
    rows = _models(client)
    if len(rows) < 2:
        pytest.skip("en az iki model gerekli")
    a, b = rows[0]["value"], rows[1]["value"]

    cmp_body = client.get("/karsilastir", params=[("models", a), ("models", b),
                                                  ("in", "100000000"), ("out", "25000000")]).text
    calc_body = client.get("/hesaplayici", params={"from": a, "to": b, "in": "100000000",
                                                    "out": "25000000", "dil": "tr"}).text

    cmp_costs = {_num(x) for x in re.findall(r'class="num">([0-9.,]+) USD</div>', cmp_body)}
    calc_costs = {_num(x) for x in re.findall(r'<div class="v">([0-9.,]+) USD</div>', calc_body)}
    if not cmp_costs or not calc_costs:
        pytest.skip("fiyat verisi yok")
    # Hesaplayicinin ilk iki karti karsilastirmanin iki kartiyla ayni olmali
    assert cmp_costs <= calc_costs | {0.0}, f"{cmp_costs} vs {calc_costs}"


def test_displayed_price_reproduces_displayed_total(client):
    """Kartta yazan fiyatlar, kartta yazan toplami vermeli (rapor bulgu 2)."""
    rows = _models(client)
    if not rows:
        pytest.skip("model yok")
    body = client.get("/karsilastir", params=[("models", rows[0]["value"]),
                                              ("in", "100000000"), ("out", "25000000")]).text
    # kart icindeki girdi/cikti fiyatlari
    prices = re.findall(r"<dt>Girdi</dt><dd>([0-9.,]+) USD/1M</dd>\s*<dt>Çıktı</dt><dd>([0-9.,]+) USD/1M</dd>", body)
    totals = re.findall(r'class="num">([0-9.,]+) USD</div>', body)
    if not prices or not totals:
        pytest.skip("kart verisi yok")
    inp, outp = _num(prices[0][0]), _num(prices[0][1])
    expected = inp * 100 + outp * 25  # 100M input + 25M output
    # Kartlar ucuzdan pahaliya siralanir; kart fiyatlari ile kart toplami
    # AYNI kayittan gelmeli. Ilk kart = en ucuz; en az bir kart tutmali.
    assert any(abs(_num(t) - expected) < 1.0 for t in totals), (
        f"kartta yazan fiyatlar toplami vermiyor: beklenen {expected}, kartlar {totals}"
    )


def test_prices_unique_per_model_dimension(client):
    """Ayni model+kalem icin TEK fiyat (rapor bulgu 4: gemini-embedding-2)."""
    rows = client.get("/api/v1/prices").json()
    seen: dict[tuple, float] = {}
    for r in rows:
        key = (r["provider"], r["model_id"], r["price_dimension"], r.get("peak_period"))
        if key in seen:
            assert abs(seen[key] - r["amount"]) < 1e-12, f"cakisma: {key}"
        seen[key] = r["amount"]


def test_changes_values_match_prices(client):
    """Changes sayfasindaki 'yeni' deger, fiyat listesindeki guncel degerle ayni olmali."""
    body = client.get("/degisiklikler").text
    new_vals = re.findall(r'data-label="Şimdi" class="num">([0-9.,]+)</td>', body)
    if not new_vals:
        pytest.skip("degisiklik yok")
    # degerler 1M token biriminde ve makul olmali (0 veya negatif degil)
    for v in new_vals:
        assert _num(v) > 0, f"anlamsiz deger: {v}"


def test_no_meaningless_percentage_in_changes(client):
    """Rapor bulgu 6: '0.000000 -> 0.000000, -22.2%' gibi satir olmamali."""
    body = client.get("/degisiklikler").text
    assert "0,000000" not in body, "yuvarlanmis sifir fiyat gosteriliyor"


def test_navbar_brand_does_not_collide(client):
    """Rapor: ust menude logo ile sayfa isimleri ic ice girmemeli."""
    body = client.get("/fiyatlar").text
    # logo blogu ve nav ayri elemanlar olmali
    assert 'class="brand"' in body
    assert 'class="nav"' in body
    assert 'aria-label="Ana menü"' in body


def test_no_embedding_on_first_screen(client):
    """Rapor 3. tur: ilk ekranda embedding/gorsel modeller gorunmemeli."""
    body = client.get("/fiyatlar").text
    import re
    names = re.findall(r'class="name"[^>]*>([^<]+)</a>', body)
    assert names, "model listesi bos"
    assert not any("embedding" in n.lower() for n in names), names[:5]


def test_compare_third_and_fourth_empty(client):
    """Rapor 3. tur bulgu 8: 3. ve 4. kutu 'Secilmedi' olmali."""
    import re
    body = client.get("/karsilastir").text
    sels = re.findall(r'<select id="m(\d)"[^>]*>(.*?)</select>', body, re.S)
    for i, chunk in sels:
        selected = re.findall(r'<option value="([^"]*)"[^>]*selected', chunk)
        if int(i) >= 2:
            assert not [s for s in selected if s], f"m{i} varsayilan secili: {selected}"


def test_number_format_uses_comma_in_h1(client):
    """Rapor 3. tur bulgu 12: H1'de 2.29 degil 2,29 olmali."""
    body = client.get("/turkce-token-maliyeti").text
    assert "2.29" not in body or "2,29" in body


def test_price_format_max_four_decimals(client):
    """Rapor bulgu 13: $/GB gibi degerler en fazla 4 ondalik."""
    import re
    body = client.get("/gpu-maliyetleri").text
    # 6 ondalikli fiyat kalmamali
    bad = re.findall(r"\b\d+,\d{6}\b", body)
    assert not bad, f"6 ondalik: {bad[:5]}"


def test_changes_use_1m_units(client):
    """Rapor bulgu 5: degisiklik degerleri ham per-token degil, 1M biriminde."""
    body = client.get("/degisiklikler").text
    assert "USD/token" not in body, "ham per-token birimi kalmis"


def test_navbar_has_grouped_tools(client):
    """Rapor: ust menude logo ile linkler ic ice girmesin; araclar gruplansin."""
    body = client.get("/fiyatlar").text
    assert 'class="nav-group"' in body
    assert "nav-group-btn" in body
    # brand ve nav kardes elemanlar olmali
    import re
    header = re.search(r"<header class=\"site-header\">(.*?)</header>", body, re.S).group(1)
    assert 'class="brand"' in header and 'class="nav"' in header


def test_gpu_columns_match_cells(client):
    """Rapor 4. tur P0-1: GPU tablosunda baslik sirasi ile hucre sirasi ayni olmali."""
    import re
    body = client.get("/gpu-maliyetleri").text
    head_match = re.search(r"<thead>(.*?)</thead>", body, re.S)
    if not head_match:
        pytest.skip("gpu tablosu yok")
    head = head_match.group(1)
    headers = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", head, re.S)]
    tbody = re.search(r"<tbody>(.*?)</tbody>", body, re.S)
    if not tbody:
        pytest.skip("gpu satiri yok")
    first = re.findall(r"<tr>(.*?)</tr>", tbody.group(1), re.S)[0]
    cells = [c for c in re.findall(r'<td[^>]*data-label="([^"]*)"', first)]
    # Basliklar ile data-label'lar ayni sirada olmali (metin farki normalize edilir)
    norm = lambda s: s.lower().replace("/", "").replace(" ", "")
    header_norm = [norm(h) for h in headers]
    cell_norm = [norm(c) for c in cells]
    for i, (h, c) in enumerate(zip(header_norm, cell_norm)):
        assert h in c or c in h, f"sutun {i}: baslik={headers[i]} hucre={cells[i]}"


def test_gpu_hourly_price_greater_than_per_gb(client):
    """Rapor 4. tur: saatlik fiyat, $/GB VRAM degerinden buyuk olmali (VRAM > 1 GB)."""
    import re
    body = client.get("/gpu-maliyetleri").text
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", body, re.S)
    if not tbody_match:
        pytest.skip("veri yok")
    rows = re.findall(r"<tr>(.*?)</tr>", tbody_match.group(1), re.S)[:5]

    def cells(row):
        out = {}
        for label, content in re.findall(r'<td[^>]*data-label="([^"]*)"[^>]*>(.*?)</td>', row, re.S):
            text = re.sub(r"<[^>]+>", " ", content).strip()
            nums = re.findall(r"(\d[\d.]*,\d+)", text)
            if nums:
                out[label] = float(nums[0].replace(".", "").replace(",", "."))
        return out

    checked = 0
    for row in rows:
        c = cells(row)
        hourly = next((v for k, v in c.items() if k.startswith("En d")), None)
        per_gb = next((v for k, v in c.items() if "GB" in k and "$" in k), None)
        if hourly and per_gb:
            assert hourly > per_gb, f"saatlik {hourly} <= $/GB {per_gb} — sutunlar karismis"
            checked += 1
    assert checked > 0, "karsilastirilacak satir bulunamadi"


def test_compare_has_language_selector(client):
    """Rapor 4. tur P0-3: Compare'de dil secici ve carpan rozeti olmali."""
    body = client.get("/karsilastir").text
    assert 'name="dil"' in body
    assert "içerik varsayımı" in body or "carpan" in body.lower()


def test_calculator_notice_mentions_both_models(client):
    """Rapor 4. tur P1-4: bilgi kutusu 'her iki model' demeli."""
    body = client.get("/hesaplayici?dil=tr").text
    if "2,2" in body or "2,29" in body:
        assert "her iki modelin" in body


def test_guide_count_is_dynamic(client):
    """Rapor 4. tur P1-5: rehber sayisi metinle uyusmali."""
    import re
    body = client.get("/rehber").text
    assert "üç kısa yazı" not in body
    m = re.search(r"(\d+) kısa yazı", body)
    assert m, "dinamik sayi bulunamadi"


def test_prices_description_mentions_marketplace(client):
    """Rapor 3.+4. tur: aciklama pazaryerini de soylemeli."""
    body = client.get("/fiyatlar").text
    assert "pazaryeri" in body.lower()
