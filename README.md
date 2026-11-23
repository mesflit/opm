# opm — One Punch Man video deposu

[mes-anime](https://github.com/mesflit/mes-anime) sitesinin One Punch Man bölümlerini tutan depo.
Burada site kodu yok; sadece şifreli video parçaları, altyazılar ve bölüm listesi (`mes.anime`) var.
Site bu dosyaları doğrudan `raw.githubusercontent.com/mesflit/opm/main/...` adresinden okur.

## Yapı

    opm/
    ├── mes.anime          # Anime bilgisi + bölüm listesi (site bunu okur)
    ├── poster.jpg         # Kapak görseli
    ├── s1/                # 1. sezon
    │   ├── ep1/
    │   │   ├── index.m3u8 # HLS oynatma listesi (AES-128, anahtar URI'si "enc.key")
    │   │   ├── seg_000.ts # ~6 sn'lik şifreli video parçaları
    │   │   ├── ...
    │   │   ├── tr.vtt     # Türkçe altyazı
    │   │   └── en.vtt     # İngilizce altyazı
    │   └── ...
    ├── s2/
    └── s3/                # 3. sezon ep0'dan başlar

Şu an: 1. sezon 12, 2. sezon 12, 3. sezon 13 bölüm (ep0–ep12). Depo 8 GB'tan büyük, ~9000 dosya.

## mes.anime

    {
      "title": "One Punch Man",
      "category": "Aksiyon",
      "poster": "poster.jpg",
      "episodes": [
        {"path": "s1/ep1", "title": "1. Sezon 1. Bölüm", "subtitles": ["tr", "en"]},
        ...
      ]
    }

- `path`: bölüm klasörü (içinde `index.m3u8` olmalı)
- `title`: sitede görünen bölüm adı, elle değiştirilebilir
- `subtitles`: klasördeki `<dil>.vtt` dosyaları; site önce izleyicinin son seçtiği dili, yoksa Türkçeyi açar
- Bölümler dosyadaki sırayla gösterilir; sezon `path`'in başındaki `sN`'den okunur

Elle düzenlersen JSON'un geçerli olduğundan emin ol (`python3 -m json.tool mes.anime`);
bozuk dosya One Punch Man'in sitede hiç görünmemesine yol açar.

## Bölüm ekleme

Tüm işler mes-anime deposundaki betiklerle yapılır. İki depo yan yana durmalı (`~/mes-anime`, `~/opm`).

**Bu depoyu videolar olmadan klonla** (8 GB yerine ~3 MB):

    cd ~/mes-anime && bash scripts/hafif_klon.sh opm

**Yeni bölüm (MKV/MP4'ten):**

    cd ~/mes-anime
    python3 scripts/pack.py /sdcard/Download/bolum.mkv opm s3/ep13 --extract-sub --tr
    cd ../opm && git add --sparse -A && git commit -m "feat: S3 B13" && git push
    git sparse-checkout reapply          # yüklenen .ts dosyalarını diskten siler

`pack.py` videoyu şifreler, altyazıları hazırlar ve `mes.anime`'yi günceller.

**Bölüm klasörlerini başka yolla eklediysen** (hazır `index.m3u8` + `.ts` kopyaladıysan), push etmeden önce:

    cd ~/mes-anime && python3 scripts/mesanime.py opm

Push'tan birkaç dakika sonra (GitHub önbelleği ~5 dk) bölüm sitede görünür. mes-anime'ye push gerekmez.

## İnce noktalar

- **Klasör adlarını değiştirme.** `s1/ep1` sitede `s1-ep1` kimliğine dönüşür; izleyicilerin
  kaldığı yer ve paylaşılan linkler buna bağlı. Yeniden adlandırırsan ilerlemeleri kaybolur.
- **Depo adını değiştirme** (`opm` = sitedeki anime kimliği, linkler `#/izle/opm/...`).
- **Depo herkese açık kalmalı.** Site dosyaları kimlik doğrulamasız okur.
- **Videolar şifreli.** `.ts` parçaları `VIDEO_SECRET_KEY`'den türetilen AES-128 anahtarıyla
  şifrelidir; anahtar bu depoda yok (`enc.key` dosyası bilerek yok, site onu tarayıcıda üretir).
  Bu yüzden parçalar tek başına oynatılamaz. Yeni bölümler aynı `VIDEO_SECRET_KEY` ile
  şifrelenmeli, yoksa oynatılmaz.
- **Altyazılar şifresiz** düz WebVTT dosyalarıdır, doğrudan düzenlenebilir.
- **`git add --sparse -A` şart:** hafif klonda `.ts` dosyaları sparse dışında olduğu için
  normal `git add` onları eklemez.
- Hafif klonda `git ls-tree -l`, `git log -p` gibi dosya boyutuna/içeriğine bakan komutlar
  videoları indirmeye başlar; kullanma.
- GitHub tek dosyada 100 MB sınırı koyar; 6 sn'lik parçalar bunun çok altında kalır.
- `.ts` dosyalarını sitenin oynatma listesi `index.m3u8` içindeki adlarla (`seg_000.ts` ...)
  ister; parçaları yeniden adlandırma veya silme.
