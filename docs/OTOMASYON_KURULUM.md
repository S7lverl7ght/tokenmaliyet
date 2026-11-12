# Tam Otomasyon Kurulumu (12.11.2026)

## Durum: TAM OTOMATIK

Site artik **sifir mudahale** ile guncelleniyor:

```
GitHub Actions (06:10 / 18:10 TR)
  -> sema olustur
  -> fiyatlari topla (5 saglayici)
  -> TCMB doviz kuru
  -> golden test
  -> statik site uret
  -> testler (142)
  -> degisiklik varsa commit
  -> Cloudflare Pages'e deploy
  -> CANLI: tokenmaliyet.com
```

## Cloudflare API Token

Token turu: **Account API Token** (`cfat_` oneki).

### Yetkiler (test edildi)

| Kaynak | Izın | Durum |
|---|---|---|
| Cloudflare Pages | Read + Edit | CALISIYOR |
| Pages deployments | Read | CALISIYOR |
| Pages domains | Read | CALISIYOR |
| Workers | Read | VAR |
| R2 | - | 403 (yok) |

### Maliyet riski: YOK

- Token **odeme/billing islemi yapamiyor** (plan degistirme, abonelik yok)
- Kullandigimiz servisler **ucretsiz katmanda**:
  - Cloudflare Pages: statik istekler sinirsiz, 500 build/ay
  - GitHub Actions: public repoda ucretsiz
- Bu proje icin **tek gercek gider alan adi** (~10-12 $/yil, zaten alinmis)

### Nerede sakli

1. **GitHub Secret:** `CLOUDFLARE_API_TOKEN` (sifreli, sadece Actions okur)
2. **Yerel `.env`:** `.gitignore`'da, git'e girmiyor
3. **Canli sitede YOK** — dogrulandi (sizinti taramasi temiz)

## GitHub Secrets

| Ad | Deger |
|---|---|
| `ADMIN_TOKEN` | 64 karakter rastgele |
| `CLOUDFLARE_API_TOKEN` | `cfat_...` (bu token) |
| `CLOUDFLARE_ACCOUNT_ID` | `279485e31b16d58ec7d5603dead31b90` |

## GitHub Variables

| Ad | Deger | Aciklama |
|---|---|---|
| `CF_DEPLOY` | `true` | Deploy adimini acar |

## Ilk otomatik calismanin sonucu

- Model sayisi: 430 -> **446**
- Sitemap: 56 -> **76 URL**
- Indekslenemeyen: **0**
- Bot kendi commit'ini atti: `veri: otomatik fiyat guncellemesi [skip ci]`
- Deployment: `2026-11-12T14:21` production, basarili

## Izleme

- Actions: https://github.com/S7lverl7ght/tokenmaliyet/actions
- Cloudflare Pages: https://dash.cloudflare.com/279485e31b16d58ec7d5603dead31b90/pages/view/tokenmaliyet
- Canli site: https://tokenmaliyet.com

## Elle mudahale gerekirse

```powershell
# Actions -> 'Veri yenile ve yayinla' -> Run workflow
# veya
curl -X POST -H "Authorization: token $env:GH_TOKEN" `
  https://api.github.com/repos/S7lverl7ght/tokenmaliyet/actions/workflows/refresh.yml/dispatches `
  -d '{"ref":"main"}'
```

## Guvenlik notlari

- Token'i **kimseyle paylasmayin**; sizinti halinde Cloudflare panelinden iptal edin
- Token yenilenirse: GitHub Settings -> Secrets -> `CLOUDFLARE_API_TOKEN` guncelleyin
- `.env` dosyasi asla commit edilmemeli (gitignore korumali)
