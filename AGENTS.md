# AGENTS.md — opm

Bu dosya bu depoda çalışan yapay zekâ ajanları içindir. İnsanlar için: README.md.

## Bu depo nedir

mes-anime sitesinin One Punch Man **video deposu**. Kod yok; sadece veri:
`sN/epM/{index.m3u8, seg_XXX.ts, tr.vtt, en.vtt}`, kökte `mes.anime` ve `poster.jpg`.
Site (https://github.com/mesflit/mes-anime) dosyaları `raw.githubusercontent.com/mesflit/opm/main/`
üzerinden okur. Tüm betikler mes-anime deposundadır ve bu depoyu `../opm` olarak bekler.

Kullanıcı Türkçe konuşur; commit mesajları ve belgeler Türkçedir.

## En önemli kural: videoları indirme

Depo 8 GB+, ~9000 dosya (~8900 `.ts`). Her zaman videolarsız klonla:

    git clone --depth 1 --filter=blob:none --no-checkout https://github.com/mesflit/opm opm
    cd opm && git sparse-checkout set --no-cone '/*' '!*.ts' && git checkout

(veya mes-anime içinden `bash scripts/hafif_klon.sh opm`). Böyle bir klonda blob içeriğine
dokunan komutlar (`git ls-tree -l`, `git log -p`, `git diff` ile `.ts`, `git gc`/`repack`,
`git checkout` ile sparse'ı kapatmak) eksik videoları **indirmeye başlar**. Dosya listesi için
`git ls-tree -r --name-only HEAD` güvenlidir. Dosya eklerken `git add --sparse`.
Bu depodan push ederken `git -c push.negotiate=true push` kullan.

## mes.anime

JSON; tam şema mes-anime/README.md'de. Değişmezler:

- `episodes[].path` = gerçek klasör (`s3/ep0`), içinde `index.m3u8` olmalı.
- Bölüm kimliği `path`'ten türetilir (`s3/ep0` -> `s3-ep0`); izleyici ilerlemesi ve linkler
  buna bağlı. Klasörleri yeniden adlandırma/taşıma.
- `title` alanlarını kullanıcı elle düzenleyebilir; betikler korur. Toplu yeniden başlıklandırma yapma.
- Elle değil, mes-anime'den üret: `python3 scripts/mesanime.py opm` (sıralar, yeni klasörleri
  ekler, silinenleri çıkarır, altyazı listesini yeniler, başlıkları korur).
- Her bölüm tek satır; biçimi koru ki diff okunur kalsın.
- Geçerli JSON olmalı, yoksa anime sitede tamamen kaybolur: `python3 -m json.tool mes.anime`.

## Şifreleme

`index.m3u8` içinde `#EXT-X-KEY:METHOD=AES-128,URI="enc.key",IV=0x0...0`. `enc.key` bu depoda
**yok ve olmamalı**; site anahtarı `SHA-256(VIDEO_SECRET_KEY)[:16]` olarak tarayıcıda üretir.
Yeni bölümler mes-anime'deki `scripts/pack.py` ile aynı `VIDEO_SECRET_KEY` kullanılarak
üretilmeli. `index.m3u8` veya `.ts` dosyalarını elle değiştirme.

## Sık görevler

- **Yeni bölüm klasörleri push edilmiş ama sitede yok:** mes-anime'de
  `python3 scripts/mesanime.py opm`, sonra burada yalnızca `mes.anime`'yi commit + push.
- **Bölüm başlığı değiştir:** `mes.anime` içinde ilgili satırın `title`'ı.
- **Altyazı düzelt:** `sN/epM/tr.vtt` düz WebVTT; mes-anime'de `python3 scripts/altyazi.py temizle|cevir opm`.

## Dikkat

- `main` dalı yayındadır (site doğrudan okur); push etmeden önce kullanıcıdan onay al.
- Push sonrası raw önbelleği ~5 dk sürebilir.
- Depo herkese açık kalmalı.
