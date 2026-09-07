#!/usr/bin/env python3
"""Kullanıcının istemi bir projeye ya da çalışma alanına değiniyorsa onun yönergesini
ve güncel durumunu enjekte eder."""
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

YONERGE_TAVAN = 12000
DURUM_TAVAN = 8000
TOPLAM_TAVAN = 40000
EN_FAZLA_PROJE = 2
EN_FAZLA = 3
ALAN_KOKLERI = ["İŞ", "KİŞİSEL"]
ALAN_DERINLIK = 3
EN_KISA_TETIK = 3
ALAN_SONEK = " — Alan.md"
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
    """Alan köklerinin altında en çok ALAN_DERINLIK katmanda `<Ad> — Alan.md` arar."""
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
            for dosya in dosyalar:
                isim = nfc(dosya)
                if isim.endswith(ALAN_SONEK):
                    bulunan.append((isim[: -len(ALAN_SONEK)], simdiki / dosya))
    bulunan.sort(key=lambda p: p[0])
    return bulunan


def govde(baslik: str, konum: str, yonerge: Path, durum: Path, durum_adi: str,
          yok_notu: str, ne: str, bilgi: str = "") -> str:
    bolum = [baslik, f"Klasör: {konum}"]
    if yonerge.is_file():
        try:
            bolum.append(
                "\n--- Yönerge ---\n"
                + kirp(yonerge.read_text(encoding="utf-8"), YONERGE_TAVAN,
                       "[not: yönerge kırpıldı, tamamı için dosyayı aç]")
            )
        except OSError:
            pass
    else:
        bolum.append("\n" + yok_notu)
    if durum.is_file():
        try:
            bolum.append(
                "\n--- " + durum_adi + f" ({ne} şu anki hâli) ---\n"
                + kirp(durum.read_text(encoding="utf-8"), DURUM_TAVAN,
                       "[not: durum kırpıldı, tamamı için dosyayı aç]")
            )
        except OSError:
            pass
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
    # Bir klasörü proje yapan şey Context'idir: `<X> Context.md` yoksa proje değildir.
    vault_projeler = vault / "PROJELER"
    adlar_kume = set()
    if vault_projeler.is_dir():
        for d in vault_projeler.iterdir():
            if not d.is_dir() or d.name.startswith("."):
                continue
            ad_nfc = nfc(d.name)
            if (d / f"{ad_nfc} Context.md").is_file():
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
        metin = govde(
            f"[Proje: {ad}]", konum,
            vault / "PROJELER" / ad / f"{ad} Yönerge.md",
            vault / "PROJELER" / ad / f"{ad} Context.md",
            f"{ad} Context.md",
            "Bu projenin özel yönergesi yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            "projenin",
            bilgi_blogu(kayitlar, bilgi_anahtarlari(ad, [])),
        )
        if parcalar and toplam + len(metin) > TOPLAM_TAVAN:
            break
        parcalar.append(metin)
        verilen.append(ad)
        toplam += len(metin)
    for ad, sayfa in eslesen_alan:
        klasor = sayfa.parent
        metin = govde(
            f"[Alan: {ad}]", str(klasor),
            klasor / f"{ad} Yönerge.md",
            klasor / f"{ad} Context.md",
            f"{ad} Context.md",
            "Bu alanın özel yönergesi yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            "alanın",
            bilgi_blogu(kayitlar, bilgi_anahtarlari(ad, tetikleri_oku(sayfa))),
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
