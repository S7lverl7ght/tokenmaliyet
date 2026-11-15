/**
 * GET /api/bulten-iptal?t=<token> — tek tikla abonelikten cikis.
 *
 * Kayit SILINMEZ, unsubscribed_at isaretlenir: ayni adres yanlislikla
 * tekrar eklenirse tekrar e-posta almasin diye iz kalir.
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
<p style="margin-top:28px"><a class="btn" href="/hesaplayici/">Hesaplayiciya don</a></p>
</main></body></html>`,
    {
      status: ok ? 200 : 400,
      headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
    },
  );
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const token = (url.searchParams.get("t") || "").trim();

  if (!/^[a-f0-9]{16,64}$/i.test(token)) {
    return page("Gecersiz baglanti", "<p>Baglanti eksik veya bozuk.</p>", false);
  }
  if (!env.DB) {
    return page("Hata", "<p>Veritabani baglantisi yok.</p>", false);
  }

  let row;
  try {
    row = await env.DB.prepare(
      "SELECT id, lang FROM newsletter_subscribers WHERE unsubscribe_token = ?",
    )
      .bind(token)
      .first();
  } catch {
    return page("Hata", "<p>Kayit okunamadi.</p>", false);
  }

  if (!row) {
    return page("Baglanti gecersiz", "<p>Bu cikis baglantisi bulunamadi.</p>", false);
  }

  try {
    await env.DB.prepare(
      "UPDATE newsletter_subscribers SET unsubscribed_at = datetime('now'), confirmed = 0 WHERE id = ?",
    )
      .bind(row.id)
      .run();
  } catch {
    return page("Hata", "<p>Kayit guncellenemedi.</p>", false);
  }

  const body =
    row.lang === "en"
      ? "<p><strong>You have been unsubscribed.</strong> No further emails will be sent to this address.</p>"
      : "<p><strong>Abonelikten ciktiniz.</strong> Bu adrese bir daha e-posta gonderilmeyecek.</p>";

  return page(row.lang === "en" ? "Unsubscribed" : "Abonelikten ciktiniz", body, true);
}

export async function onRequestPost() {
  return new Response("Method not allowed", { status: 405 });
}
