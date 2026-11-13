-- TokenMaliyet — kalici fiyat gecmisi (Supabase / Postgres)
--
-- Neden: GitHub Actions her calistiginda bos bir Postgres basliyordu; bu yuzden
-- alert_changes.py (len(items) < 2) hicbir zaman fiyat farki yakalayamiyor ve
-- uyari e-postasi gonderemiyordu (rapor 5. tur Hata 5).
-- Bu sema kalici olarak Supabase'de durur; her gun uzerine yazilir.
--
-- Uygulama: Supabase SQL Editor veya psql ile calistir.

create table if not exists providers (
  id            bigserial primary key,
  slug          text not null unique,
  name          text not null,
  website       text,
  pricing_url   text,
  created_at    timestamptz not null default now()
);

create table if not exists models (
  id            bigserial primary key,
  provider_id   bigint not null references providers(id) on delete cascade,
  canonical_id  text not null,
  display_name  text not null,
  created_at    timestamptz not null default now(),
  unique (provider_id, canonical_id)
);

create table if not exists data_sources (
  id               bigserial primary key,
  provider_id      bigint not null references providers(id) on delete cascade,
  label            text not null,
  source_url       text not null,
  source_type      text not null,
  retrieval_method text not null,
  sales_channel    text not null,
  is_official      boolean not null default true,
  created_at       timestamptz not null default now()
);

create table if not exists collection_runs (
  id               bigserial primary key,
  provider_id      bigint not null references providers(id) on delete cascade,
  source_id        bigint references data_sources(id),
  started_at       timestamptz not null default now(),
  finished_at      timestamptz,
  status           text not null default 'ok',
  note             text
);

create table if not exists price_observations (
  id              bigserial primary key,
  model_id        bigint not null references models(id) on delete cascade,
  collection_run_id bigint references collection_runs(id) on delete set null,
  price_dimension text not null,
  amount          numeric(20,10) not null,
  currency        text not null default 'USD',
  billing_unit    text not null,
  tier_label      text,
  peak_period     text,
  observed_at     timestamptz not null default now(),
  effective_from  timestamptz,
  status          text not null default 'pending',
  raw_payload     jsonb,
  created_at      timestamptz not null default now()
);

-- Ayni model+kalem+donem icin TEK onayli fiyat (QA kurali veritabani seviyesinde)
create unique index if not exists uq_price_approved
  on price_observations (model_id, price_dimension,
                         coalesce(peak_period, ''), coalesce(tier_label, ''))
  where status = 'approved';

create index if not exists idx_price_lookup
  on price_observations (model_id, price_dimension, observed_at desc);

-- Gunluk fiyat farki sorgusu icin
create index if not exists idx_price_observed
  on price_observations (observed_at desc) where status = 'approved';

create table if not exists exchange_rates (
  id            bigserial primary key,
  base_currency text not null,
  quote_currency text not null,
  rate          numeric(20,8) not null,
  source_url    text,
  effective_at  timestamptz not null,
  unique (base_currency, quote_currency, effective_at)
);

create table if not exists gpu_providers (
  id          bigserial primary key,
  slug        text not null unique,
  name        text not null,
  pricing_url text,
  created_at  timestamptz not null default now()
);

create table if not exists gpu_prices (
  id             bigserial primary key,
  provider_id    bigint not null references gpu_providers(id) on delete cascade,
  gpu_model      text not null,
  gpu_family     text not null,
  vram_gb        integer,
  price_per_hour numeric(20,10) not null,
  price_kind     text not null default 'on_demand',
  min_lease_hours numeric(10,2),
  observed_at    timestamptz not null default now(),
  status         text not null default 'pending',
  created_at     timestamptz not null default now()
);

create index if not exists idx_gpu_lookup on gpu_prices (gpu_family, price_per_hour);

-- Gunluk degisim raporu icin yardimci gorunum:
-- son 36 saatte ayni model+kalem icin en eski ve en yeni fiyat.
-- Gunluk degisim raporu icin yardimci gorunum.
-- ONEMLI: eski ve yeni AYRI gozlemler olmali; aksi halde pct_change = 0 cikar.
-- Bu yuzden eski = rn_asc = 1, yeni = rn_desc = 1 ve id'leri FARKLI olmali.
create or replace view v_price_changes as
with ranked as (
  select
    po.id,
    po.model_id,
    po.price_dimension,
    coalesce(po.peak_period, '') as peak_key,
    po.amount,
    po.billing_unit,
    po.observed_at
  from price_observations po
  where po.status = 'approved'
)
, paired as (
  select
    n.model_id,
    n.price_dimension,
    n.peak_key,
    n.amount as new_amount,
    n.observed_at as new_at,
    n.id as new_id,
    o.amount as old_amount,
    o.observed_at as old_at,
    o.id as old_id
  from ranked n
  join ranked o
    on o.model_id = n.model_id
   and o.price_dimension = n.price_dimension
   and o.peak_key = n.peak_key
   and o.observed_at < n.observed_at
)
select distinct on (p.model_id, p.price_dimension, p.peak_key)
  p.model_id,
  m.canonical_id,
  m.display_name,
  pr.slug as provider_slug,
  pr.name as provider_name,
  p.price_dimension,
  p.old_amount,
  p.new_amount,
  p.old_at,
  p.new_at,
  case when p.old_amount > 0
       then ((p.new_amount - p.old_amount) / p.old_amount) * 100
       else null end as pct_change
from paired p
join models m on m.id = p.model_id
join providers pr on pr.id = m.provider_id
order by p.model_id, p.price_dimension, p.peak_key, p.new_at desc;
