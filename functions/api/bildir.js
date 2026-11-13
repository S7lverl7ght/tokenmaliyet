/**
 * POST /api/bildir — fiyat degisimi bildirimleri.
 *
 * Cagiran: GitHub Actions (refresh.yml), veri toplandiktan sonra.
 * Kimlik: BILDIR_SECRET basligi (env.BILDIR_SECRET ile eslesmeli).
 *
 * Govde: { changes: [{ target, target_label, old_price, new_price }] }
 *   - target: formdaki model anahtari (or. "deepseek|deepseek-v4-pro|") veya "all"
 *   - Sadece confirmed=1 ve unsubscribed_at IS NULL kayitlara gonderilir.
 *   - Esik (threshold_pct) ve yon (direction) kontrol edilir.
 */
import { sendMailBatch, siteUrl } from "../_lib/mail.js";
import { escapeHtml, headerSafe } from "../_lib/sanitize.js";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

export async function onRequestPost({ request, env }) {
  const secret = request.headers.get("x-bildir-secret") || "";
  if (!env.BILDIR_SECRET || secret !== env.BILDIR_SECRET) {
    return json({ ok: false, error: "Yetkisiz." }, 401);
  }
  if (!env.DB) return json({ ok: false, error: "DB yok." }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "JSON gecersiz." }, 400);
  }
  const changes = Array.isArray(body.changes) ? body.changes.slice(0, 200) : [];
  if (!changes.length) return json({ ok: true, sent: 0 });

  const site = siteUrl(env);
  let sent = 0;
  let skipped = 0;
  const errors = [];
  // Toplu gonderim kuyrugu: her aboneye ayri fetch YAPILMAZ (50 subrequest siniri).
  const mails = [];

  for (const ch of changes) {
    const target = String(ch.target || "all").slice(0, 200);
    const label = String(ch.target_label || target).slice(0, 200);
    const oldP = Number(ch.old_price);
    const newP = Number(ch.new_price);
    if (!isFinite(oldP) || !isFinite(newP) || oldP <= 0) { skipped++; continue; }
    const pct = ((newP - oldP) / oldP) * 100;

    let rows;
    try {
      const q = await env.DB.prepare(
        `SELECT id, email, target_label, direction, threshold_pct, unsubscribe_token
           FROM price_alerts
          WHERE confirmed = 1 AND unsubscribed_at IS NULL
            AND (target = ? OR target = 'all')`
      ).bind(target).all();
      rows = q.results || [];
    } catch (e) {
      errors.push(String(e).slice(0, 120));
      continue;
    }

    for (const row of rows) {
      const th = Number(row.threshold_pct) || 10;
      if (Math.abs(pct) < th) { skipped++; continue; }
      if (row.direction === "down" && pct >= 0) { skipped++; continue; }
      if (row.direction === "up" && pct <= 0) { skipped++; continue; }

      const unsub = site + "/api/iptal?t=" + row.unsubscribe_token;
      const arrow = pct < 0 ? "dustu" : "yukseldi";
      mails.push({
        to: row.email,
        subject: "TokenMaliyet: " + headerSafe(label, 80) + " fiyati %" + Math.abs(pct).toFixed(1) + " " + arrow,
        text:
          label + " fiyati degisti.\n\n" +
          "Once: " + oldP + " USD / 1M token\n" +
          "Simdi: " + newP + " USD / 1M token\n" +
          "Degisim: %" + pct.toFixed(1) + "\n\n" +
          "Detay: " + site + "/fiyatlar\n\n" +
          "Bu uyariyi iptal etmek icin: " + unsub,
        html:
          '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.6">' +
          "<p><strong>" + escapeHtml(label) + "</strong> fiyati degisti.</p>" +
          "<p>Once: " + oldP + " USD/1M<br>Simdi: <strong>" + newP + " USD/1M</strong><br>" +
          "Degisim: %" + pct.toFixed(1) + "</p>" +
          '<p><a href="' + site + '/fiyatlar">Fiyat listesine git</a></p>' +
          '<p style="color:#64748b;font-size:13px"><a href="' + unsub + '">Uyariyi iptal et</a></p>' +
          "</div>",
        rowId: row.id,
        newPrice: newP,
      });
    }
  }

  // Tek HTTP istegiyle, 100'luk parcalar halinde gonder (Resend batch).
  const CHUNK = 100;
  for (let i = 0; i < mails.length; i += CHUNK) {
    const slice = mails.slice(i, i + CHUNK);
    const res = await sendMailBatch(env, slice);
    if (res.ok) {
      sent += slice.length;
      const now = new Date().toISOString();
      for (const m of slice) {
        try {
          await env.DB.prepare(
            "UPDATE price_alerts SET last_notified_at = ?, last_price = ? WHERE id = ?"
          ).bind(now, m.newPrice, m.rowId).run();
        } catch { /* sayim tutmazsa sorun degil */ }
      }
    } else {
      errors.push(res.reason || "mail_failed");
    }
  }

  return json({ ok: true, sent, skipped, errors: errors.slice(0, 5) });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Yalnizca POST." }, 405);
}
