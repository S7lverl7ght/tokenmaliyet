-- Iletisim mesajlari (D1)
--
-- Neden: e-posta gonderimi basarisiz olsa bile mesaj KAYBOLMASIN.
-- Kullanici mesaji her durumda buraya yazilir; e-posta ikincil kanal.
--
-- Uygulama:
--   npx wrangler d1 execute tokenmaliyet-alerts --remote --file=db/contact.sql

create table if not exists contact_messages (
  id           integer primary key autoincrement,
  created_at   text not null default (datetime('now')),
  name         text not null,
  email        text not null,
  topic        text not null,
  message      text not null,
  ip_hash      text,
  mail_sent    integer not null default 0,
  mail_error   text
);

create index if not exists idx_contact_created
  on contact_messages (created_at desc);

-- Ayni IP'den gunluk 5'ten fazla mesaj engellenir (basit spam korumasi).
create index if not exists idx_contact_ip
  on contact_messages (ip_hash, created_at desc);
