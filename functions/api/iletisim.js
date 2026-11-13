/**
 * POST /api/iletisim — site ici iletisim formu.
 *
 * Akis:
 *   1. Turnstile dogrula (bot korumasi, fail-closed)
 *   2. Alanlari dogrula (ad, e-posta, konu, mesaj)
 *   3. D1'e YAZ (mail basarisiz olsa bile mesaj kaybolmaz)
 *   4. Resend ile sahibine ilet (reply-to = kullanicinin adresi)
 *
 * Neden D1 once: e-posta kotasi dolarsa veya Resend dusersе mesaj yine elimizde.
 */
import { sendMail, siteUrl } from "../_lib/mail.js";
import { escapeHtml, headerSafe } from "../_lib/sanitize.js";
import { verifyTurnstile } from "../_lib/turnstile.js";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const TOPICS = {
  duzeltme: "Veri duzeltmesi / hatali fiyat",
  isbirligi: "Is birligi / sponsorluk",
  basin: "Basin",
  teknik: "Teknik sorun",
  diger: "Diger",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

/** IP'yi tuzlayarak saklariz: kaba spam tespiti icin yeterli, KVKK dostu. */
async function hashIp(ip) {
  if (!ip) return "";
  const data = new TextEncoder().encode("tm-contact:" + ip);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function onRequestPost({ request, env }) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Gecersiz form verisi." }, 400);
  }

  const name = String(form.get("name") || "").trim().slice(0, 80);
  const email = String(form.get("email") || "").trim().slice(0, 160);
  const topic = String(form.get("topic") || "diger").trim();
  const message = String(form.get("message") || "").trim().slice(0, 4000);
  // Bal kupu (bot tuzagi): insanlar bunu gormez, doldurmaz.
  const honeypot = String(form.get("website") || "").trim();

  if (honeypot) {
    // Bot: sessizce basarili gorun, hicbir sey yapma.
    return json({ ok: true, mail_sent: false });
  }

  const errors = {};
  if (name.length < 2) errors.name = "Adinizi yazin.";
  if (!EMAIL_RE.test(email)) errors.email = "Gecerli bir e-posta adresi girin.";
  if (!TOPICS[topic]) errors.topic = "Konu secin.";
  if (message.length < 10) errors.message = "Mesaj en az 10 karakter olmali.";
  if (Object.keys(errors).length) {
    return json({ ok: false, errors, error: "Formu kontrol edin." }, 400);
  }

  // 1) Bot korumasi
  const ip = request.headers.get("cf-connecting-ip") || "";
  const ts = await verifyTurnstile(env, form.get("cf-turnstile-response") || "", ip);
  if (!ts.ok) {
    const msg = ts.reason === "not_configured"
      ? "Bot korumasi yapilandirilmamis. Lutfen daha sonra tekrar deneyin."
      : "Guvenlik dogrulamasi basarisiz. Sayfayi yenileyip tekrar deneyin.";
    return json({ ok: false, error: msg, turnstile: ts.reason }, 400);
  }

  const ipHash = await hashIp(ip);
  const now = new Date().toISOString();

  // 2) D1: mesaji HER DURUMDA sakla
  let stored = false;
  if (env.DB) {
    try {
      // Basit hiz siniri: son 24 saatte ayni IP'den 5'ten fazla mesaj yok.
      const recent = await env.DB.prepare(
        "SELECT COUNT(*) AS n FROM contact_messages WHERE ip_hash = ? AND created_at > datetime('now','-1 day')"
      ).bind(ipHash).first();
      if (recent && Number(recent.n) >= 5) {
        return json({ ok: false, error: "Cok fazla mesaj gonderdiniz. Lutfen yarin tekrar deneyin." }, 429);
      }
      await env.DB.prepare(
        "INSERT INTO contact_messages (created_at, name, email, topic, message, ip_hash) VALUES (?,?,?,?,?,?)"
      ).bind(now, name, email, topic, message, ipHash).run();
      stored = true;
    } catch (e) {
      // Tablo yoksa bile e-posta yolunu kapatma.
      stored = false;
    }
  }

  // 3) E-posta: site sahibine ilet; reply-to kullanicinin adresi
  const owner = env.CONTACT_INBOX || "omerktn55@gmail.com";
  const site = siteUrl(env);
  const topicLabel = TOPICS[topic];
  const sent = await sendMail(env, {
    to: owner,
    subject: "TokenMaliyet iletisim: " + headerSafe(topicLabel, 40) + " — " + headerSafe(name, 40),
    text:
      "Yeni iletisim mesaji\n\n" +
      "Ad: " + name + "\n" +
      "E-posta: " + email + "\n" +
      "Konu: " + topicLabel + "\n" +
      "Tarih: " + now + "\n\n" +
      message + "\n\n" +
      "---\n" +
      "Yanitlamak icin bu e-postayi yanitlayin (Reply-To: " + email + ").\n" +
      site,
    html:
      '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.6">' +
      "<h2 style=\"margin:0 0 12px\">Yeni iletisim mesaji</h2>" +
      "<table cellpadding=\"4\" style=\"font-size:14px\">" +
      "<tr><td><strong>Ad</strong></td><td>" + escapeHtml(name) + "</td></tr>" +
      "<tr><td><strong>E-posta</strong></td><td>" + escapeHtml(email) + "</td></tr>" +
      "<tr><td><strong>Konu</strong></td><td>" + escapeHtml(topicLabel) + "</td></tr>" +
      "<tr><td><strong>Tarih</strong></td><td>" + escapeHtml(now) + "</td></tr>" +
      "</table>" +
      '<pre style="white-space:pre-wrap;background:#f5f5f5;padding:12px;border-radius:6px">' +
      escapeHtml(message) + "</pre>" +
      '<p style="color:#64748b;font-size:13px">Yanitlamak icin bu e-postayi yanitlayin.</p>' +
      "</div>",
    replyTo: email,
  });

  // 4) Gonderim sonucunu kaydet (teshis icin)
  if (env.DB && stored) {
    try {
      await env.DB.prepare(
        "UPDATE contact_messages SET mail_sent = ?, mail_error = ? WHERE created_at = ? AND email = ?"
      ).bind(sent.ok ? 1 : 0, sent.ok ? null : String(sent.reason || "").slice(0, 120), now, email).run();
    } catch { /* teshis kaydi basarisizsa kullaniciyi engelleme */ }
  }

  return json({
    ok: true,
    stored,
    mail_sent: !!sent.ok,
    // Kullaniciya ic hata detayi gosterme.
    ...(sent.ok ? {} : { note: "Mesajiniz kaydedildi; e-posta iletimi gecici olarak basarisiz." }),
  });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Yalnizca POST." }, 405);
}
