/**
 * Resend ile e-posta gonderme yardimcisi.
 *
 * Ucretsiz katman: 100 e-posta/gun, 3.000/ay.
 * Anahtar tanimli degilse sessizce basarisiz olur (kayit yine alinir).
 */

const API = "https://api.resend.com/emails";

export async function sendMail(env, { to, subject, text, html }) {
  if (!env.RESEND_API_KEY || !env.ALERT_FROM) {
    return { ok: false, reason: "not_configured" };
  }
  try {
    const r = await fetch(API, {
      method: "POST",
      headers: {
        authorization: "Bearer " + env.RESEND_API_KEY,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.ALERT_FROM,
        to: [to],
        subject,
        text,
        ...(html ? { html } : {}),
      }),
    });
    if (r.ok) {
      const j = await r.json().catch(() => ({}));
      return { ok: true, id: j.id };
    }
    const err = await r.text();
    return { ok: false, reason: "api_error", detail: err.slice(0, 300) };
  } catch (e) {
    return { ok: false, reason: "network", detail: String(e).slice(0, 200) };
  }
}

export function siteUrl(env) {
  return env.SITE_URL || "https://tokenmaliyet.com";
}

/**
 * Resend toplu gonderim (tek HTTP istegi, 100 e-posta).
 * Neden: Cloudflare Functions ucretsiz planinda fonksiyon basina 50 alt istek
 * siniri var. Tek tek gonderince 50. aboneden sonra fonksiyon olduruluyordu
 * (rapor 5. tur Hata 6). Batch ucu tek istekte 100 e-posta kabul eder.
 */
export async function sendMailBatch(env, messages) {
  if (!env.RESEND_API_KEY || !env.ALERT_FROM) {
    return { ok: false, reason: "not_configured", sent: 0 };
  }
  if (!messages.length) return { ok: true, sent: 0 };

  const payload = messages.map((m) => ({
    from: env.ALERT_FROM,
    to: [m.to],
    subject: m.subject,
    text: m.text,
    ...(m.html ? { html: m.html } : {}),
  }));

  try {
    const r = await fetch(API + "/batch", {
      method: "POST",
      headers: {
        authorization: "Bearer " + env.RESEND_API_KEY,
        "content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (r.ok) {
      const j = await r.json().catch(() => ({}));
      return { ok: true, sent: messages.length, ids: j.data || [] };
    }
    const detail = await r.text();
    return { ok: false, reason: "api_error", detail: detail.slice(0, 300), sent: 0 };
  } catch (e) {
    return { ok: false, reason: "network", detail: String(e).slice(0, 200), sent: 0 };
  }
}
