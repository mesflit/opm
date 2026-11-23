#!/usr/bin/env python3
"""Bölümlere 480p kopya ekler. Orijinal dosyalara DOKUNMAZ.

Kullanım (bu deponun klasöründe):
    python3 resize.py                  # 480p'si olmayan tüm bölümler
    python3 resize.py s3               # sadece 3. sezon
    python3 resize.py s1/ep1 s2/ep4    # sadece bu bölümler
    python3 resize.py --gonder         # her bölümden sonra commit + push

Her bölüm için:  sN/epM/index.m3u8 + seg_*.ts  (orijinal, aynen kalır)
                 sN/epM/480p/index.m3u8 + seg_*.ts  (yeni, aynı anahtarla şifreli)
ve mes.anime'de bölümün satırına "variants" eklenir; site bunu görünce kalite menüsü gösterir.

Gerekenler: python3, ffmpeg. Başka hiçbir şey gerekmez (mes-anime'ye ihtiyaç yok).
Şifre anahtarı sırayla: VIDEO_SECRET_KEY ortam değişkeni -> ~/.mes-anime-anahtar -> yayındaki site.
Orijinal parçalar diskte yoksa (videolarsız klon) GitHub'dan indirilir.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KOK = Path(__file__).resolve().parent
KATALOG = KOK / "mes.anime"
ANAHTAR_DOSYASI = Path.home() / ".mes-anime-anahtar"
BOLUM = re.compile(r"^s(\d+)/ep(\d+)$")


def hata(m):
    sys.exit(f"❌ {m}")


def calistir(komut, **kw):
    return subprocess.run([str(k) for k in komut], check=True, **kw)


def cikti(komut):
    r = subprocess.run([str(k) for k in komut], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


# ---------- depo bilgisi ----------

def depo_adresi():
    """('mesflit', 'opm'): git remote'tan, yoksa klasör adından."""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", cikti(["git", "-C", KOK, "remote", "get-url", "origin"]))
    return (m[1], m[2]) if m else (os.environ.get("GH_USER", "mesflit"), KOK.name)


# ---------- anahtar ----------

def anahtar(sahip):
    k = os.environ.get("VIDEO_SECRET_KEY", "").strip()
    if not k and ANAHTAR_DOSYASI.exists():
        k = ANAHTAR_DOSYASI.read_text(encoding="utf-8").strip()
    if not k:
        site = os.environ.get("MES_SITE", f"https://{sahip}.github.io/mes-anime/")
        print(f"🔑 Anahtar bu cihazda yok, siteden alınıyor ({site})")
        try:
            with urllib.request.urlopen(site, timeout=30) as r:
                m = re.search(r'const SECRET_KEY = "([^"]*)"', r.read().decode("utf-8", "ignore"))
        except Exception as e:
            hata(f"Site okunamadı: {e}. Anahtarı VIDEO_SECRET_KEY ile ver.")
        if not m or not m[1] or m[1] == "__VIDEO_SECRET_KEY__":
            hata("Sitede anahtar bulunamadı. Anahtarı VIDEO_SECRET_KEY ile ver.")
        k = m[1]
        ANAHTAR_DOSYASI.write_text(k + "\n", encoding="utf-8")
        print(f"🔑 Kaydedildi: {ANAHTAR_DOSYASI}")
    return hashlib.sha256(k.encode("utf-8")).digest()[:16]   # site ile aynı türetme


# ---------- mes.anime ----------

def katalog_oku():
    if not KATALOG.exists():
        return {"episodes": []}
    try:
        return json.loads(KATALOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        hata(f"mes.anime bozuk: {e}")


def katalog_yaz(bilgi):
    """mes-anime'deki biçimle aynı: her bölüm tek satır."""
    bas = [f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},"
           for k, v in bilgi.items() if k != "episodes"]
    bol = [f"    {json.dumps(e, ensure_ascii=False)}" for e in bilgi.get("episodes", [])]
    KATALOG.write_text("{\n" + "\n".join(bas) + '\n  "episodes": [\n' + ",\n".join(bol) + "\n  ]\n}\n", encoding="utf-8")


def katalog_isle(yol, orijinal, varyant):
    bilgi = katalog_oku()
    e = next((x for x in bilgi.get("episodes", []) if x.get("path") == yol), None)
    if e is None:
        print(f"⚠️  {yol} mes.anime'de yok; sitede görünmesi için mes-anime'de: python3 mes.py guncelle {KOK.name}")
        return
    if orijinal is None:
        e["no_variants"] = True            # orijinal zaten küçük
    else:
        e["bandwidth"] = orijinal["bandwidth"]
        if orijinal["resolution"]:
            e["resolution"] = orijinal["resolution"]
        e["variants"] = [v for v in e.get("variants", []) if v.get("name") != varyant["name"]] + [varyant]
        e["variants"].sort(key=lambda v: -int(re.sub(r"\D", "", v["name"]) or 0))
    katalog_yaz(bilgi)


# ---------- dönüştürme ----------

def parcalar(m3u8):
    sure, sonuc = 0.0, []
    for s in m3u8.read_text(encoding="utf-8").splitlines():
        s = s.strip()
        if s.startswith("#EXTINF:"):
            sure = float(s[8:].split(",")[0] or 0)
        elif s and not s.startswith("#"):
            sonuc.append((s, sure))
    return sonuc


def bant(klasor, liste):
    toplam = sum(s for _, s in liste) or 1
    return int(sum((klasor / ad).stat().st_size for ad, _ in liste) * 8 / toplam)


def cozunurluk(m3u8):
    j = cikti(["ffprobe", "-v", "error", "-allowed_extensions", "ALL", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "json", m3u8])
    s = (json.loads(j or "{}").get("streams") or [{}])[0]
    return int(s.get("width") or 0), int(s.get("height") or 0)


def indir(url, hedef):
    for deneme in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(hedef, "wb") as f:
                shutil.copyfileobj(r, f)
            return
        except Exception:
            if deneme == 3:
                raise


def kucult(yol, aes, sahip, depo, yukseklik, hiz):
    """yol (ör. 's1/ep1') için <yukseklik>p kopya üretir."""
    kaynak = KOK / yol
    ad = f"{yukseklik}p"
    liste = parcalar(kaynak / "index.m3u8")
    url = f"https://raw.githubusercontent.com/{sahip}/{depo}/main/{yol}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copyfile(kaynak / "index.m3u8", tmp / "index.m3u8")
        (tmp / "enc.key").write_bytes(aes)

        def getir(dosya):
            if (kaynak / dosya).exists():
                shutil.copyfile(kaynak / dosya, tmp / dosya)
            else:
                indir(f"{url}/{dosya}", tmp / dosya)
        eksik = sum(not (kaynak / d).exists() for d, _ in liste)
        if eksik:
            print(f"⬇️  {eksik} parça GitHub'dan indiriliyor")
        with ThreadPoolExecutor(8) as havuz:
            list(havuz.map(getir, [d for d, _ in liste]))

        g, y = cozunurluk(tmp / "index.m3u8")
        if not y:
            hata(f"{yol} çözülemedi: şifre anahtarı yanlış olabilir")
        orijinal = {"bandwidth": bant(tmp, liste), "resolution": f"{g}x{y}"}
        if y <= yukseklik:
            print(f"ℹ️  Orijinal zaten {y}p, {ad} gereksiz")
            return None, None

        cikis = kaynak / ad
        if cikis.exists():
            shutil.rmtree(cikis)
        cikis.mkdir()
        (tmp / "keyinfo.txt").write_text(f"enc.key\n{tmp / 'enc.key'}\n")
        calistir([
            "ffmpeg", "-v", "warning", "-stats", "-y", "-allowed_extensions", "ALL", "-i", tmp / "index.m3u8",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", f"scale=-2:{yukseklik}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", hiz,
            "-crf", "26", "-maxrate", "1200k", "-bufsize", "2400k",
            "-c:a", "aac", "-b:a", "96k", "-ac", "2",
            "-hls_time", "6", "-hls_playlist_type", "vod",
            "-hls_key_info_file", tmp / "keyinfo.txt",
            "-hls_segment_filename", cikis / "seg_%03d.ts", cikis / "index.m3u8",
        ])

    genislik = round(g * yukseklik / y / 2) * 2
    varyant = {"name": ad, "path": ad, "bandwidth": bant(cikis, parcalar(cikis / "index.m3u8")),
               "resolution": f"{genislik}x{yukseklik}"}
    print(f"✅ {yol}/{ad}: {varyant['bandwidth'] // 1000} kbps (orijinal {orijinal['bandwidth'] // 1000} kbps)")
    return orijinal, varyant


def gonder(yol, ad):
    calistir(["git", "-C", KOK, "add", "--sparse", "-A", yol, "mes.anime"])
    if not cikti(["git", "-C", KOK, "diff", "--cached", "--name-only"]):
        return
    calistir(["git", "-C", KOK, "commit", "-q", "-m", f"feat: {yol} {ad}"])
    calistir(["git", "-C", KOK, "push", "-q"])
    if cikti(["git", "-C", KOK, "config", "core.sparseCheckout"]) == "true":
        calistir(["git", "-C", KOK, "sparse-checkout", "reapply"])      # yüklenen .ts'leri diskten sil
    print(f"⬆️  {yol}/{ad} gönderildi")


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("secim", nargs="*", help="sezon (s3) veya bölüm (s3/ep5); boşsa hepsi")
    p.add_argument("--yukseklik", type=int, default=480, help="hedef kalite (varsayılan 480)")
    p.add_argument("--hepsi", action="store_true", help="kopyası olanları da yeniden yap")
    p.add_argument("--gonder", action="store_true", help="her bölümden sonra commit + push")
    p.add_argument("--hiz", default="veryfast", help="ffmpeg preset (ultrafast/veryfast/medium)")
    a = p.parse_args()

    if not shutil.which("ffmpeg"):
        hata("ffmpeg yok (Termux: pkg install ffmpeg)")
    ad = f"{a.yukseklik}p"
    bilgi = {e.get("path"): e for e in katalog_oku().get("episodes", [])}
    bolumler = sorted((m3u8.parent.relative_to(KOK).as_posix() for m3u8 in KOK.glob("s*/ep*/index.m3u8")
                       if BOLUM.match(m3u8.parent.relative_to(KOK).as_posix())),
                      key=lambda y: tuple(int(x) for x in BOLUM.match(y).groups()))
    if a.secim:
        bolumler = [y for y in bolumler if any(y == s.strip("/") or y.startswith(s.strip("/") + "/") for s in a.secim)]
    if not a.hepsi:
        bolumler = [y for y in bolumler if not (KOK / y / ad / "index.m3u8").exists() and not bilgi.get(y, {}).get("no_variants")]
    if not bolumler:
        print(f"ℹ️  {ad} yapılacak bölüm yok.")
        return

    sahip, depo = depo_adresi()
    aes = anahtar(sahip)
    print(f"🎞️  {len(bolumler)} bölüm {ad}'ye küçültülecek ({sahip}/{depo})")
    for i, yol in enumerate(bolumler, 1):
        print(f"\n━━ [{i}/{len(bolumler)}] {yol}")
        orijinal, varyant = kucult(yol, aes, sahip, depo, a.yukseklik, a.hiz)
        katalog_isle(yol, orijinal, varyant)
        if a.gonder:
            gonder(yol, ad)
    print("\n🎉 Bitti." + ("" if a.gonder else f"  Göndermek için: git add --sparse -A && git commit -m \"feat: {ad}\" && git push"))


if __name__ == "__main__":
    main()
