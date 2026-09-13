#!/usr/bin/env python3
"""Stop kancası: son asistan cevabındaki dosya linklerini denetler.

Markdown dosya linkinde boşluk, % ya da Türkçe harf varsa cevabı blokla,
düzeltmeyi iste. http(s)/mailto/obsidian/# hedefleri ve bozuk girdi/hata
durumlarında sessizce çık (asla cevabı kilitleme).
"""
import json
import re
import sys

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+(?:\s[^)]*)?)\)")
TR_HARF_RE = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
MUAF_ON_EKLER = ("http://", "https://", "mailto:", "obsidian://", "#")


def son_asistan_metni(veri):
    metin = veri.get("last_assistant_message")
    if isinstance(metin, str) and metin.strip():
        return metin

    transcript_path = veri.get("transcript_path")
    if not transcript_path:
        return None

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            satirlar = f.readlines()
    except OSError:
        return None

    for satir in reversed(satirlar):
        satir = satir.strip()
        if not satir:
            continue
        try:
            kayit = json.loads(satir)
        except json.JSONDecodeError:
            continue

        if kayit.get("type") != "assistant":
            continue

        mesaj = kayit.get("message")
        icerik = None
        if isinstance(mesaj, dict):
            icerik = mesaj.get("content")
        if icerik is None:
            icerik = kayit.get("content")

        parcalar = []
        if isinstance(icerik, list):
            for blok in icerik:
                if isinstance(blok, dict) and blok.get("type") == "text":
                    metin_blok = blok.get("text")
                    if isinstance(metin_blok, str):
                        parcalar.append(metin_blok)
        elif isinstance(icerik, str):
            parcalar.append(icerik)

        if parcalar:
            return "\n".join(parcalar)

    return None


def ihlalli_hedefler(metin):
    ihlaller = []
    for eslesme in LINK_RE.finditer(metin):
        hedef = eslesme.group(1)
        if hedef.startswith(MUAF_ON_EKLER):
            continue
        if " " in hedef or "%" in hedef or TR_HARF_RE.search(hedef):
            ihlaller.append(hedef)
    return ihlaller


def main():
    try:
        veri = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    try:
        if veri.get("stop_hook_active") is True:
            sys.exit(0)

        metin = son_asistan_metni(veri)
        if not metin:
            sys.exit(0)

        ihlaller = ihlalli_hedefler(metin)
        if not ihlaller:
            sys.exit(0)

        hedef_listesi = ", ".join(ihlaller)
        sonuc = {
            "decision": "block",
            "reason": (
                "Dosya linki kuralı (anayasa §2): boşluk ve Türkçe harf yerine "
                "yıldız kullan, desenin tek dosya eşlediğini doğrula. "
                f"Düzeltilecek linkler: {hedef_listesi}. "
                "Aynı cevabı yalnız linkleri düzelterek yeniden ver."
            ),
        }
        print(json.dumps(sonuc, ensure_ascii=False))
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
