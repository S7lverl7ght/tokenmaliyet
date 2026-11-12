/**
 * POST /api/uyari — fiyat uyarisi kaydi.
 *
 * Statik sitede sunucu yok; bu Pages Function kaydi Cloudflare D1'e yazar.
 * E-posta gonderimi OPSIYONEL: RESEND_API_KEY tanimliysa Resend ile onay
 * e-postasi gonderilir (ucretsiz katman: 100/gun). Tanimli degilse kayit
 * yine alinir, kullaniciya "kaydedildi" denir.
 */

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

  const token = crypto.randomUUID().replace(/-/g, "");
  const now = new Date().toISOString();

  try {
    await env.DB.prepare(
      `INSERT INTO price_alerts
         (email, target, target_label, direction, threshold_pct,
          confirmed, confirm_token, consent_at, consent_text_version)
       VALUES (?, ?, ?, ?, ?, 0, ?, ?, 'v1')
       ON CONFLICT(email, target) DO UPDATE SET
         threshold_pct = excluded.threshold_pct,
         direction = excluded.direction,
         target_label = excluded.target_label,
         unsubscribed_at = NULL`
    ).bind(email, target, targetLabel, direction, threshold, token, now).run();
  } catch (e) {
    return json({ ok: false, error: "Kayit sirasinda hata olustu." }, 500);
  }

  // Opsiyonel: onay e-postasi (Resend ucretsiz katman)
  let mailSent = false;
  if (env.RESEND_API_KEY && env.ALERT_FROM) {
    const site = env.SITE_URL || "https://tokenmaliyet.com";
    const body = {
      from: env.ALERT_FROM,
      to: [email],
      subject: "TokenMaliyet fiyat uyarisi kaydiniz",
      text:
        "Merhaba,\n\n" +
        "TokenMaliyet'te " + targetLabel + " icin fiyat uyarisi kaydiniz alindi.\n" +
        "Bildirim esigi: %" + threshold + " (" +
        (direction === "down" ? "sadece ucuzlarsa" : direction === "up" ? "sadece pahalanirsa" : "her iki yon") +
        ").\n\n" +
        "Kaydinizi iptal etmek icin: " + site + "/uyari?iptal=" + token + "\n\n" +
        "Bu e-postayi siz istediniz. Ucuncu taraflarla paylasilmiyor.",
    };
    try {
      const r = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          authorization: "Bearer " + env.RESEND_API_KEY,
          "content-type": "application/json",
        },
        body: JSON.stringify(body),
      });
      mailSent = r.ok;
    } catch {
      mailSent = false;
    }
  }

  return json({ ok: true, mail_sent: mailSent });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Bu adres yalnizca POST kabul eder." }, 405);
}
