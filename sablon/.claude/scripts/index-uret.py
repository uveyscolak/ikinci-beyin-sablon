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


def main() -> int:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
