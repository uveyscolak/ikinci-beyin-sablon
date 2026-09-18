#!/usr/bin/env python3
"""Kök index.md'yi makine üretir: elle yazılmış notların klasöre göre gruplu kataloğu.

Katalog elle tutulunca eskiyordu; 273 dosyanın 207'si listede yoktu ve taşınmış
dosyalara giden ölü linkler kalıyordu. Artık her oturum sonunda yeniden üretilir.

Taranan kökler: İŞ, KİŞİSEL, PROJELER, EĞİTİMLER/KENDİ NOTLARIM, ASSETS.
Taranmayan: GÜNLÜK, BİLGİ, HAFIZA (makine ya da hafıza katmanı), GİZLİ (git'e girmez),
EĞİTİMLER/KAYNAKLAR (kendi index'i var), .claude (motor).

Elle yazılmış giriş ayrı bir kaynak dosyada durur: .claude/index-giris.md. Script'in
içinde sabit metin tutulmuyor; öyle olsaydı kişisel ifadeler motor koduyla birlikte
genel şablona kopyalanırdı. Giriş dosyası yoksa index yalnız listeden ibaret olur.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
GIRIS = VAULT / ".claude" / "index-giris.md"
KOKLER = ["İŞ", "KİŞİSEL", "PROJELER", "EĞİTİMLER/KENDİ NOTLARIM", "ASSETS"]
ACIKLAMA_TAVAN = 90
NOT = (
    "> Bu dosyayı makine üretir (`index-uret.py`, her oturum sonunda). "
    "Elle düzenleme; değişiklik bir sonraki üretimde silinir."
)

RE_FRONT = re.compile(r"(?s)\A---\n.*?\n(?:---|\.\.\.)\n")
RE_WIKI = re.compile(r"!?\[\[([^\]\n]+?)\]\]")
RE_MD_LINK = re.compile(r"\[([^\]\n]*?)\]\([^)\n]*\)")
RE_ISARET = re.compile(r"[*_`>]+")


def nfc(s: str) -> str:
    """macOS dosya adlarını NFD verir; karşılaştırma ve yazım öncesi NFC'ye çek."""
    return unicodedata.normalize("NFC", s)


def temizle(satir: str) -> str:
    """Bir satırı okunur düz metne indirger: link, kalın, kod ve madde işaretini atar."""
    s = RE_WIKI.sub(lambda m: m.group(1).split("|")[-1], satir)
    s = RE_MD_LINK.sub(lambda m: m.group(1), s)
    s = RE_ISARET.sub("", s)
    s = re.sub(r"^\s*[-+*]\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def aciklama(yol: Path) -> str:
    """Dosyanın ilk anlamlı satırından kısa açıklama.

    Başlık, tablo, ayraç ve kod bloğu atlanır; kalan ilk satırın ilk cümlesi alınır.
    Anlamlı satır yoksa açıklama boş kalır.
    """
    try:
        ham = yol.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    govde = RE_FRONT.sub("", ham)
    kod = False
    for satir in govde.splitlines():
        s = satir.strip()
        if s.startswith("```"):
            kod = not kod
            continue
        if kod or not s:
            continue
        if s.startswith("#") or s.startswith("|") or set(s) <= set("-=*_"):
            continue
        # Yapılacak kutusu ("- [ ] ...") şablonlarda ilk satır oluyor; açıklama değil.
        if re.match(r"^[-+*]\s*\[[ xX]\]", s):
            continue
        metin = temizle(s)
        if len(metin) < 3:
            continue
        # İlk cümle: nokta + boşluk sınırı. Yoksa satırın tamamı tavana kadar.
        m = re.search(r"(?<=[.!?])\s", metin)
        if m and m.start() <= ACIKLAMA_TAVAN:
            metin = metin[: m.start()]
        if len(metin) > ACIKLAMA_TAVAN:
            kesik = metin[:ACIKLAMA_TAVAN]
            bosluk = kesik.rfind(" ")
            metin = kesik[:bosluk] if bosluk > ACIKLAMA_TAVAN // 2 else kesik
        return metin.rstrip(" ,;:-—")
    return ""


def dosyalari_topla() -> list[Path]:
    """Taranan köklerin altındaki bütün .md dosyaları, kök sırasına sadık."""
    cikti: list[Path] = []
    for kok_adi in KOKLER:
        kok = VAULT / kok_adi
        if not kok.is_dir():
            continue
        # Önce klasör yoluna, sonra dosya adına göre: üst klasör kendi alt
        # klasörlerinden önce gelsin ("İŞ/X" listede "İŞ/X/alt"tan önce).
        def anahtar(x: Path) -> tuple[str, str]:
            rel = x.relative_to(VAULT)
            return (nfc(str(rel.parent)).casefold(), nfc(x.name).casefold())

        for p in sorted(kok.rglob("*.md"), key=anahtar):
            if any(parca.startswith(".") for parca in p.relative_to(VAULT).parts):
                continue
            cikti.append(p)
    return cikti


def uret() -> str:
    dosyalar = dosyalari_topla()

    # Aynı dosya adı birden çok klasörde varsa link yol yazılarak belirsizlik giderilir.
    sayac: dict[str, int] = {}
    for p in dosyalar:
        anahtar = nfc(p.stem).casefold()
        sayac[anahtar] = sayac.get(anahtar, 0) + 1

    gruplar: dict[str, list[str]] = {}
    sira: list[str] = []
    for p in dosyalar:
        rel = p.relative_to(VAULT)
        klasor = nfc(str(rel.parent))
        if klasor not in gruplar:
            gruplar[klasor] = []
            sira.append(klasor)
        ad = nfc(p.stem)
        if sayac[ad.casefold()] > 1:
            hedef = f"[[{nfc(str(rel.with_suffix('')))}|{ad}]]"
        else:
            hedef = f"[[{ad}]]"
        ac = aciklama(p)
        gruplar[klasor].append(f"- {hedef} — {ac}" if ac else f"- {hedef}")

    # Tek dosyalı klasörler kendi başlığını hak etmez: girdi bir üst klasörün grubuna katılır,
    # alt klasör adı açıklamanın başına yazılır. Üst düzey klasörler (İŞ, KİŞİSEL...) katlanmaz.
    degisti = True
    while degisti:
        degisti = False
        for klasor in list(sira):
            if len(gruplar.get(klasor, [])) != 1 or "/" not in klasor:
                continue
            ust = klasor.rsplit("/", 1)[0]
            alt_ad = klasor.rsplit("/", 1)[1]
            satir = gruplar[klasor][0]
            # Ayraç linkin bitiminden sonra aranır; dosya adının içinde de " — " olabilir.
            son = satir.find("]]") + 2
            baslik, kalan = satir[:son], satir[son:]
            ac = kalan[3:] if kalan.startswith(" — ") else ""
            satir = f"{baslik} — ({alt_ad}/) {ac}".rstrip()
            if ust not in gruplar:
                gruplar[ust] = []
                sira.insert(sira.index(klasor), ust)
            gruplar[ust].append(satir)
            del gruplar[klasor]
            sira.remove(klasor)
            degisti = True

    parca = [NOT, ""]
    if GIRIS.is_file():
        try:
            parca.append(GIRIS.read_text(encoding="utf-8").strip())
            parca.append("")
        except OSError:
            pass
    for klasor in sira:
        parca.append(f"## {klasor}")
        parca.append("")
        parca.extend(gruplar[klasor])
        parca.append("")
    parca.append(f"_{len(dosyalar)} not, {len(sira)} klasör._")
    return "\n".join(parca).rstrip() + "\n"


# --- tetik indeksi ---------------------------------------------------------------------
# `.claude/tetik-indeks.json`: tetik kökünden not yoluna eşleme. Her istemde çalışan kanca
# bunu yükleyip kullanıcının cümlesindeki kelimelerle eşleştirir ve tek satır ipucu basar.
# İçerik hiç yüklenmez; yalnız not adı ve yolu basılır.

TETIK_HEDEF = VAULT / ".claude" / "tetik-indeks.json"
TETIK_KOKLER = ["İŞ", "KİŞİSEL", "PROJELER"]
TETIK_EN_KISA = 4
# Bir nottan indekse giren `## ` başlık kelimesi sayısı; Kararlar dosyaları yüzlerce
# başlık taşıyor ve sınırsız alınırsa ipucu satırını tek başına dolduruyorlar.
ZAYIF_EN_FAZLA = 40
# Durak kelimeler: her notta geçer, ayırt etmez, indeksi gürültüye boğar. İstem tarafındaki
# durak listesiyle (proje-yonerge.py) kasıtlı olarak örtüşür; ikisi de aynı gürültüyü eler.
DURAK = {
    "ve", "ile", "için", "bir", "bu", "şu", "olan", "olarak", "daha", "gibi", "ama",
    "veya", "yani", "çok", "her", "kadar", "sonra", "önce", "göre", "ise", "ki",
    "notlarım", "içindekiler", "index", "readme", "md", "kaynaklar", "genel",
    "durum", "kararlar", "proje", "alan", "dosya", "dosyası", "notlar", "not",
    "genel", "ortak", "temel", "başlık", "bölüm", "liste", "tablo",
}
RE_GOVDE_TETIK = re.compile(r"(?mi)^\s*tetik\s*:\s*(.+)$")
RE_H2 = re.compile(r"(?m)^##\s+(.+?)\s*$")


def _sadelestir(metin: str) -> str:
    """Türkçe harfleri ASCII karşılığına indirir; eşleşme aksandan bağımsız olsun.

    Küçültme elle yapılır: Python'un lower()'ı I ve İ'yi Türkçede yanlış çeviriyor.
    """
    kucuk = unicodedata.normalize("NFC", metin).replace("İ", "i").replace("I", "ı").lower()
    d = {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"}
    return "".join(d.get(k, k) for k in kucuk)


def _kelimeler(metin: str) -> list[str]:
    """Bir metni tetik köklerine ayırır: kısa ve durak kelimeler atılır."""
    ham = re.split(r"[^0-9a-zA-ZçğıöşüÇĞİÖŞÜâîû]+", metin)
    cikti = []
    for kelime in ham:
        if not kelime:
            continue
        kucuk = unicodedata.normalize("NFC", kelime).replace("İ", "i").replace("I", "ı").lower()
        if kucuk in DURAK:
            continue
        kok = _sadelestir(kelime)
        if len(kok) < TETIK_EN_KISA or kok in DURAK:
            continue
        cikti.append(kok)
    return cikti


def _onblok_tetikleri(metin: str) -> list[str]:
    """Alan sayfalarının ön bloğundaki `tetik:` listesi (üç biçim de desteklenir)."""
    satirlar = metin.splitlines()
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
    return [p.strip().strip("\"'") for p in ham if p.strip()]


def _tetik_dosyalari() -> list[Path]:
    """İndekse giren notlar.

    İŞ, KİŞİSEL, PROJELER altındaki bütün .md dosyaları; EĞİTİMLER altından yalnız
    `00 İçindekiler.md`, `* — Notlarım.md` ve TEKİL VİDEOLAR altındaki notlar. Ders
    sayfaları ve RAW transkriptleri girmez: binlerce dosya indeksi kullanışsız yapar.
    HAFIZA, GÜNLÜK, BİLGİ ve GİZLİ hiç taranmaz.
    """
    cikti: list[Path] = []
    for kok_adi in TETIK_KOKLER:
        kok = VAULT / kok_adi
        if not kok.is_dir():
            continue
        for p in sorted(kok.rglob("*.md")):
            if any(parca.startswith(".") for parca in p.relative_to(VAULT).parts):
                continue
            cikti.append(p)
    egitimler = VAULT / "EĞİTİMLER"
    if egitimler.is_dir():
        for p in sorted(egitimler.rglob("*.md")):
            rel = p.relative_to(VAULT)
            if any(parca.startswith(".") for parca in rel.parts):
                continue
            if "RAW" in rel.parts:
                continue
            ad = nfc(p.name)
            if ad == "00 İçindekiler.md" or ad.endswith("— Notlarım.md") \
                    or "TEKİL VİDEOLAR" in rel.parts:
                cikti.append(p)
    return cikti


def tetik_indeksi() -> dict:
    """Not başına tetik kökleri, kaynak türüne göre üç ayrı liste:

    - "tetik": ön blok `tetik:` ve gövdedeki "Tetik:" satırından gelen kelimeler (en güçlü işaret).
    - "ad": dosya adından (ve genel adlı dosyalarda üst klasör adından) gelen kelimeler.
    - "baslik": `## ` başlıklarından gelen kelimeler (en zayıf işaret; bir Kararlar dosyasında
      yüzlerce başlık var, hepsi eşit sayılırsa dosya her cümleyle eşleşip ipucunu ele geçirir).

    Ağırlıklandırma tüketici tarafta (proje-yonerge.py) yapılır: tetik 3, ad 2, başlık 1 puan.
    """
    notlar = []
    for p in _tetik_dosyalari():
        rel = nfc(str(p.relative_to(VAULT)))
        ad = nfc(p.stem)
        try:
            ham = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            ham = ""
        tetik: list[str] = []
        for t in _onblok_tetikleri(ham):
            tetik += _kelimeler(t)
        eslesme = RE_GOVDE_TETIK.search(ham[:2000])
        if eslesme:
            for parca in eslesme.group(1).split(","):
                tetik += _kelimeler(parca)

        ad_kelimeleri: list[str] = list(_kelimeler(ad))
        # Genel adlı dosyalar (Durum, Kararlar, Proje, Alan) adlarıyla ayırt edilmez;
        # üst klasörlerinin adı onları ayırır.
        if ad in ("Durum", "Kararlar", "Proje", "Alan", "Kurallar", "PRD", "00 İçindekiler"):
            for parca in Path(rel).parent.parts:
                ad_kelimeleri += _kelimeler(parca)

        baslik: list[str] = []
        for m in RE_H2.finditer(ham):
            baslik += _kelimeler(m.group(1))

        tetik_kume = sorted(set(tetik))
        ad_kume = sorted(set(ad_kelimeleri) - set(tetik_kume))
        baslik_kume = sorted(set(baslik) - set(tetik_kume) - set(ad_kume))[:ZAYIF_EN_FAZLA]
        if not tetik_kume and not ad_kume and not baslik_kume:
            continue
        notlar.append({
            "yol": rel, "ad": ad,
            "tetik": tetik_kume, "adtetik": ad_kume, "baslik": baslik_kume,
            # Geri uyumluluk: eski tüketiciler "zayif" anahtarını bekleyebilir.
            "zayif": baslik_kume,
        })
    return {"uretildi": dt.datetime.now().isoformat(timespec="seconds"), "notlar": notlar}


def tetik_yaz() -> int:
    veri = tetik_indeksi()
    try:
        TETIK_HEDEF.parent.mkdir(parents=True, exist_ok=True)
        TETIK_HEDEF.write_text(json.dumps(veri, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"tetik-indeks.json yazılamadı: {e}", file=sys.stderr)
        return 1
    print(f"tetik-indeks.json üretildi: {len(veri['notlar'])} not")
    return 0


def main() -> int:
    if "--tetik" in sys.argv:
        return tetik_yaz()
    metin = uret()
    if "--goster" in sys.argv:
        print(metin, end="")
        return 0
    hedef = VAULT / "index.md"
    try:
        hedef.write_text(metin, encoding="utf-8")
    except OSError as e:
        print(f"index.md yazılamadı: {e}", file=sys.stderr)
        return 1
    print(f"index.md üretildi: {len(metin.splitlines())} satır")
    # Tetik indeksi aynı taramanın ürünü; kök index ile beraber tazelenir.
    return tetik_yaz()


if __name__ == "__main__":
    raise SystemExit(main())
