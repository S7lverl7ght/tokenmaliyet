/**
 * Cloudflare Turnstile dogrulama (sunucu tarafi siteverify).
 *
 * Kural: secret key HICBIR ZAMAN istemciye gitmez; yalnizca env.TURNSTILE_SECRET.
 * Token tek kullanimliktir; 300 saniye icinde dogrulanmalidir.
 *
 * Docs: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
 */

const VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

/**
 * @param {object} env  Pages Function env (TURNSTILE_SECRET)
 * @param {string} token  formdan gelen cf-turnstile-response
 * @param {string} [remoteIp]  zorunlu degil ama onerilir
 * @returns {Promise<{ok: boolean, reason?: string, codes?: string[]}>}
 */
export async function verifyTurnstile(env, token, remoteIp) {
  // Secret tanimli degilse dogrulama ATLANIR ama bu durum loglanabilir olmali.
  // Uretimde TURNSTILE_SECRET tanimli olmak zorunda; degilse fail-open yerine
  // fail-closed tercih edilir (guvenli varsayilan).
  if (!env.TURNSTILE_SECRET) {
    return { ok: false, reason: "not_configured" };
  }
  if (!token || typeof token !== "string" || token.length > 2048) {
    return { ok: false, reason: "missing_token" };
  }

  const body = new URLSearchParams();
  body.set("secret", env.TURNSTILE_SECRET);
  body.set("response", token);
  if (remoteIp) body.set("remoteip", remoteIp);

  try {
    const r = await fetch(VERIFY_URL, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    if (!r.ok) {
      return { ok: false, reason: "verify_http_" + r.status };
    }
    const j = await r.json();
    if (j.success === true) return { ok: true };
    return { ok: false, reason: "rejected", codes: j["error-codes"] || [] };
  } catch {
    return { ok: false, reason: "verify_network" };
  }
}

/** Istemci icin site key (public; gizli degil). */
export function siteKey(env) {
  return env.TURNSTILE_SITE_KEY || "0x4AAAAAAF_TxkQHNciYw5a6";
}
