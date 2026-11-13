/**
 * GET /api/iptal?t=<token> — abonelikten cikma (tek tik, KVKK).
 */
import { escapeHtml } from "../_lib/sanitize.js";

function page(title, body, ok = true) {
  return new Response(
    '<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<meta name="robots" content="noindex">' +
    "<title>" + title + " - TokenMaliyet</title>" +
    '<link rel="stylesheet" href="/static/app.css"></head><body>' +
    '<main class="container" style="max-width:560px;padding:56px 0">' +
    '<h1 style="font-size:1.6rem">' + title + "</h1>" + body +
    '<p style="margin-top:28px"><a class="btn" href="/fiyatlar/">Fiyatlara git</a></p>' +
    "</main></body></html>",
    { status: ok ? 200 : 400, headers: { "content-type": "text/html; charset=utf-8" } }
  );
}

export async function onRequestGet({ request, env }) {
  const t = new URL(request.url).searchParams.get("t") || "";
  if (!/^[a-f0-9]{16,64}$/.test(t)) {
    return page("Gecersiz baglanti", "<p>Iptal baglantisi gecersiz.</p>", false);
  }
  if (!env.DB) {
    return page("Sunucu hatasi", "<p>Veritabani baglantisi yok.</p>", false);
  }
  try {
    const row = await env.DB.prepare(
      "SELECT id, target_label FROM price_alerts WHERE unsubscribe_token = ? OR confirm_token = ?"
    ).bind(t, t).first();

    if (!row) {
      return page("Baglanti gecersiz", "<p>Bu iptal baglantisi bulunamadi.</p>", false);
    }
    await env.DB.prepare(
      "UPDATE price_alerts SET unsubscribed_at = ?, confirmed = 0 WHERE id = ?"
    ).bind(new Date().toISOString(), row.id).run();

    return page(
      "Uyariniz iptal edildi",
      "<p><strong>" + escapeHtml(row.target_label) + "</strong> icin fiyat uyarisi kaldirildi. " +
      "Istediginiz zaman yeniden kaydolabilirsiniz.</p>"
    );
  } catch {
    return page("Sunucu hatasi", "<p>Iptal sirasinda hata olustu.</p>", false);
  }
}
