/**
 * HTML kacis yardimcisi.
 *
 * Neden: kullanici form girdisi (target_label) onay/iptal sayfalarina ve
 * e-posta HTML'ine dogrudan basilinca Stored XSS olusuyordu.
 * CSP 'unsafe-inline' izinli oldugu icin enjekte script calisiyordu.
 */

export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** D1'den gelen degerleri URL'ye guvenle koymak icin. */
export function safeUrl(value, fallback = "/") {
  const s = String(value || "").trim();
  // Yalnizca site ici goreli yollar kabul edilir (javascript:, data: engellenir)
  if (/^\/(?!\/)[A-Za-z0-9\-_./?=&%#]*$/.test(s)) return s;
  return fallback;
}

/** E-posta basligi icin: satir sonu ve kontrol karakterlerini temizler.
 *  Amac: baslik enjeksiyonu (CRLF injection) ve asiri uzun konu engeli. */
export function headerSafe(value, max = 120) {
  return String(value || "")
    .replace(/[\r\n\t\x00-\x1F\x7F]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}
