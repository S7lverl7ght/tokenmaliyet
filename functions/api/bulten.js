/**
 * POST /api/bulten — haftalik maliyet raporu bultenine kayit (cift onay).
 *
 * Akis:
 *   1. Turnstile dogrula (bot korumasi, fail-closed)
 *   2. E-posta + onay kutusu dogrula
 *   3. D1'e confirmed=0 olarak yaz (onaysiz adrese e-posta GONDERILMEZ)
 *   4. Resend ile onay e-postasi gonder (tek tik)
 *   5. Kullanici tiklar -> /api/bulten-onay -> confirmed=1
 *
 * Neden cift onay: yanlis yazilmis veya baskasinin adresi kaydedilmesin;
 * ayni zamanda istenmeyen posta sikayeti riski sifira iner.
 */
import { sendMail, siteUrl } from "../_lib/mail.js";
import { escapeHtml } from "../_lib/sanitize.js";
import { verifyTurnstile } from "../_lib/turnstile.js";

const MAX_EMAIL = 254;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const SITE_NAME = "TokenMaliyet";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

/** JS kapaliysa form dogrudan POST eder; kullaniciya HTML sayfa donmeliyiz. */
function htmlPage(title, body, status = 200) {
  const doc =
    '<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<meta name="robots" content="noindex,nofollow">' +
    "<title>" + title + " - TokenMaliyet</title>" +
    '<link rel="stylesheet" href="/static/app.css"></head><body>' +
    '<main class="container" style="padding:56px 0;max-width:620px">' +
    '<h1 style="font-size:1.6rem">' + title + "</h1>" +
    '<div style="border-left:4px solid #4F46E5;padding:12px 16px;margin:20px 0;background:#f8fafc">' +
    body +
    "</div>" +
    '<p style="margin-top:28px"><a class="btn" href="/hesaplayici/">Hesaplayiciya don</a></p>' +
    "</main></body></html>";
  return new Response(doc, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}

function clean(v, max = 200) {
  return String(v || "").trim().slice(0, max);
}

/** IP'yi tuzlayarak saklariz: kaba spam tespiti icin yeterli, KVKK dostu. */
async function hashIp(ip) {
  if (!ip) return "";
  const data = new TextEncoder().encode("tm-newsletter:" + ip);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .slice(0, 8)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function onRequestPost({ request, env }) {
  let form;
  try {
    form = await request.formData();
  } catch {
    return json({ ok: false, error: "Gecersiz form verisi." }, 400);
  }

  const email = clean(form.get("email"), MAX_EMAIL).toLowerCase();
  const lang = clean(form.get("lang"), 2) === "en" ? "en" : "tr";
  const source = clean(form.get("source"), 40) || "calculator";
  const consent = form.get("consent");
  // Bal kupu (bot tuzagi)
  const honeypot = clean(form.get("website"));

  if (honeypot) {
    return json({ ok: true, needs_confirm: true, mail_sent: false });
  }
  if (!EMAIL_RE.test(email)) {
    return json(
      { ok: false, error: lang === "en" ? "Enter a valid email address." : "Gecerli bir e-posta adresi girin." },
      400,
    );
  }
  if (!["on", "1", "true", "yes"].includes(String(consent))) {
    return json(
      {
        ok: false,
        error:
          lang === "en"
            ? "Please accept the privacy notice to subscribe."
            : "Abone olmak icin aydinlatma metnini onaylamaniz gerekir.",
      },
      400,
    );
  }

  const ip = request.headers.get("cf-connecting-ip") || "";
  const tsToken = form.get("cf-turnstile-response") || "";
  const ts = await verifyTurnstile(env, tsToken, ip);
  if (!ts.ok) {
    const msg =
      ts.reason === "not_configured"
        ? lang === "en"
          ? "Bot protection is not configured. Please try again later."
          : "Bot korumasi yapilandirilmamis. Lutfen daha sonra tekrar deneyin."
        : lang === "en"
          ? "Security check failed. Refresh the page and try again."
          : "Guvenlik dogrulamasi basarisiz. Sayfayi yenileyip tekrar deneyin.";
    return json({ ok: false, error: msg, turnstile: ts.reason }, 400);
  }

  if (!env.DB) {
    return json({ ok: false, error: "Veritabani baglantisi yok." }, 503);
  }

  const ipHash = await hashIp(ip);

  // Basit kota: ayni IP'den gunluk 5'ten fazla kayit engellenir.
  try {
    const recent = await env.DB.prepare(
      "SELECT COUNT(*) AS n FROM newsletter_subscribers WHERE ip_hash = ? AND created_at > datetime('now','-1 day')",
    )
      .bind(ipHash)
      .first();
    if (recent && recent.n >= 5) {
      return json({ ok: false, error: "Cok fazla deneme. Lutfen yarin tekrar deneyin." }, 429);
    }
  } catch {
    /* sayim yapilamazsa kaydi engellemeyiz */
  }

  const confirmToken = crypto.randomUUID().replace(/-/g, "");
  const unsubToken = crypto.randomUUID().replace(/-/g, "");
  const now = new Date().toISOString();

  try {
    // ON CONFLICT: ayni adres tekrar kaydolursa onay token'i yenilenir,
    // abonelikten cikmis biri tekrar abone olabilir.
    await env.DB.prepare(
      `INSERT INTO newsletter_subscribers
         (email, lang, confirmed, confirm_token, unsubscribe_token,
          consent_at, consent_text_version, source, ip_hash)
       VALUES (?, ?, 0, ?, ?, ?, 'v1', ?, ?)
       ON CONFLICT(email) DO UPDATE SET
         lang = excluded.lang,
         confirm_token = excluded.confirm_token,
         unsubscribe_token = excluded.unsubscribe_token,
         source = excluded.source,
         consent_at = excluded.consent_at,
         unsubscribed_at = NULL`,
    )
      .bind(email, lang, confirmToken, unsubToken, now, source, ipHash)
      .run();
  } catch {
    return json({ ok: false, error: "Kayit sirasinda hata olustu." }, 500);
  }

  const site = siteUrl(env);
  const confirmUrl = site + "/api/bulten-onay?t=" + confirmToken;
  const unsubUrl = site + "/api/bulten-iptal?t=" + unsubToken;

  const subject =
    lang === "en"
      ? SITE_NAME + ": confirm your weekly cost report"
      : SITE_NAME + ": haftalik maliyet raporu kaydinizi onaylayin";

  const text =
    (lang === "en"
      ? "Hello,\n\nSomeone (hopefully you) asked to receive the weekly AI cost report from " +
        SITE_NAME +
        ".\n\nClick to confirm:\n" +
        confirmUrl +
        "\n\nIf you do not confirm, nothing is sent to you (double opt-in).\n\n" +
        "Unsubscribe at any time: " +
        unsubUrl +
        "\n\nYou are receiving this because you submitted the form. Your address is never shared.\n"
      : "Merhaba,\n\n" +
        SITE_NAME +
        " haftalik AI maliyet raporuna kaydolmak istediniz.\n\n" +
        "Onaylamak icin tiklayin:\n" +
        confirmUrl +
        "\n\nOnaylamazsaniz size hicbir e-posta gonderilmez (cift onay).\n\n" +
        "Istediginiz an cikabilirsiniz: " +
        unsubUrl +
        "\n\nBu e-postayi siz formu doldurdugunuz icin aldiniz. Adresiniz ucuncu taraflarla paylasilmaz.\n");

  const html =
    '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;line-height:1.6">' +
    '<h2 style="font-size:18px;margin:0 0 12px">' +
    (lang === "en" ? "Confirm your subscription" : "Kaydinizi onaylayin") +
    "</h2>" +
    "<p>" +
    (lang === "en"
      ? "Confirm that you want the weekly AI cost report."
      : "Haftalik AI maliyet raporuna abone olmak istediginizi onaylayin.") +
    "</p>" +
    '<p style="margin:24px 0"><a href="' +
    confirmUrl +
    '" style="background:#4F46E5;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:600">' +
    (lang === "en" ? "Confirm subscription" : "Aboneligi onayla") +
    "</a></p>" +
    '<p style="color:#64748b;font-size:13px">' +
    (lang === "en"
      ? "If you do not confirm, nothing is sent to you."
      : "Onaylamazsaniz size hicbir e-posta gonderilmez.") +
    "</p>" +
    '<p style="color:#64748b;font-size:13px">' +
    (lang === "en" ? "Unsubscribe: " : "Cikmak icin: ") +
    '<a href="' +
    unsubUrl +
    '">' +
    (lang === "en" ? "unsubscribe" : "abonelikten cik") +
    "</a></p>" +
    "</div>";

  const mail = await sendMail(env, { to: email, subject, text, html });

  const okMsg =
    lang === "en"
      ? "Almost done: check your inbox and click the confirmation link."
      : "Son adim: gelen kutunuzu kontrol edip onay baglantisina tiklayin.";

  // JS kapaliysa tarayici form gonderir ve HTML bekler; fetch ise JSON ister.
  if ((request.headers.get("accept") || "").includes("text/html")) {
    return htmlPage(
      lang === "en" ? "Confirm your subscription" : "Kaydinizi onaylayin",
      "<p>" + okMsg + "</p>",
    );
  }

  return json({
    ok: true,
    needs_confirm: true,
    mail_sent: mail.ok,
    mail_reason: mail.ok ? undefined : mail.reason,
    message: okMsg,
  });
}

export async function onRequestGet() {
  return json({ ok: false, error: "Bu adres yalnizca POST kabul eder." }, 405);
}
