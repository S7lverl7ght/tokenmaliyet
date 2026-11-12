"""Ana sayfa ve hesaplayici tasarim testleri.

Kullanici istegi (12.11.2026): site adi TokenMaliyet ve amaci token maliyeti
hesaplamak. Ilk ekranda HESAPLAYICI acilmali; fiyat listesi gezinmede kalmali.
Ayrica form+sonuc 845px viewport'a sigmali (kaydirmadan gorunmeli).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

CALC = ROOT / "backend" / "app" / "web" / "templates" / "calculator.html"
ROUTES = ROOT / "backend" / "app" / "web" / "routes.py"
CSS = ROOT / "backend" / "app" / "web" / "static" / "app.css"


def test_home_redirects_to_calculator():
    src = ROUTES.read_text(encoding="utf-8")
    m = re.search(r'def home\(\):\s*(?:"""[\s\S]*?"""\s*)?return RedirectResponse\("([^"]+)"', src)
    assert m, "home route bulunamadi"
    assert m.group(1) == "/hesaplayici", f"ana sayfa {m.group(1)}'e gidiyor, hesaplayici olmali"


def test_calculator_canonical_is_home():
    src = ROUTES.read_text(encoding="utf-8")
    assert 'ctx["canonical"] = SITE_URL + "/"' in src, "hesaplayici canonical '/' olmali"


def test_sitemap_starts_with_home():
    src = ROUTES.read_text(encoding="utf-8")
    assert 'urls = ["/", "/fiyatlar"' in src, "sitemap '/' ile baslamali"


def test_header_has_only_title():
    html = CALC.read_text(encoding="utf-8")
    head = html[html.index("<header"):html.index("</header>")]
    assert "breadcrumb" not in head, "ustte breadcrumb kalmamali"
    assert 'class="lede"' not in head, "uzun aciklama kaldirilmali"
    assert "Aylık API maliyeti" in head or "Monthly API cost" in head
    # tek h1
    assert html.count("<h1") == 1


def test_cache_field_is_right_of_language():
    html = CALC.read_text(encoding="utf-8")
    i_dil = html.find('id="dil"')
    i_cache = html.find('id="cache"')
    assert 0 < i_dil < i_cache, "onbellek alani metin dilinin saginda olmali"
    # ayni grid icinde
    seg = html[i_dil - 800:i_cache]
    assert "form-grid" in seg, "ikisi ayni satirda degil"
    # cache alani kucuk (kisa etiket)
    assert "Önbellek okuma" in html or "Cache read" in html


def test_result_comes_before_chart():
    """Sonuc kartlari grafikten ONCE gelmeli (kaydirmadan gorunsun)."""
    html = CALC.read_text(encoding="utf-8")
    i_result = html.find('id="sonuc-alani"')
    i_chart = html.find('<figure class="mt-4"')
    assert 0 < i_result < i_chart, "sonuc grafikten once olmali"
    # sonuc formun altinda
    i_form_end = html.find("</form>")
    assert i_form_end < i_result, "sonuc formdan sonra olmali"


def test_compact_mode_applied():
    html = CALC.read_text(encoding="utf-8")
    assert "calc-tight" in html, "sikistirilmis mod sinifi yok"
    css = CSS.read_text(encoding="utf-8")
    assert ".calc-tight" in css, "sikistirilmis mod CSS'i yok"
