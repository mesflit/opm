# opm — One Punch Man video deposu

[mes-anime](https://github.com/mesflit/mes-anime) sitesinin One Punch Man bölümlerini tutan depo.
Burada site kodu yok; sadece şifreli video parçaları, altyazılar ve bölüm listesi (`mes.anime`) var.
Site bu dosyaları doğrudan `raw.githubusercontent.com/mesflit/opm/main/...` adresinden okur.

## Yapı

    opm/
    ├── mes.anime          # Anime bilgisi + bölüm listesi (site bunu okur)
    ├── resize.py          # Bölümlere 480p kopya ekler (orijinallere dokunmaz)
    ├── poster.jpg         # Kapak görseli
    ├── s1/                # 1. sezon
    │   ├── ep1/
    │   │   ├── index.m3u8 # HLS oynatma listesi (AES-128, anahtar URI'si "enc.key")
    │   │   ├── seg_000.ts # ~6 sn'lik şifreli video parçaları
    │   │   ├── ...
    │   │   ├── 480p/      # resize.py'nin kopyası (varsa): index.m3u8 + seg_XXX.ts
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

Tüm işler mes-anime deposundaki `mes.py` ile yapılır. İki depo yan yana durur
(`~/mes-anime`, `~/opm`); `mes.py` bu depoyu yoksa videolar olmadan kendisi klonlar.

**Yeni bölüm(ler):**

    cd ~/mes-anime
    python3 mes.py ekle opm /sdcard/Download/bolum.mkv --sezon 3          # numara kendiliğinden (S3'te 13)
    python3 mes.py ekle opm /sdcard/Download/sezon4/ --sezon 4            # klasördeki hepsi
    python3 mes.py ekle opm bolum.mkv --sezon 3 --bolum 13 --baslik "Final"

Video şifrelenir, altyazılar hazırlanır (videodaki İngilizce + otomatik Türkçe), `mes.anime`
güncellenir ve her bölüm ayrı gönderilir; yüklenen `.ts` dosyaları diskten silinir.

**Bölüm klasörlerini başka yolla eklediysen** (hazır `index.m3u8` + `.ts` kopyaladıysan):

    cd ~/mes-anime && python3 mes.py guncelle opm

**Sadece klonlamak için** (8 GB yerine ~3 MB): `python3 mes.py klonla opm`

Push'tan birkaç dakika sonra (GitHub önbelleği ~5 dk) bölüm sitede görünür. mes-anime'ye push gerekmez.
Ayrıntılar: mes-anime/README.md

## 480p kopya (resize.py)

İnternet yavaş olanlar için bölümlere 480p kopya eklenir. **Orijinal dosyalara dokunulmaz**,
kopya bölüm klasörünün içine `480p/` olarak yazılır ve aynı anahtarla şifrelenir.

    cd ~/opm
    python3 resize.py                  # 480p'si olmayan tüm bölümler
    python3 resize.py s3               # sadece 3. sezon
    python3 resize.py s1/ep1 s2/ep4    # sadece bu bölümler
    python3 resize.py --gonder         # her bölümden sonra commit + push (önerilen)

- Sadece python3 ve ffmpeg gerekir; mes-anime'ye gerek yok.
- Şifre anahtarı: `VIDEO_SECRET_KEY` -> `~/.mes-anime-anahtar` -> yayındaki site (kendisi alır).
- Videolarsız klonda orijinal parçalar GitHub'dan indirilir; tam klonda diskten okunur.
- `mes.anime`'de bölümün satırına `variants`, `bandwidth`, `resolution` yazılır. Site bunu görünce
  oynatıcının ⚙️ menüsünde "Kalite: Otomatik / 1080p / 480p" gösterir; "Otomatik"te internet
  yavaşsa kendiliğinden 480p'ye düşer. İndirme düğmelerine "480p (küçük dosya)" eklenir.
- Orijinali zaten 480p veya küçükse kopya yapılmaz (`no_variants` işaretlenir).
- Yarıda kalırsa tekrar çalıştır; kopyası olan bölümleri atlar (`--hepsi` ile yeniden yapar).
- Uzun iştir (bölüm başına birkaç dakika). Telefonda yavaş olur, PC'de çalıştırmak daha iyi.
- Depo büyür (480p kopya orijinalin yaklaşık 1/3-1/10'u kadar).
- Bir kopyayı kaldırmak: `git rm -r s1/ep1/480p`, sonra mes.anime'de o satırdan `variants` kısmını sil.
- Başka animeye kopyalanabilir: `resize.py`'yi o deponun köküne koyman yeter.

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
