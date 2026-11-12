/**
 * POST /api/uyari — fiyat uyarisi kaydi (cift onay).
 *
 * Akis:
 *   1. Form gelir -> dogrula -> D1'e confirmed=0 olarak yaz
 *   2. Resend ile onay e-postasi gonder (confirm linki)
 *   3. Kullanici linke tiklar -> /api/onayla -> confirmed=1
 *   4. Fiyat degisince /api/bildir -> sadece confirmed kayitlara e-posta
 */
import { sendMail, siteUrl } from "../_lib/mail.js";

const MAX_EMAIL = 254;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function clean(v, max = 200) {
  return String(v || "").trim().slice(0, max);
}

export async function onRequestPost({ request, env }) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Form verisi okunamadi." }, 400);
  }

  const email = clean(form.get("email"), MAX_EMAIL).toLowerCase();
  const target = clean(form.get("target") || "all") || "all";
  const targetLabel = clean(form.get("target_label"), 200) || "Tum modeller";
  const direction = ["up", "down", "any"].includes(form.get("direction"))
    ? form.get("direction")
    : "any";
  const threshold = Math.min(90, Math.max(1, Number(form.get("threshold_pct")) || 10));
  const consent = form.get("consent");

  if (!EMAIL_RE.test(email)) {
    return json({ ok: false, error: "Gecerli bir e-posta adresi girin." }, 400);
  }
  if (!["on", "1", "true", "yes"].includes(String(consent))) {
    return json({ ok: false, error: "Aydinlatma metnini onaylamaniz gerekir." }, 400);
  }
  if (!env.DB) {
    return json({ ok: false, error: "Veritabani baglantisi yok." }, 503);
  }

  const confirmToken = crypto.randomUUID().replace(/-/g, "");
  const unsubToken = crypto.randomUUID().replace(/-/g, "");
  const now = new Date().toISOString();

  try {
    await env.DB.prepare(
      `INSERT INTO price_alerts
         (email, target, target_label, direction, threshold_pct,
          confirmed, confirm_token, unsubscribe_token, consent_at, consent_text_version)
       VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 'v1')
       ON CONFLICT(email, target) DO UPDATE SET
         threshold_pct = excluded.threshold_pct,
         direction = excluded.direction,
         target_label = excluded.target_label,
         confirm_token = excluded.confirm_token,
         unsubscribed_at = NULL`
    ).bind(email, target, targetLabel, direction, threshold,
           confirmToken, unsubToken, now).run();
  } catch {
    return json({ ok: false, error: "Kayit sirasinda hata olustu." }, 500);
  }

  const site = siteUrl(env);
  const confirmUrl = site + "/api/onayla?t=" + confirmToken;
  const unsubUrl = site + "/api/iptal?t=" + unsubToken;

  const dirText = direction === "down" ? "sadece ucuzlarsa"
    : direction === "up" ? "sadece pahalanirsa" : "her iki yon";

  const mail = await sendMail(env, {
    to: email,
    subject: "TokenMaliyet: fiyat uyarisi kaydinizi onaylayin",
    text:
      "Merhaba,\n\n" +
      "TokenMaliyet'te \"" + targetLabel + "\" icin fiyat uyarisi kaydiniz olusturuldu.\n" +
      "Bildirim esigi: %" + threshold + " (" + dirText + ")\n\n" +
      "Kaydinizi etkinlestirmek icin asagidaki baglantiya tiklayin:\n" +
      confirmUrl + "\n\n" +
      "Bu adimi atlarsaniz uyari gonderilmez (cift onay).\n\n" +
      "Iptal etmek icin her zaman: " + unsubUrl + "\n\n" +
      "Bu e-postayi siz istediniz. Adresiniz ucuncu taraflarla paylasilmiyor.\n" +
      "TokenMaliyet - AI API fiyat ve maliyet verisi",
    html:
      '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;line-height:1.6">' +
      '<h2 style="font-size:18px;margin:0 0 12px">Fiyat uyarisi kaydinizi onaylayin</h2>' +
      "<p><strong>" + targetLabel + "</strong> icin fiyat uyarisi olusturuldu.</p>" +
      "<p>Bildirim esigi: <strong>%" + threshold + "</strong> (" + dirText + ")</p>" +
      '<p style="margin:24px 0"><a href="' + confirmUrl + '" ' +
      'style="background:#4F46E5;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">' +
      "Kaydi etkinlestir</a></p>" +
      '<p style="color:#64748b;font-size:13px">Onaylamazsaniz uyari gonderilmez.</p>' +
      '<p style="color:#64748b;font-size:13px">Iptal: <a href="' + unsubUrl + '">aboneligi kaldir</a></p>' +
      "</div>",
  });

  return json({
    ok: true,
    mail_sent: mail.ok,
    needs_confirm: true,
    mail_reason: mail.ok ? undefined : mail.reason,
  });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Bu adres yalnizca POST kabul eder." }, 405);
}
