-- Haftalik maliyet raporu bulteni (D1)
--
-- Neden: ucretsiz arac tek basina gelir uretmez; e-posta listesi
-- tekrar gelen trafik ve donusum kanalidir. Cift onay (double opt-in)
-- zorunlu: onaylanmamis adrese tek bir e-posta bile gonderilmez.
--
-- Uygulama:
--   npx wrangler d1 execute tokenmaliyet-alerts --remote --file=db/newsletter.sql

create table if not exists newsletter_subscribers (
  id                  integer primary key autoincrement,
  email               text not null unique,
  lang                text not null default 'tr',
  confirmed           integer not null default 0,
  confirm_token       text not null,
  unsubscribe_token   text not null,
  consent_at          text not null,
  consent_text_version text not null default 'v1',
  confirmed_at        text,
  unsubscribed_at     text,
  -- Hangi sayfadan geldigi (hesaplayici, fiyatlar, ...): donusum olcumu icin
  source              text,
  -- Kayit IP'sinin tek yonlu ozeti (ham IP saklanmaz - KVKK)
  ip_hash             text,
  created_at          text not null default (datetime('now'))
);

create index if not exists idx_newsletter_confirmed
  on newsletter_subscribers (confirmed, unsubscribed_at);

create index if not exists idx_newsletter_created
  on newsletter_subscribers (created_at desc);

create index if not exists idx_newsletter_ip
  on newsletter_subscribers (ip_hash, created_at desc);
