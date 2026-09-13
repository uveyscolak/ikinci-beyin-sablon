#!/usr/bin/env python3
"""Kullanıcının istemi bir projeye ya da çalışma alanına değiniyorsa onun kurallarını
ve güncel durumunu enjekte eder."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

KURALLAR_TAVAN = 12000
DURUM_TAVAN = 8000
TOPLAM_TAVAN = 40000
EN_FAZLA_PROJE = 2
EN_FAZLA = 3
ALAN_KOKLERI = ["İŞ", "KİŞİSEL"]
ALAN_DERINLIK = 4
EN_KISA_TETIK = 3
RE_FRONTMATTER_AD = re.compile(r"^ad:\s*(.+)$", re.MULTILINE)


def proje_cekirdek(klasor, tur):
    """Proje klasöründe `Durum`, `Kararlar`, `PRD`, `Kurallar` dosyasını bulur (BEYİN alt klasörü yok)."""
    sade = klasor / f"{tur}.md"
    return sade if sade.is_file() else None


def alan_cekirdek(beyin_klasor, tur):
    """Alanın `BEYİN/` klasöründe `Durum`, `Kararlar`, `Kurallar`, `Alan` dosyasını bulur."""
    sade = beyin_klasor / f"{tur}.md"
    return sade if sade.is_file() else None


def alan_dosyasi_mi(isim):
    return isim == "Alan.md"


def alan_adi_oku(sayfa, ad_dosyadan):
    """`Alan.md` ise frontmatter'daki `ad:` alanını okur; yoksa/eksikse dosyadan türetilen adı döner."""
    if sayfa.name != "Alan.md":
        return ad_dosyadan
    try:
        with sayfa.open("r", encoding="utf-8") as f:
            bas = f.read(2048)
    except OSError:
        return ad_dosyadan
    satirlar = bas.splitlines()
    if not satirlar or satirlar[0].strip() != "---":
        return ad_dosyadan
    son = None
    for i, satir in enumerate(satirlar[1:], 1):
        if satir.strip() in ("---", "..."):
            son = i
            break
    if son is None:
        return ad_dosyadan
    blok = "\n".join(satirlar[1:son])
    eslesme = RE_FRONTMATTER_AD.search(blok)
    if eslesme:
        deger = eslesme.group(1).strip().strip("\"'").strip()
        if deger:
            return deger
    return ad_dosyadan
# BİLGİ katmanı: proje ya da alan enjekte edilirken indeksten ilgili kavram satırları
BILGI_EN_FAZLA = 5
BILGI_OZET = 120
BILGI_EN_KISA_KELIME = 6  # tetikten anahtar üretirken: 5 karakterden uzun kelimeler

# Tablo satırı: "| [[Ad]] | özet | kaynak | güncellendi |"
RE_INDEKS_SATIR = re.compile(r"^\|\s*(\[\[[^\]]+\]\])\s*\|(.*)$")
# Özet metninde kaçışlı boru (`curl \| bash`) geçebiliyor; yalnız kaçışsız borudan böl.
RE_KACISSIZ_BORU = re.compile(r"(?<!\\)\|")


def nfc(metin: str) -> str:
    # Diskteki adlar NFD gelebilir ("İŞ" = I + birleşen nokta); istemdeki metin NFC'dir.
    # Karşılaştırmadan önce ikisi de aynı biçime çekilmezse eşleşme sessizce kaçar.
    return unicodedata.normalize("NFC", metin)


def kucult(metin: str) -> str:
    # Türkçe: I ve İ'nin karşılığı Python'un lower()'ında yanlış çıkar.
    return nfc(metin).replace("İ", "i").replace("I", "ı").lower()


def kirp(metin: str, tavan: int, not_metni: str) -> str:
    metin = metin.strip()
    if len(metin) <= tavan:
        return metin
    return metin[: tavan - len(not_metni) - 1] + "\n" + not_metni


def indeks_satirlari(vault: Path) -> list[tuple[str, str, str]]:
    """BİLGİ/index.md tablosunu (link, özet, güncellendi) üçlülerine ayrıştırır.

    Kavram makaleleri derleyicinin ürettiği bilgi katmanıdır; buraya kadar hiç
    okunmuyordu. Enjeksiyonda ilgili satırları göstermek için tablo ayrıştırılır.
    """
    try:
        metin = (vault / "BİLGİ" / "index.md").read_text(encoding="utf-8")
    except OSError:
        return []
    kayitlar: list[tuple[str, str, str]] = []
    for satir in metin.splitlines():
        eslesme = RE_INDEKS_SATIR.match(satir.strip())
        if not eslesme:
            continue
        link = nfc(eslesme.group(1))
        parcalar = [p.strip() for p in RE_KACISSIZ_BORU.split(eslesme.group(2))]
        while parcalar and not parcalar[-1]:
            parcalar.pop()
        if len(parcalar) < 3:
            continue
        kayitlar.append((link, nfc(parcalar[0]), nfc(parcalar[-1])))
    return kayitlar


def bilgi_anahtarlari(ad: str, tetikler: list[str]) -> list[str]:
    """Eşleme anahtarları: adın kendisi ve tetiklerin 5 karakterden uzun kelimeleri."""
    anahtarlar = {kucult(ad)}
    for tetik in tetikler:
        for kelime in re.split(r"[\s,/]+", tetik):
            kelime = kelime.strip(".:;()[]\"'").strip()
            if len(kelime) >= BILGI_EN_KISA_KELIME:
                anahtarlar.add(kucult(kelime))
    return [a for a in anahtarlar if a]


def bilgi_blogu(kayitlar: list[tuple[str, str, str]], anahtarlar: list[str]) -> str:
    """İndeks satırlarından anahtarlarla eşleşenleri kısa bir blok olarak döndürür.

    En yeni "güncellendi" tarihi önce gelir, en fazla beş satır. Eşleşme yoksa boş.
    """
    if not kayitlar or not anahtarlar:
        return ""
    secilen: list[tuple[str, str, str]] = []
    for link, ozet, guncellendi in kayitlar:
        govde_metni = kucult(link + " " + ozet)
        if any(anahtar in govde_metni for anahtar in anahtarlar):
            secilen.append((link, ozet, guncellendi))
    if not secilen:
        return ""
    # Sıralama kararlıdır: aynı tarihli satırlar indeksteki sırasını korur.
    secilen.sort(key=lambda k: k[2], reverse=True)
    satirlar = ["\n--- BİLGİ'de ilgili kavramlar ---"]
    for link, ozet, guncellendi in secilen[:BILGI_EN_FAZLA]:
        kisa = ozet[:BILGI_OZET].rstrip()
        satirlar.append(f"- {link} — {kisa} (güncellendi: {guncellendi})")
    return "\n".join(satirlar)


# Eğitim kaynakları bloğu: alan/proje tetiklenince BEYİN/TARİFLER (proje için TARİFLER)
# klasöründeki damıtılmış tarifler, Durum'daki Kaynaklar maddeleri ve EĞİTİMLER/YOUTUBE'daki
# ilgili videolar tek blokta gösterilir; kullanıcı hatırlatmasın.
EGITIM_TAVAN = 3000
RE_ILK_LINK = re.compile(r"\[\[([^|\]]+)")


def _tarif_aciklama(dosya: Path) -> str:
    """Tarif dosyasının H1'inden sonraki ilk boş olmayan, başlık olmayan satırını döner.

    Baştaki `> ` (alıntı) ve `**...**` (kalın) gibi işaretler atılır, 120 karakterde kesilir.
    Açıklama bulunamazsa boş döner.
    """
    try:
        satirlar = dosya.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    h1_gecti = False
    for satir in satirlar:
        s = satir.strip()
        if not h1_gecti:
            if s.startswith("# "):
                h1_gecti = True
            continue
        if not s or s.startswith("#"):
            continue
        s = s.lstrip(">").strip()
        s = s.replace("**", "").strip()
        # "Kaynak: 2026-07-28 oturumu" gibi üst bilgi satırları açıklama değildir; atla.
        if not s or re.match(r"^(Kaynak|Tarih|Eklendi|Güncellendi|Durum)\s*:", s):
            continue
        return s[:120].rstrip()
    return ""


def tarifler_maddeleri(vault: Path, tarifler_klasor: Path) -> list[str]:
    """`<alan/proje>/[BEYİN/]TARİFLER/*.md` dosyalarını ad sırasıyla listeler.

    Biçim: `[[<vault'a göre yol, uzantısız>|<dosya adı>]] — <açıklama>` (açıklama yoksa atlanır).
    """
    if not tarifler_klasor.is_dir():
        return []
    sonuc = []
    for dosya in sorted(tarifler_klasor.glob("*.md"), key=lambda p: nfc(p.name)):
        try:
            rel = dosya.relative_to(vault)
        except ValueError:
            continue
        yol = nfc(str(rel.with_suffix("")))
        ad = nfc(dosya.stem)
        aciklama = _tarif_aciklama(dosya)
        if aciklama:
            sonuc.append(f"[[{yol}|{ad}]] — {aciklama}")
        else:
            sonuc.append(f"[[{yol}|{ad}]]")
    return sonuc


def youtube_alan_maddeleri(vault: Path, alan_klasor_rel: str) -> list[str]:
    """`EĞİTİMLER/YOUTUBE/00 İçindekiler.md` tablosunda Alan sütunu verilen alan klasörüne
    (`<alan klasörü>/BEYİN/Alan`) giden satırları `- [[yol|başlık]] — özet` biçiminde döner.

    Yol eşleşmesi yeter, alias'a bakılmaz. Tablo hücreleri kaçışlı boru içerebiliyor
    (`\\|` bir wiki-link içinde), bu yüzden kaçışsız borudan bölünür (RE_KACISSIZ_BORU).
    """
    try:
        metin = (vault / "EĞİTİMLER" / "YOUTUBE" / "00 İçindekiler.md").read_text(encoding="utf-8")
    except OSError:
        return []
    hedef = nfc(f"{alan_klasor_rel}/BEYİN/Alan").casefold()
    sonuc = []
    for satir in metin.splitlines():
        s = satir.strip()
        if not s.startswith("|") or set(s) <= {"|", "-", " "}:
            continue
        hucreler = [p.strip() for p in RE_KACISSIZ_BORU.split(s)]
        hucreler = [h for h in hucreler if h or hucreler.index(h) not in (0, len(hucreler) - 1)]
        # Baştaki ve sondaki boş hücreler (satırın kenar boruları) atılır.
        if hucreler and hucreler[0] == "":
            hucreler = hucreler[1:]
        if hucreler and hucreler[-1] == "":
            hucreler = hucreler[:-1]
        if len(hucreler) < 5:
            continue
        video_hucre, _kanal, _sure, alan_hucre, ozet_hucre = hucreler[:5]
        alan_link = RE_ILK_LINK.search(alan_hucre)
        if not alan_link:
            continue
        if nfc(alan_link.group(1).strip().rstrip("\\")).casefold() != hedef:
            continue
        video_link = RE_ILK_LINK.search(video_hucre)
        if not video_link:
            continue
        not_yolu = nfc(video_link.group(1).strip().rstrip("\\"))
        baslik_m = re.search(r"\|([^\]]+)\]\]", video_hucre)
        baslik = nfc(baslik_m.group(1).strip()) if baslik_m else not_yolu
        sonuc.append(f"[[{not_yolu}|{baslik}]] — {nfc(ozet_hucre.strip())}")
    return sonuc


def egitim_kaynaklari_blogu(
    ad: str, tarif_maddeler: list[str], durum_maddeler: list[str], youtube_maddeler: list[str]
) -> str:
    """TARİFLER, Durum'daki Kaynaklar maddeleri ve YouTube eşleşmelerini tek blokta birleştirir.

    Sıra: (1) TARİFLER, (2) Durum Kaynakları, (3) YouTube. Bir yol daha önce geçtiyse
    (hangi kaynaktan olursa olsun) tekrar eklenmez, ilk geçtiği yerde kalır. Üç kaynak da
    boşsa boş döner (blok hiç basılmaz). EGITIM_TAVAN'ı aşarsa madde sayısı kesilir.
    """
    if not tarif_maddeler and not durum_maddeler and not youtube_maddeler:
        return ""
    gorulen_yol: set[str] = set()
    maddeler: list[str] = []
    for kaynak in (tarif_maddeler, durum_maddeler, youtube_maddeler):
        for madde in kaynak:
            m = RE_ILK_LINK.search(madde)
            yol = nfc(m.group(1).strip()).casefold() if m else None
            if yol and yol in gorulen_yol:
                continue
            maddeler.append(madde)
            if yol:
                gorulen_yol.add(yol)

    baslik = f"\n[Eğitim kaynakları — {ad}]"
    kuyruk = (
        "\nBu alanda plan, script, strateji ya da içerik yazmadan önce ilgili kaynağı oku; "
        "kullanıcının söylemesini bekleme. Uzun kaynakta ilgili bölümü `arastirmaci` ajanına "
        "çıkarttır. Kaynaklar birbiriyle çelişiyorsa iki planı da sun. Kaynağın dediğine "
        "katılmıyorsan kendi fikrini ayrı ve işaretli ver. Kurallar dosyasındaki \"önce oku\" "
        "dosyaları da bu listenin parçasıdır. TARİFLER klasöründeki dosyalar o işin adım adım "
        "tarifidir; ilgili olanı uygula, yorum katma."
    )
    gosterilecek = list(maddeler)
    while gosterilecek:
        gövde_satirlari = "\n".join(f"- {m}" for m in gosterilecek)
        eksik = len(maddeler) - len(gosterilecek)
        kesme_notu = f"\n[not: {eksik} kaynak daha, Durum dosyasındaki Kaynaklar listesine bak]" if eksik else ""
        blok = basilik_birlestir(baslik, gövde_satirlari, kesme_notu, kuyruk)
        if len(blok) <= EGITIM_TAVAN or len(gosterilecek) == 1:
            return blok
        gosterilecek = gosterilecek[:-1]
    return ""


def basilik_birlestir(baslik: str, govde_satirlari: str, kesme_notu: str, kuyruk: str) -> str:
    return f"{baslik}\n{govde_satirlari}{kesme_notu}{kuyruk}"


def durum_kaynak_maddeleri(durum: Path | None) -> list[str]:
    """Durum dosyasının TAMAMINDAN `## Kaynaklar` madde satırlarını okur (kırpmadan bağımsız)."""
    if durum is None or not durum.is_file():
        return []
    try:
        _, maddeler = durum_kaynaklar_ayikla(durum.read_text(encoding="utf-8"))
    except OSError:
        return []
    return maddeler


def tetikleri_oku(yol: Path) -> list[str]:
    """Dosyanın başındaki YAML frontmatter'dan `tetik:` listesini çıkarır.

    Üç biçim: `tetik: [a, b]`, `tetik: a, b` ve alt satırlarda `- a`.
    pyyaml yok; kanca her istemde çalıştığı için bağımlılık istemiyoruz.
    """
    try:
        with yol.open("r", encoding="utf-8") as dosya:
            bas = dosya.read(2048)
    except OSError:
        return []
    satirlar = bas.splitlines()
    if not satirlar or satirlar[0].strip() != "---":
        return []
    son = None
    for i, satir in enumerate(satirlar[1:], 1):
        if satir.strip() in ("---", "..."):
            son = i
            break
    if son is None:
        return []

    ham: list[str] = []
    i = 1
    while i < son:
        eslesme = re.match(r"^tetik\s*:\s*(.*)$", satirlar[i])
        if not eslesme:
            i += 1
            continue
        kalan = eslesme.group(1).strip()
        if kalan:
            ham += kalan.strip("[]").split(",")
        else:
            j = i + 1
            while j < son:
                alt = re.match(r"^\s*-\s+(.+?)\s*$", satirlar[j])
                if not alt:
                    break
                ham.append(alt.group(1))
                j += 1
            i = j - 1
        i += 1

    temiz = []
    for parca in ham:
        parca = parca.strip().strip("\"'").strip()
        if len(parca) >= EN_KISA_TETIK:
            temiz.append(kucult(parca))
    return temiz


def alanlari_bul(vault: Path, kokler: list[str]) -> list[tuple[str, Path]]:
    """Alan köklerinin altında en çok ALAN_DERINLIK katmanda `BEYİN/Alan.md` arar.

    Alan klasörü BEYİN'in üst klasörüdür; alanın adı o klasörün adı ya da
    Alan.md'nin frontmatter'ındaki `ad:` alanı. "BEYİN" hiçbir zaman alan adı sayılmaz.
    """
    bulunan: list[tuple[str, Path]] = []
    for kok_adi in kokler:
        kok = vault / kok_adi
        if not kok.is_dir():
            continue
        temel = len(kok.parts)
        for dizin, altlar, dosyalar in os.walk(kok):
            simdiki = Path(dizin)
            if len(simdiki.parts) - temel >= ALAN_DERINLIK - 1:
                altlar[:] = []
            else:
                altlar[:] = [a for a in altlar if not a.startswith(".")]
            if simdiki.name != "BEYİN":
                continue
            for dosya in dosyalar:
                isim = nfc(dosya)
                if alan_dosyasi_mi(isim):
                    sayfa = simdiki / dosya
                    ad_dosyadan = simdiki.parent.name
                    bulunan.append((alan_adi_oku(sayfa, ad_dosyadan), sayfa))
    bulunan.sort(key=lambda p: p[0])
    return bulunan


RE_BASLIK = re.compile(r"(?m)^##\s+(.+?)\s*$")


def durum_kaynaklar_ayikla(durum_metni: str) -> tuple[str, list[str]]:
    """Durum metnindeki `## Kaynaklar` bölümünü ayıklar.

    Döner: (kaynaklar bölümü çıkarılmış metin, madde satırları listesi ("- " sonrası)).
    Bölüm dosyanın sonunda olduğu için DURUM_TAVAN kırpması onu düşürüyordu; bu yüzden
    kırpmadan önce ayrı çıkarılır, kırpma boşa gitmez.
    """
    eslesmeler = list(RE_BASLIK.finditer(durum_metni))
    for i, m in enumerate(eslesmeler):
        if m.group(1).strip().casefold() != "kaynaklar":
            continue
        bas = m.start()
        bit = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(durum_metni)
        bolum = durum_metni[m.end():bit]
        maddeler = [
            satir.strip()[2:].strip()
            for satir in bolum.splitlines()
            if satir.strip().startswith("- ")
        ]
        kalan = (durum_metni[:bas] + durum_metni[bit:]).strip()
        return kalan, maddeler
    return durum_metni, []


def govde(baslik: str, konum: str, kurallar: Path | None, durum: Path | None, durum_adi: str,
          yok_notu: str, ne: str, bilgi: str = "", egitim: str = "") -> str:
    bolum = [baslik, f"Klasör: {konum}"]
    if kurallar is not None and kurallar.is_file():
        try:
            bolum.append(
                "\n--- Kurallar ---\n"
                + kirp(kurallar.read_text(encoding="utf-8"), KURALLAR_TAVAN,
                       "[not: kurallar kırpıldı, tamamı için dosyayı aç]")
            )
        except OSError:
            pass
    else:
        bolum.append("\n" + yok_notu)
    if durum is not None and durum.is_file():
        try:
            durum_metni, _ = durum_kaynaklar_ayikla(durum.read_text(encoding="utf-8"))
            bolum.append(
                "\n--- " + durum_adi + f" ({ne} şu anki hâli) ---\n"
                + kirp(durum_metni, DURUM_TAVAN,
                       "[not: durum kırpıldı, tamamı için dosyayı aç]")
            )
        except OSError:
            pass
    if egitim:
        bolum.append(egitim)
    if bilgi:
        bolum.append(bilgi)
    return "\n".join(bolum)


def main() -> int:
    vault = Path(os.environ.get("BEYIN_VAULT", ""))
    durum_dizin = Path(os.environ.get("BEYIN_DURUM", ""))
    if not vault.is_dir():
        return 0

    try:
        girdi = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError, IndexError):
        return 0
    istem = girdi.get("prompt")
    oturum = girdi.get("session_id")
    if not isinstance(istem, str) or not istem.strip():
        return 0
    # Yalnız kullanıcının kendi yazdığı mesaj sayılır. Arka plan ajan bildirimleri, sistem
    # hatırlatmaları ve kanca çıktıları da bu olaydan geçer; içlerinde geçen proje adı
    # yönerge yüklememeli (2026-09-06: bir ajan raporunda proje adı geçince yüklendi).
    bas = istem.lstrip()[:200]
    if bas.startswith(("<system-reminder", "<task-notification", "[SYSTEM NOTIFICATION")) \
            or "<task-notification>" in istem or "[SYSTEM NOTIFICATION" in istem:
        return 0

    ayar = {}
    try:
        ayar = json.loads((vault / ".claude" / "beyin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ayar = {}
    if not isinstance(ayar, dict):
        ayar = {}

    # ---- projeler ----
    adlar: list[str] = []
    projeler_kok = None
    kok = ayar.get("projeler")
    if isinstance(kok, str) and kok:
        aday = Path(kok).expanduser()
        if aday.is_dir():
            projeler_kok = aday
    # Proje adları YALNIZ vault'un PROJELER klasöründen okunur; ayrı kayıt yoktur
    # (anayasa, "Projelerde çalışma düzeni"). Kod kökündeki klasörler ad kaynağı
    # değildir: orada arşiv, deneme ve taşınmış proje kalıntıları da duruyor ve
    # bunlar sohbette geçince boş yönerge enjekte ediyordu. Kod kökü yalnız
    # projenin kod konumunu yazmak için kullanılır (aşağıda `konum`).
    # Bir klasörü proje yapan şey Durum'udur: `Durum.md` yoksa proje değildir.
    vault_projeler = vault / "PROJELER"
    adlar_kume = set()
    if vault_projeler.is_dir():
        for d in vault_projeler.iterdir():
            if not d.is_dir() or d.name.startswith("."):
                continue
            ad_nfc = nfc(d.name)
            if proje_cekirdek(d, "Durum") is not None:
                adlar_kume.add(ad_nfc)
    adlar = sorted(adlar_kume)

    # ---- alanlar ----
    kokler = ayar.get("alan_kokleri")
    if not isinstance(kokler, list) or not all(isinstance(k, str) for k in kokler):
        kokler = ALAN_KOKLERI
    alanlar = alanlari_bul(vault, kokler)

    # Aynı oturumda aynı proje ya da alan bir kez enjekte edilir.
    gorulen: set[str] = set()
    izlek = None
    if isinstance(oturum, str) and oturum and durum_dizin.is_dir():
        anahtar = hashlib.sha256(oturum.encode("utf-8")).hexdigest()
        izlek = durum_dizin / f"yonerge-verilen.{anahtar}"
        if izlek.exists():
            try:
                gorulen = set(izlek.read_text(encoding="utf-8").split("\n"))
            except OSError:
                gorulen = set()

    # Aynı ad hem proje hem alan olarak görünüyorsa alan kazanır: alan sayfası bilinçli bir
    # beyan, koddaki klasör yalnızca bir dizin. Proje alandan taşındığında kod klasörü yerinde
    # kalıyor ve iki kayıt birden enjekte oluyordu (2026-09-06).
    alan_adlari = {ad for ad, _ in alanlar}

    eslesen_proje = []
    for ad in adlar:
        if ad in gorulen or ad in alan_adlari:
            continue
        kalip = re.escape(ad).replace(r"\ ", r"[\s-]?")
        if re.search(rf"(?<![\wçğıöşüÇĞİÖŞÜ]){kalip}(?![\wçğıöşüÇĞİÖŞÜ])", istem, re.IGNORECASE):
            eslesen_proje.append(ad)
    eslesen_proje = eslesen_proje[:EN_FAZLA_PROJE]

    istem_kucuk = kucult(istem)
    eslesen_alan = []
    for ad, sayfa in alanlar:
        if f"alan:{ad}" in gorulen:
            continue
        if kucult(ad) in istem_kucuk or any(t in istem_kucuk for t in tetikleri_oku(sayfa)):
            eslesen_alan.append((ad, sayfa))
    eslesen_alan = eslesen_alan[: max(0, EN_FAZLA - len(eslesen_proje))]

    if not eslesen_proje and not eslesen_alan:
        return 0

    kayitlar = indeks_satirlari(vault)

    parcalar = []
    verilen = []
    toplam = 0
    for ad in eslesen_proje:
        konum = str(projeler_kok / ad) if projeler_kok is not None else "kod klasörü yok"
        proje_klasor = vault / "PROJELER" / ad
        durum_dosyasi = proje_cekirdek(proje_klasor, "Durum")
        # Proje klasörünün İçindekiler tablosunda alan sütunuyla eşleşen bir yolu yoktur
        # (o sütun yalnız BEYİN/Alan.md hedeflerini gösterir); YouTube tarafı doğal olarak boş.
        # Proje için TARİFLER doğrudan proje klasöründedir (BEYİN alt klasörü yok).
        egitim = egitim_kaynaklari_blogu(
            ad, tarifler_maddeleri(vault, proje_klasor / "TARİFLER"),
            durum_kaynak_maddeleri(durum_dosyasi),
            youtube_alan_maddeleri(vault, f"PROJELER/{ad}"),
        )
        metin = govde(
            f"[Proje: {ad}]", konum,
            proje_cekirdek(proje_klasor, "Kurallar"),
            durum_dosyasi,
            "Durum.md",
            "Bu projenin özel kuralları yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            "projenin",
            bilgi_blogu(kayitlar, bilgi_anahtarlari(ad, [])),
            egitim,
        )
        if parcalar and toplam + len(metin) > TOPLAM_TAVAN:
            break
        parcalar.append(metin)
        verilen.append(ad)
        toplam += len(metin)
    for ad, sayfa in eslesen_alan:
        # Alan adı BEYİN'in üst klasöründen gelir; sayfa BEYİN/Alan.md'dir.
        beyin_klasor = sayfa.parent
        alan_klasor = beyin_klasor.parent
        durum_dosyasi = alan_cekirdek(beyin_klasor, "Durum")
        alan_klasor_rel = str(alan_klasor.relative_to(vault))
        egitim = egitim_kaynaklari_blogu(
            ad, tarifler_maddeleri(vault, beyin_klasor / "TARİFLER"),
            durum_kaynak_maddeleri(durum_dosyasi),
            youtube_alan_maddeleri(vault, alan_klasor_rel),
        )
        metin = govde(
            f"[Alan: {ad}]", str(alan_klasor),
            alan_cekirdek(beyin_klasor, "Kurallar"),
            durum_dosyasi,
            "BEYİN/Durum.md",
            "Bu alanın özel kuralları yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            "alanın",
            bilgi_blogu(kayitlar, bilgi_anahtarlari(ad, tetikleri_oku(sayfa))),
            egitim,
        )
        if parcalar and toplam + len(metin) > TOPLAM_TAVAN:
            break
        parcalar.append(metin)
        verilen.append(f"alan:{ad}")
        toplam += len(metin)

    if not parcalar:
        return 0

    if izlek is not None:
        try:
            izlek.write_text(
                "\n".join(sorted(gorulen | set(verilen))).strip(),
                encoding="utf-8",
            )
        except OSError:
            pass

    print("\n\n".join(parcalar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
