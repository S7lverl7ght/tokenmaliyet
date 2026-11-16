/**
 * GET /api/bulten-onay?t=<token> — bulten kaydini etkinlestirir (cift onayin 2. adimi).
 *
 * Neden HTML cevap: kullanici e-postadaki baglantiya tiklar ve tarayicida
 * bir "onaylandi" sayfasi gormelidir. JSON gostermek kullaniciyi kaybederdi.
 */
import { siteUrl } from "../_lib/mail.js";

function page(title, body, ok = true) {
  const color = ok ? "#059669" : "#DC2626";
  return new Response(
    `<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>${title} — TokenMaliyet</title>
<link rel="stylesheet" href="/static/app.css">
</head><body><main class="container" style="padding:56px 0;max-width:620px">
<h1 style="font-size:1.6rem">${title}</h1>
<div style="border-left:4px solid ${color};padding:12px 16px;margin:20px 0;background:#f8fafc">
${body}
</div>
<p style="margin-top:28px"><a class="btn" href="/hesaplayici/">Hesaplayiciya don</a>
<a class="btn btn-secondary" href="/fiyatlar/" style="margin-left:8px">Fiyatlar</a></p>
</main></body></html>`,
    {
      status: ok ? 200 : 400,
      headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store",
      "x-robots-tag": "noindex" },
    },
  );
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const token = (url.searchParams.get("t") || "").trim();

  if (!/^[a-f0-9]{16,64}$/i.test(token)) {
    return page("Gecersiz baglanti", "<p>Baglanti eksik veya bozuk. Lutfen e-postadaki baglantiyi tekrar kullanin.</p>", false);
  }
  if (!env.DB) {
    return page("Hata", "<p>Veritabani baglantisi yok.</p>", false);
  }

  let row;
  try {
    row = await env.DB.prepare(
      "SELECT id, lang, confirmed, unsubscribe_token FROM newsletter_subscribers WHERE confirm_token = ?",
    )
      .bind(token)
      .first();
  } catch {
    return page("Hata", "<p>Kayit okunamadi. Lutfen daha sonra tekrar deneyin.</p>", false);
  }

  if (!row) {
    return page(
      "Baglanti gecersiz",
      "<p>Bu onay baglantisi bulunamadi veya daha once kullanilmis.</p>",
      false,
    );
  }

  if (!row.confirmed) {
    try {
      await env.DB.prepare(
        "UPDATE newsletter_subscribers SET confirmed = 1, confirmed_at = datetime('now') WHERE id = ?",
      )
        .bind(row.id)
        .run();
    } catch {
      return page("Hata", "<p>Kayit guncellenemedi. Lutfen daha sonra tekrar deneyin.</p>", false);
    }
  }

  const unsubUrl = siteUrl(env) + "/api/bulten-iptal?t=" + row.unsubscribe_token;
  const body =
    row.lang === "en"
      ? `<p><strong>Your subscription is active.</strong> You will receive the weekly AI cost report.</p>
<p style="font-size:14px;color:#475569">You can <a href="${unsubUrl}">unsubscribe</a> at any time with one click.</p>`
      : `<p><strong>Aboneligi­niz etkin.</strong> Haftalik AI maliyet raporunu alacaksiniz.</p>
<p style="font-size:14px;color:#475569">Istediginiz an tek tikla <a href="${unsubUrl}">abonelikten cikabilirsiniz</a>.</p>`;

  return page(row.lang === "en" ? "Subscription confirmed" : "Abonelik onaylandi", body, true);
}

export async function onRequestPost() {
  return new Response("Method not allowed", { status: 405 });
}
