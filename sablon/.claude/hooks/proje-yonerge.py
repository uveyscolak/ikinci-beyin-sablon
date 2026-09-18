#!/usr/bin/env python3
"""Kullanıcının istemi bir projeye ya da çalışma alanına değiniyorsa onun kurallarını,
güncel durumunu ve kaynaklarını enjekte eder; ayrıca tetik indeksinden tek satır ipucu basar.

Eşleşme kelime bazlıdır, alt dize değil. Eskiden "görsel üretim" cümlesi OPERASYON alanının
"üretim" tetiğini de uyandırıyordu, "atölye e-tablosuna bakalım" ise hiçbir şeyi
uyandırmıyordu. Artık istem kelimelere ayrılır ve bir tetik yalnız bir kelimenin BAŞIYLA
eşleşirse tetiklenir; Türkçe ekler böyle karşılanır ("kampanya" tetiği "kampanyayı" ile
eşleşir), gövde içinde geçen kelime eşleşmez.

Bütün tavanlar beyin.json'daki "sinirlar" bölümünden gelir; bu dosyada sayı tutulmaz.
Toplam çıktı `kanca_istem_karakter` (8.500) sınırını kesinlikle aşmaz.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from _sinirlar import sinirlar as _sinirlar_oku  # noqa: E402

EN_FAZLA_PROJE = 2
EN_FAZLA = 2
ALAN_KOKLERI = ["İŞ", "KİŞİSEL"]
ALAN_DERINLIK = 4
EN_KISA_TETIK = 4        # tetik en az dört harf olmalı; kısası gürültü üretir
IPUCU_TAVAN = 300
EGITIM_TAVAN = 1000
KARARLAR_EN_FAZLA = 3

# --- tetik ipucu puanlaması -------------------------------------------------------------
# Eskiden her eşleşme tek puandı ve "tmm devam edelim", "günaydın bitti mi" gibi genel
# cümleler bile üçer not basıyordu. Artık kaynağa göre ağırlıklandırılır: açık "Tetik:"
# satırı ya da Alan.md tetik listesi en güçlü işarettir, dosya adı orta, `## ` başlığı en
# zayıf. Yalnız toplam puanı IPUCU_ESIK'i geçen notlar basılır.
IPUCU_PUAN_TETIK = 3
IPUCU_PUAN_AD = 2
IPUCU_PUAN_BASLIK = 1
IPUCU_ESIK = 3
EN_KISA_IPUCU = 6        # normal kelime kökü için en az altı harf
EN_KISA_IPUCU_TETIK = 4  # tetik listesinden gelen kelime için en az dört harf yeter
IPUCU_EN_AZ_KELIME = 3   # istem üç anlamlı kelimeden kısaysa ipucu hiç basılmaz

# İstemdeki gürültü kelimeleri: günlük konuşma dolgusu ve vault jargonu. Bunlar tek
# başına hiçbir notu tetiklemez; aksi halde "tmm devam edelim" gibi cümleler bile
# rastgele bir Durum ya da Kararlar dosyasını uyandırıyordu.
IPUCU_DURAK = {
    "devam", "edelim", "bakalım", "kontrol", "yapalım", "bitti", "günaydın", "tamam",
    "tmm", "şimdi", "sonra", "önce", "bugün", "dün", "yarın", "olsun", "gibi", "için",
    "nasıl", "nedir", "hangi", "neyi", "şunu", "bunu", "onu", "dosya", "dosyası",
    "durum", "kararlar", "notlar", "not", "proje", "alan", "iyi", "merhaba", "selam",
    "teşekkür", "sağol", "lütfen", "rica", "acaba", "belki", "galiba", "sanırım",
    "aslında", "yani", "işte", "tabii", "peki", "evet", "hayır", "olabilir", "olur",
    "olmaz", "istiyorum", "istiyorsun", "gerekiyor", "lazım", "biraz", "hemen",
    "az", "çok", "her", "hep", "hiç", "ama", "veya", "ile", "ve", "bir", "bu", "şu",
    "ne", "mi", "mı", "mu", "mü", "de", "da", "ki", "diye", "göre", "kadar", "daha",
    "en", "var", "yok", "oldu", "olacak", "yaptım", "yapayım", "bakayım", "geldi",
    "gitti", "başla", "başlayalım", "devam", "kaldık", "kaldı", "nerede",
}


def _ipucu_kelime_gecerli(kelime: str, en_kisa: int) -> bool:
    return len(kelime) >= en_kisa and kelime not in IPUCU_DURAK

RE_FRONTMATTER_AD = re.compile(r"^ad:\s*(.+)$", re.MULTILINE)
RE_ILK_LINK = re.compile(r"\[\[([^|\]]+)")
RE_KACISSIZ_BORU = re.compile(r"(?<!\\)\|")
RE_BASLIK = re.compile(r"(?m)^##\s+(.+?)\s*$")
RE_GOVDE_TETIK = re.compile(r"(?mi)^\s*tetik\s*:\s*(.+)$")
RE_KARAR_BASLIK = re.compile(r"(?m)^##\s+(\[[^\]]+\].*?)\s*$")


def nfc(metin: str) -> str:
    # Diskteki adlar NFD gelebilir ("İŞ" = I + birleşen nokta); istemdeki metin NFC'dir.
    return unicodedata.normalize("NFC", metin)


def kucult(metin: str) -> str:
    # Türkçe: I ve İ'nin karşılığı Python'un lower()'ında yanlış çıkar.
    return nfc(metin).replace("İ", "i").replace("I", "ı").lower()


def sadelestir(metin: str) -> str:
    """Türkçe harfleri ASCII karşılığına indirir; eşleşme aksandan bağımsız olsun."""
    d = {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"}
    return "".join(d.get(k, k) for k in kucult(metin))


def kelimelere_ayir(metin: str) -> list[str]:
    """İstemi eşleşmeye hazır kelimelere ayırır: küçük harf, Türkçe sadeleştirilmiş."""
    return [k for k in re.split(r"[^0-9a-zçğıöşü]+", kucult(metin)) if k]


def kelime_kokleri(metin: str) -> list[str]:
    return [sadelestir(k) for k in kelimelere_ayir(metin)]


def tetik_eslesti(tetik: str, kelimeler: list[str], en_kisa: int) -> bool:
    """Tetik istemdeki bir kelimenin başıyla eşleşiyor mu.

    Tek kelimelik tetik: bir kelime tetikle BAŞLIYORSA eşleşir ("kampanyayı" ~ "kampanya").
    Çok kelimeli tetik ("görsel üretim"): parçaları istemde aynı sırayla ardışık geçmeli.
    """
    parcalar = [sadelestir(p) for p in re.split(r"[\s/,-]+", tetik) if p.strip()]
    parcalar = [p for p in parcalar if p]
    if not parcalar:
        return False
    if any(len(p) < en_kisa for p in parcalar):
        return False
    if len(parcalar) == 1:
        return any(k.startswith(parcalar[0]) for k in kelimeler)
    n = len(parcalar)
    for i in range(len(kelimeler) - n + 1):
        if all(kelimeler[i + j].startswith(parcalar[j]) for j in range(n)):
            return True
    return False


def proje_cekirdek(klasor: Path, tur: str) -> Path | None:
    sade = klasor / f"{tur}.md"
    return sade if sade.is_file() else None


def alan_cekirdek(beyin_klasor: Path, tur: str) -> Path | None:
    sade = beyin_klasor / f"{tur}.md"
    return sade if sade.is_file() else None


def alan_dosyasi_mi(isim: str) -> bool:
    return isim == "Alan.md"


def _onblok(yol: Path) -> str | None:
    """Dosyanın başındaki `---` bloğunu döner; blok yoksa None."""
    try:
        with yol.open("r", encoding="utf-8") as f:
            bas = f.read(2048)
    except OSError:
        return None
    satirlar = bas.splitlines()
    if not satirlar or satirlar[0].strip() != "---":
        return None
    for i, satir in enumerate(satirlar[1:], 1):
        if satir.strip() in ("---", "..."):
            return "\n".join(satirlar[1:i])
    return None


def alan_adi_oku(sayfa: Path, ad_dosyadan: str) -> str:
    """`Alan.md` ise ön bloktaki `ad:` alanını okur; yoksa dosyadan türetilen adı döner."""
    if sayfa.name != "Alan.md":
        return ad_dosyadan
    blok = _onblok(sayfa)
    if blok is None:
        return ad_dosyadan
    eslesme = RE_FRONTMATTER_AD.search(blok)
    if eslesme:
        deger = eslesme.group(1).strip().strip("\"'").strip()
        if deger:
            return deger
    return ad_dosyadan


def tetikleri_oku(yol: Path) -> list[str]:
    """Alan sayfasının ön bloğundaki `tetik:` listesi.

    Üç biçim: `tetik: [a, b]`, `tetik: a, b` ve alt satırlarda `- a`. pyyaml yok; kanca
    her istemde çalıştığı için bağımlılık istemiyoruz.
    """
    blok = _onblok(yol)
    if blok is None:
        return []
    satirlar = blok.splitlines()
    ham: list[str] = []
    i = 0
    while i < len(satirlar):
        eslesme = re.match(r"^tetik\s*:\s*(.*)$", satirlar[i])
        if not eslesme:
            i += 1
            continue
        kalan = eslesme.group(1).strip()
        if kalan:
            ham += kalan.strip("[]").split(",")
        else:
            j = i + 1
            while j < len(satirlar):
                alt = re.match(r"^\s*-\s+(.+?)\s*$", satirlar[j])
                if not alt:
                    break
                ham.append(alt.group(1))
                j += 1
            i = j - 1
        i += 1
    return [p.strip().strip("\"'").strip() for p in ham if p.strip().strip("\"'").strip()]


def govde_tetikleri(yol: Path | None) -> list[str]:
    """Proje ya da alan sayfasının gövdesinde başlığın altındaki "Tetik: a, b" satırı.

    Ön blok yasak olduğu için proje sayfaları tetiklerini gövdede taşır; ilk 2.000
    karakterde aranır, tek satırdır.
    """
    if yol is None or not yol.is_file():
        return []
    try:
        with yol.open("r", encoding="utf-8") as f:
            bas = f.read(2048)
    except OSError:
        return []
    eslesme = RE_GOVDE_TETIK.search(bas)
    if not eslesme:
        return []
    return [p.strip().strip("\"'").strip() for p in eslesme.group(1).split(",") if p.strip()]


def kirp(metin: str, tavan: int, not_metni: str) -> str:
    metin = metin.strip()
    if len(metin) <= tavan:
        return metin
    return metin[: max(0, tavan - len(not_metni) - 1)].rstrip() + "\n" + not_metni


def alanlari_bul(vault: Path, kokler: list[str]) -> list[tuple[str, Path]]:
    """Alan köklerinin altında en çok ALAN_DERINLIK katmanda `BEYİN/Alan.md` arar."""
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
                    bulunan.append((alan_adi_oku(sayfa, simdiki.parent.name), sayfa))
    bulunan.sort(key=lambda p: p[0])
    return bulunan


def durum_kaynaklar_ayikla(durum_metni: str) -> tuple[str, list[str]]:
    """Durum metnindeki `## Kaynaklar` bölümünü ayıklar.

    Döner: (kaynaklar bölümü çıkarılmış metin, madde satırları listesi).
    Bölüm dosyanın sonunda olduğu için kırpma onu düşürüyordu; bu yüzden kırpmadan önce
    ayrı çıkarılır, kırpma boşa gitmez. Bu koruma bilerek korunuyor.
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


def su_an_ayikla(durum_metni: str, tavan: int) -> str:
    """Durum'un "## Şu An" bölümü; başlık yoksa geçiş döneminde dosyanın ilk `tavan` karakteri.

    Durum dosyaları Faz 3'te yeni biçime geçecek; o güne kadar eski dosyalar da çalışsın diye
    başlık bulunamazsa dosyanın başı alınır.
    """
    eslesmeler = list(RE_BASLIK.finditer(durum_metni))
    for i, m in enumerate(eslesmeler):
        if m.group(1).strip().casefold() not in ("şu an", "su an"):
            continue
        bit = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(durum_metni)
        return kirp(durum_metni[m.end():bit], tavan, "[not: Şu An kırpıldı, dosyayı aç]")
    return kirp(durum_metni, tavan, "[not: Durum kırpıldı, dosyayı aç]")


def son_kararlar(kararlar: Path | None, en_fazla: int) -> str:
    """Kararlar.md'nin en son `## [tarih] ...` başlıkları, tek satır halinde.

    Gerekçe katmanı bugüne kadar hiç basılmıyordu; başlıkların gelmesi "gerekçe var ve
    şurada" bilgisini bağlama sokar, ayrıntı çekilerek okunur.
    """
    if kararlar is None or not kararlar.is_file():
        return ""
    try:
        metin = kararlar.read_text(encoding="utf-8")
    except OSError:
        return ""
    basliklar = [m.group(1).strip() for m in RE_KARAR_BASLIK.finditer(metin)]
    if not basliklar:
        return ""
    secilen = basliklar[-en_fazla:][::-1]
    return "Son kararlar: " + " | ".join(s[:70] for s in secilen)


def _tarif_aciklama(dosya: Path) -> str:
    """Tarif dosyasının H1'inden sonraki ilk anlamlı satırı, 120 karakterde kesilmiş."""
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
        s = s.lstrip(">").strip().replace("**", "").strip()
        if not s or re.match(r"^(Kaynak|Tarih|Eklendi|Güncellendi|Durum)\s*:", s):
            continue
        return s[:120].rstrip()
    return ""


def tarifler_maddeleri(vault: Path, tarifler_klasor: Path) -> list[str]:
    """`TARİFLER/*.md` dosyalarını `[[yol|ad]] — açıklama` biçiminde listeler."""
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
        sonuc.append(f"[[{yol}|{ad}]] — {aciklama}" if aciklama else f"[[{yol}|{ad}]]")
    return sonuc


def youtube_alan_maddeleri(vault: Path, alan_klasor_rel: str) -> list[str]:
    """`EĞİTİMLER/YOUTUBE/00 İçindekiler.md` tablosunda bu alana bağlanan video notları."""
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


def egitim_kaynaklari_blogu(tarif_maddeler: list[str], durum_maddeler: list[str],
                            youtube_maddeler: list[str], tavan: int) -> str:
    """TARİFLER, Durum'daki Kaynaklar maddeleri ve YouTube eşleşmelerini tek blokta birleştirir."""
    if not tarif_maddeler and not durum_maddeler and not youtube_maddeler:
        return ""
    gorulen: set[str] = set()
    maddeler: list[str] = []
    for kaynak in (tarif_maddeler, durum_maddeler, youtube_maddeler):
        for madde in kaynak:
            m = RE_ILK_LINK.search(madde)
            yol = nfc(m.group(1).strip()).casefold() if m else None
            if yol and yol in gorulen:
                continue
            maddeler.append(madde)
            if yol:
                gorulen.add(yol)

    kuyruk = ("\nBu alanda plan, script, strateji ya da içerik yazmadan önce ilgili kaynağı oku;"
              " kullanıcının söylemesini bekleme. TARİFLER klasöründeki dosya o işin adım adım tarifidir.")
    gosterilecek = list(maddeler)
    while gosterilecek:
        govde = "\n".join(f"- {m}" for m in gosterilecek)
        eksik = len(maddeler) - len(gosterilecek)
        kesme = f"\n[not: {eksik} kaynak daha, Durum'un Kaynaklar listesine bak]" if eksik else ""
        blok = f"\n[Kaynaklar]\n{govde}{kesme}{kuyruk}"
        if len(blok) <= tavan or len(gosterilecek) == 1:
            return blok
        gosterilecek = gosterilecek[:-1]
    return ""


def govde(baslik: str, konum: str, kurallar: Path | None, durum: Path | None,
          kararlar: Path | None, yok_notu: str, sinir: dict, egitim: str) -> str:
    """Bir proje ya da alan bloğunu kurar: Kurallar, Şu An, son kararlar, Kaynaklar."""
    bolum = [baslik, f"Klasör: {konum}"]
    if kurallar is not None and kurallar.is_file():
        try:
            bolum.append("\n--- Kurallar ---\n" + kirp(
                kurallar.read_text(encoding="utf-8"), sinir["kurallar_blok_karakter"],
                "[not: kurallar kırpıldı, tamamı için dosyayı aç]"))
        except OSError:
            pass
    else:
        bolum.append("\n" + yok_notu)
    if durum is not None and durum.is_file():
        try:
            durum_metni, _ = durum_kaynaklar_ayikla(durum.read_text(encoding="utf-8"))
            bolum.append("\n--- Şu An ---\n" + su_an_ayikla(durum_metni, sinir["su_an_karakter"]))
        except OSError:
            pass
    kararlar_satiri = son_kararlar(kararlar, KARARLAR_EN_FAZLA)
    if kararlar_satiri:
        bolum.append("\n" + kararlar_satiri + " (gerekçe için Kararlar.md'yi aç)")
    if egitim:
        bolum.append(egitim)
    return "\n".join(bolum)


def tetik_ipucu(vault: Path, kelimeler: list[str], hariç: set[str], en_fazla: int) -> str:
    """`.claude/tetik-indeks.json` ile istem kelimelerini eşleştirip tek satır ipucu basar.

    Puanlama kaynağa göre ağırlıklıdır: "Tetik:" satırı ya da Alan.md tetik listesi 3 puan,
    dosya adı kelimesi 2 puan, `## ` başlık kelimesi 1 puan. Yalnız toplam puanı IPUCU_ESIK'i
    (3) geçen notlar basılır. Kök eşleşmesi için normal kelime en az altı harf, tetik
    listesinden gelen kelime en az dört harf olmalı. İstem üç anlamlı kelimeden kısaysa ya da
    yalnızca durak kelimelerden oluşuyorsa hiçbir şey basılmaz. Zaten bu istemde basılan proje
    ve alan dosyaları listeye girmez.
    """
    try:
        veri = json.loads((vault / ".claude" / "tetik-indeks.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    notlar = veri.get("notlar") if isinstance(veri, dict) else None
    if not isinstance(notlar, list) or not notlar:
        return ""

    # İstemin kendisi anlamlı mı: durak kelimeler çıkarılınca en az üç kelime kalmalı.
    anlamli_kelimeler = [k for k in kelimeler if k not in IPUCU_DURAK]
    if len(anlamli_kelimeler) < IPUCU_EN_AZ_KELIME:
        return ""

    # İki eşik: normal kök için altı harf, tetik listesinden gelen kök için dört harf yeter.
    kok_genis = [k for k in anlamli_kelimeler if _ipucu_kelime_gecerli(k, EN_KISA_IPUCU_TETIK)]
    kok_dar = [k for k in anlamli_kelimeler if _ipucu_kelime_gecerli(k, EN_KISA_IPUCU)]
    if not kok_genis:
        return ""

    puanlar: list[tuple[int, str, str]] = []
    for kayit in notlar:
        if not isinstance(kayit, dict):
            continue
        yol = kayit.get("yol")
        ad = kayit.get("ad")
        if not yol or not ad:
            continue
        if yol in hariç:
            continue
        tetikler = kayit.get("tetik")
        adtetik = kayit.get("adtetik")
        # Geri uyumluluk: "adtetik" yoksa (eski indeks) ad kelimeleri gelmiyor demektir,
        # eski "zayif" alanı başlık kelimeleri olarak kullanılır.
        baslik = kayit.get("baslik", kayit.get("zayif"))
        puan = 0
        katmanlar = (
            (tetikler if isinstance(tetikler, list) else [], IPUCU_PUAN_TETIK, kok_dar),
            (adtetik if isinstance(adtetik, list) else [], IPUCU_PUAN_AD, kok_dar),
            (baslik if isinstance(baslik, list) else [], IPUCU_PUAN_BASLIK, kok_dar),
        )
        for kume, agirlik, havuz in katmanlar:
            for tetik in kume:
                if not isinstance(tetik, str):
                    continue
                # Tetik kümesindeki kelime kısa olabilir (ör. "sms", 4 harf sınırı tetik
                # listesi kelimeleri içindir); istem tarafında yine de en az dört harf ister.
                if len(tetik) < EN_KISA_IPUCU_TETIK:
                    continue
                if any(k.startswith(tetik) or tetik.startswith(k) for k in havuz):
                    puan += agirlik
        if puan >= IPUCU_ESIK:
            puanlar.append((puan, str(ad), str(yol)))
    if not puanlar:
        return ""
    puanlar.sort(key=lambda p: (-p[0], p[1]))
    # Satır tavanı parça parça harcanır; ortadan kesilen bir yol tıklanamaz hale gelir,
    # bu yüzden sığmayan kayıt hiç yazılmaz, kesilmez.
    parcalar: list[str] = []
    uzunluk = len("İlgili notlar: ")
    for _, ad, yol in puanlar[:en_fazla]:
        if len(ad) > 60:
            ad = ad[:57].rstrip() + "..."
        parca = f"{ad} ({yol})"
        ek = len(parca) + (2 if parcalar else 0)
        if uzunluk + ek > IPUCU_TAVAN:
            break
        parcalar.append(parca)
        uzunluk += ek
    if not parcalar:
        return ""
    return "İlgili notlar: " + ", ".join(parcalar)


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
    # Yalnız kullanıcının kendi yazdığı mesaj sayılır. Arka plan ajan bildirimleri ve
    # sistem hatırlatmaları da bu olaydan geçer; içlerinde geçen proje adı yüklememeli.
    bas = istem.lstrip()[:200]
    if bas.startswith(("<system-reminder", "<task-notification", "[SYSTEM NOTIFICATION")) \
            or "<task-notification>" in istem or "[SYSTEM NOTIFICATION" in istem:
        return 0

    sinir = _sinirlar_oku(vault)
    try:
        ayar = json.loads((vault / ".claude" / "beyin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ayar = {}
    if not isinstance(ayar, dict):
        ayar = {}

    kelimeler = kelime_kokleri(istem)
    if not kelimeler:
        return 0

    projeler_kok = None
    kok = ayar.get("projeler")
    if isinstance(kok, str) and kok:
        aday = Path(kok).expanduser()
        if aday.is_dir():
            projeler_kok = aday

    # Proje adları yalnız vault'un PROJELER klasöründen okunur; bir klasörü proje yapan
    # şey Durum.md'sidir.
    vault_projeler = vault / "PROJELER"
    adlar: list[str] = []
    if vault_projeler.is_dir():
        adlar = sorted({nfc(d.name) for d in vault_projeler.iterdir()
                        if d.is_dir() and not d.name.startswith(".")
                        and proje_cekirdek(d, "Durum") is not None})

    kokler = ayar.get("alan_kokleri")
    if not isinstance(kokler, list) or not all(isinstance(k, str) for k in kokler):
        kokler = ALAN_KOKLERI
    alanlar = alanlari_bul(vault, kokler)

    # Aynı oturumda aynı proje ya da alan bir kez enjekte edilir. İz dosyası oturum
    # kimliğinin sha256'sıdır; pre-compact.sh bağlam özetlenince onu siler.
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

    alan_adlari = {ad for ad, _ in alanlar}

    # --- eşleşme: kelime bazlı, ad eşleşmesi ile tetik eşleşmesi ayrı tutulur -----------
    proje_eslesme: list[tuple[str, bool]] = []   # (ad, ad_ile_eslesti)
    for ad in adlar:
        if ad in alan_adlari:
            continue
        ad_ile = tetik_eslesti(ad, kelimeler, EN_KISA_TETIK)
        tetikle = False
        if not ad_ile:
            proje_klasor = vault_projeler / ad
            ek = govde_tetikleri(proje_cekirdek(proje_klasor, "Proje"))
            tetikle = any(tetik_eslesti(t, kelimeler, EN_KISA_TETIK) for t in ek)
        if ad_ile or tetikle:
            proje_eslesme.append((ad, ad_ile))

    alan_eslesme: list[tuple[str, Path, bool]] = []
    for ad, sayfa in alanlar:
        ad_ile = tetik_eslesti(ad, kelimeler, EN_KISA_TETIK)
        tetikle = False
        if not ad_ile:
            tetikler = tetikleri_oku(sayfa) + govde_tetikleri(sayfa)
            tetikle = any(tetik_eslesti(t, kelimeler, EN_KISA_TETIK) for t in tetikler)
        if ad_ile or tetikle:
            alan_eslesme.append((ad, sayfa, ad_ile))

    # Bir ad TAM olarak eşleştiyse, yalnız o adın içindeki bir kelimeyle eşleşen diğerleri
    # düşer. "görsel üretim" cümlesi GÖRSEL ÜRETİM alanını tam adıyla uyandırıyor;
    # OPERASYON'un "üretim" tetiği aynı cümlede artık tetiklenmez.
    tam_adlar = [ad for ad, ad_ile in proje_eslesme if ad_ile] + \
                [ad for ad, _, ad_ile in alan_eslesme if ad_ile]
    if tam_adlar:
        tam_kelimeler: set[str] = set()
        for ad in tam_adlar:
            tam_kelimeler.update(kelime_kokleri(ad))

        def yalniz_ad_icinden_mi(ad: str, sayfa: Path | None) -> bool:
            """Bu kayıt yalnız tam eşleşen adın içinde geçen kelimelerle mi tetiklendi."""
            tetikler = list(kelime_kokleri(ad))
            if sayfa is not None:
                for t in tetikleri_oku(sayfa) + govde_tetikleri(sayfa):
                    tetikler += kelime_kokleri(t)
            vuran = [t for t in tetikler
                     if len(t) >= EN_KISA_TETIK and any(k.startswith(t) for k in kelimeler)]
            return bool(vuran) and all(t in tam_kelimeler for t in vuran)

        proje_eslesme = [(ad, a) for ad, a in proje_eslesme
                         if a or not yalniz_ad_icinden_mi(ad, proje_cekirdek(vault_projeler / ad, "Proje"))]
        alan_eslesme = [(ad, s, a) for ad, s, a in alan_eslesme
                        if a or not yalniz_ad_icinden_mi(ad, s)]

    # Tam ad eşleşmeleri öne alınır; iz dosyasında görülmüş olanlar düşer.
    proje_eslesme.sort(key=lambda p: (not p[1], p[0]))
    alan_eslesme.sort(key=lambda p: (not p[2], p[0]))
    eslesen_proje = [ad for ad, _ in proje_eslesme if ad not in gorulen][:EN_FAZLA_PROJE]
    eslesen_alan = [(ad, s) for ad, s, _ in alan_eslesme if f"alan:{ad}" not in gorulen]
    eslesen_alan = eslesen_alan[: max(0, EN_FAZLA - len(eslesen_proje))]

    # --- bütçe: toplam kanca_istem_karakter'i asla aşma --------------------------------
    toplam_tavan = sinir["kanca_istem_karakter"]
    eslesme_sayisi = len(eslesen_proje) + len(eslesen_alan)
    if eslesme_sayisi == 0:
        # Blok yok ama ipucu satırı her istemde çalışır; "bir kez" izine bağlı değildir.
        ipucu = tetik_ipucu(vault, kelimeler, set(), sinir["ipucu_en_fazla"])
        if ipucu:
            print(ipucu)
        return 0

    # İpucu satırı için pay ayrılır, kalan bütçe eşleşmeler arasında bölünür.
    kalan_butce = toplam_tavan - IPUCU_TAVAN - 120
    blok_butce = max(1000, kalan_butce // eslesme_sayisi)

    parcalar: list[str] = []
    verilen: list[str] = []
    basilan_yollar: set[str] = set()
    kirpildi = False
    kullanilan = 0

    def blok_ekle(metin: str, iz: str) -> None:
        nonlocal kullanilan, kirpildi
        if len(metin) > blok_butce:
            metin = kirp(metin, blok_butce, "[not: blok bütçeye sığmadığı için kırpıldı]")
            kirpildi = True
        if kullanilan + len(metin) > kalan_butce:
            kirpildi = True
            return
        parcalar.append(metin)
        verilen.append(iz)
        kullanilan += len(metin)

    for ad in eslesen_proje:
        konum = str(projeler_kok / ad) if projeler_kok is not None else "kod klasörü yok"
        proje_klasor = vault_projeler / ad
        durum_dosyasi = proje_cekirdek(proje_klasor, "Durum")
        kaynak_maddeler: list[str] = []
        if durum_dosyasi is not None:
            try:
                _, kaynak_maddeler = durum_kaynaklar_ayikla(durum_dosyasi.read_text(encoding="utf-8"))
            except OSError:
                kaynak_maddeler = []
        egitim = egitim_kaynaklari_blogu(
            tarifler_maddeleri(vault, proje_klasor / "TARİFLER"),
            kaynak_maddeler,
            youtube_alan_maddeleri(vault, f"PROJELER/{ad}"),
            min(EGITIM_TAVAN, sinir["kaynaklar_blok_karakter"]),
        )
        for yol in (proje_cekirdek(proje_klasor, "Kurallar"), durum_dosyasi):
            if yol is not None:
                basilan_yollar.add(str(yol.relative_to(vault)))
        blok_ekle(govde(
            f"[Proje: {ad}]", konum,
            proje_cekirdek(proje_klasor, "Kurallar"), durum_dosyasi,
            proje_cekirdek(proje_klasor, "Kararlar"),
            "Bu projenin özel kuralları yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            sinir, egitim,
        ), ad)

    for ad, sayfa in eslesen_alan:
        beyin_klasor = sayfa.parent
        alan_klasor = beyin_klasor.parent
        durum_dosyasi = alan_cekirdek(beyin_klasor, "Durum")
        kaynak_maddeler = []
        if durum_dosyasi is not None:
            try:
                _, kaynak_maddeler = durum_kaynaklar_ayikla(durum_dosyasi.read_text(encoding="utf-8"))
            except OSError:
                kaynak_maddeler = []
        egitim = egitim_kaynaklari_blogu(
            tarifler_maddeleri(vault, beyin_klasor / "TARİFLER"),
            kaynak_maddeler,
            youtube_alan_maddeleri(vault, str(alan_klasor.relative_to(vault))),
            min(EGITIM_TAVAN, sinir["kaynaklar_blok_karakter"]),
        )
        for yol in (alan_cekirdek(beyin_klasor, "Kurallar"), durum_dosyasi, sayfa):
            if yol is not None:
                basilan_yollar.add(str(yol.relative_to(vault)))
        blok_ekle(govde(
            f"[Alan: {ad}]", str(alan_klasor),
            alan_cekirdek(beyin_klasor, "Kurallar"), durum_dosyasi,
            alan_cekirdek(beyin_klasor, "Kararlar"),
            "Bu alanın özel kuralları yok; CLAUDE.md'deki ortak çalışma düzeni geçerli.",
            sinir, egitim,
        ), f"alan:{ad}")

    if not parcalar:
        return 0

    if kirpildi:
        parcalar.append("[not: yer kalmadığı için bir blok kırpıldı; ilgili dosyayı aç]")

    ipucu = tetik_ipucu(vault, kelimeler, basilan_yollar, sinir["ipucu_en_fazla"])
    if ipucu:
        parcalar.append(ipucu)

    if izlek is not None:
        try:
            izlek.write_text("\n".join(sorted(gorulen | set(verilen))).strip(), encoding="utf-8")
        except OSError:
            pass

    cikti = "\n\n".join(parcalar)
    if len(cikti) > toplam_tavan:
        cikti = cikti[: toplam_tavan - 60].rstrip() + "\n[not: çıktı tavanda kırpıldı]"
    print(cikti)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
