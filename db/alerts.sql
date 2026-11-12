-- Fiyat uyarisi kayitlari (Cloudflare D1)
CREATE TABLE IF NOT EXISTS price_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT 'all',
  target_label TEXT NOT NULL DEFAULT 'Tum modeller',
  direction TEXT NOT NULL DEFAULT 'any',
  threshold_pct REAL NOT NULL DEFAULT 10,
  last_price REAL,
  confirmed INTEGER NOT NULL DEFAULT 0,
  confirm_token TEXT NOT NULL,
  unsubscribe_token TEXT NOT NULL,
  consent_at TEXT NOT NULL,
  consent_text_version TEXT NOT NULL DEFAULT 'v1',
  confirmed_at TEXT,
  last_notified_at TEXT,
  unsubscribed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(email, target)
);
CREATE INDEX IF NOT EXISTS idx_alerts_email ON price_alerts(email);
CREATE INDEX IF NOT EXISTS idx_alerts_target ON price_alerts(target);
CREATE INDEX IF NOT EXISTS idx_alerts_confirmed ON price_alerts(confirmed, unsubscribed_at);
