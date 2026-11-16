/**
 * POST /api/bulten-gonder — haftalik maliyet raporunu abonelere gonderir.
 *
 * Cagiran: GitHub Actions (.github/workflows/bulten.yml), haftada bir.
 * Kimlik: x-bildir-secret basligi (BILDIR_SECRET ile eslesmeli) — /api/bildir ile ayni desen.
 *
 * Govde: {
 *   subject: "...", "haftalik rapor basligi",
 *   headline: "...",          // raporun ana bulgusu (tek cumle)
 *   items: [ {model, change_pct, old_price, new_price, direction} ],
 *   note: "..."               // opsiyonel kapanis notu
 * }
 *
 * Guvenlik/kurallar:
 *   - Yalnizca confirmed=1 VE unsubscribed_at IS NULL kayitlara gonderilir.
 *   - Her e-postada tek tikla cikis baglantisi vardir (zorunlu).
 *   - Toplu gonderim: 100'luk partiler (Cloudflare 50 subrequest siniri).
 */
import { sendMailBatch, siteUrl } from "../_lib/mail.js";
import { escapeHtml } from "../_lib/sanitize.js";

async function timingSafeEqual(a, b) {
  const enc = new TextEncoder();
  const ab = enc.encode(String(a || ""));
  const bb = enc.encode(String(b || ""));
  if (ab.length !== bb.length) return false;
  let diff = 0;
  for (let i = 0; i < ab.length; i++) diff |= ab[i] ^ bb[i];
  return diff === 0;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex",
    },
  });
}

function esc(v, max = 200) {
  return escapeHtml(String(v == null ? "" : v).slice(0, max));
}

/** Rapor govdesini (metin + HTML) uretir. */
function buildBody({ headline, items, note, unsubUrl, site, lang }) {
  const en = lang === "en";
  const rows = items.slice(0, 12);

  const textLines = [
    en ? "Weekly AI cost report" : "Haftalik AI maliyet raporu",
    "",
    headline || "",
    "",
  ];
  for (const it of rows) {
    const sign = Number(it.change_pct) >= 0 ? "+" : "";
    textLines.push(
      `  ${it.model}: ${sign}${Number(it.change_pct).toFixed(1)}% (${it.old_price} -> ${it.new_price} USD)`,
    );
  }
  if (note) textLines.push("", note);
  textLines.push(
    "",
    en ? `All prices: ${site}/fiyatlar/` : `Tum fiyatlar: ${site}/fiyatlar/`,
    en ? `Calculator: ${site}/hesaplayici/` : `Hesaplayici: ${site}/hesaplayici/`,
    "",
    en ? `Unsubscribe (one click): ${unsubUrl}` : `Abonelikten cik (tek tik): ${unsubUrl}`,
  );

  const htmlRows = rows
    .map((it) => {
      const up = Number(it.change_pct) >= 0;
      const color = up ? "#DC2626" : "#059669";
      const arrow = up ? "▲" : "▼";
      return (
        '<tr>' +
        '<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;font-size:14px">' +
        esc(it.model, 80) +
        "</td>" +
        '<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:right;font-size:14px;color:' +
        color +
        ';white-space:nowrap">' +
        arrow +
        " " +
        Math.abs(Number(it.change_pct)).toFixed(1) +
        "%</td>" +
        '<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:right;font-size:13px;color:#64748b;white-space:nowrap">' +
        esc(it.old_price, 20) +
        " → " +
        esc(it.new_price, 20) +
        "</td>" +
        "</tr>"
      );
    })
    .join("");

  const html =
    '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:600px;line-height:1.6;color:#0f172a">' +
    '<h2 style="font-size:19px;margin:0 0 6px">' +
    (en ? "Weekly AI cost report" : "Haftalık AI maliyet raporu") +
    "</h2>" +
    (headline
      ? '<p style="margin:0 0 16px;font-size:15px">' + esc(headline, 300) + "</p>"
      : "") +
    (htmlRows
      ? '<table style="width:100%;border-collapse:collapse;margin:12px 0">' +
        '<thead><tr>' +
        '<th style="text-align:left;padding:6px 10px;font-size:12px;color:#64748b;border-bottom:2px solid #cbd5e1">' +
        (en ? "Model" : "Model") +
        "</th>" +
        '<th style="text-align:right;padding:6px 10px;font-size:12px;color:#64748b;border-bottom:2px solid #cbd5e1">' +
        (en ? "Change" : "Değişim") +
        "</th>" +
        '<th style="text-align:right;padding:6px 10px;font-size:12px;color:#64748b;border-bottom:2px solid #cbd5e1">USD</th>' +
        "</tr></thead><tbody>" +
        htmlRows +
        "</tbody></table>"
      : "") +
    (note ? '<p style="font-size:14px;color:#334155">' + esc(note, 400) + "</p>" : "") +
    '<p style="margin:20px 0 6px;font-size:14px">' +
    '<a href="' +
    site +
    '/fiyatlar/" style="color:#4F46E5">' +
    (en ? "Full price list" : "Tüm fiyat listesi") +
    "</a> &nbsp;·&nbsp; " +
    '<a href="' +
    site +
    '/hesaplayici/" style="color:#4F46E5">' +
    (en ? "Calculator" : "Hesaplayıcı") +
    "</a></p>" +
    '<p style="color:#94a3b8;font-size:12px;margin-top:20px">' +
    (en
      ? "You are receiving this because you confirmed the weekly report. "
      : "Bu e-postayı haftalık rapora onay verdiğiniz için alıyorsunuz. ") +
    '<a href="' +
    unsubUrl +
    '" style="color:#94a3b8">' +
    (en ? "Unsubscribe" : "Abonelikten çık") +
    "</a></p>" +
    "</div>";

  return { text: textLines.join("\n"), html };
}

export async function onRequestPost({ request, env }) {
  const secret = request.headers.get("x-bildir-secret") || "";
  if (!env.BILDIR_SECRET || !(await timingSafeEqual(secret, env.BILDIR_SECRET))) {
    return json({ ok: false, error: "Yetkisiz." }, 401);
  }
  if (!env.DB) return json({ ok: false, error: "DB yok." }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false, error: "JSON gecersiz." }, 400);
  }

  const subject = String(body.subject || "").slice(0, 150);
  if (!subject) return json({ ok: false, error: "subject gerekli." }, 400);
  const items = Array.isArray(body.items) ? body.items.slice(0, 12) : [];

  const site = siteUrl(env);

  // Yalnizca cift onayli ve cikmamis aboneler.
  let rows = [];
  try {
    const res = await env.DB.prepare(
      "SELECT email, lang, unsubscribe_token FROM newsletter_subscribers " +
        "WHERE confirmed = 1 AND unsubscribed_at IS NULL ORDER BY id",
    ).all();
    rows = (res && res.results) || [];
  } catch {
    return json({ ok: false, error: "Abone listesi okunamadi." }, 500);
  }

  if (!rows.length) {
    return json({ ok: true, sent: 0, total: 0, message: "Onayli abone yok." });
  }

  // 100'luk partiler: Cloudflare alt istek sinirini asmamak icin.
  const BATCH = 100;
  let sent = 0;
  const failures = [];

  for (let i = 0; i < rows.length; i += BATCH) {
    const chunk = rows.slice(i, i + BATCH);
    const messages = chunk.map((r) => {
      const unsubUrl = site + "/api/bulten-iptal?t=" + r.unsubscribe_token;
      const built = buildBody({
        headline: body.headline,
        items,
        note: body.note,
        unsubUrl,
        site,
        lang: r.lang,
      });
      return {
        to: r.email,
        subject,
        text: built.text,
        html: built.html,
        // List-Unsubscribe: istemciler tek tikla cikis gosterebilsin (RFC 8058 ruhu).
        headers: { "List-Unsubscribe": "<" + unsubUrl + ">" },
      };
    });

    const res = await sendMailBatch(env, messages);
    if (res.ok) {
      sent += chunk.length;
    } else {
      failures.push({ batch: i / BATCH, reason: res.reason || "error", sent: res.sent || 0 });
      sent += res.sent || 0;
    }
  }

  return json({ ok: failures.length === 0, sent, total: rows.length, failures });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Bu adres yalnizca POST kabul eder." }, 405);
}
