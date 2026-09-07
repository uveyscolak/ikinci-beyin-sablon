#!/usr/bin/env python3
"""Satın alınan eğitimler için giriş sayfaları üretir.

Her WİKİ klasörü olan eğitim için kökünde `00 İçindekiler.md` (modül, ders, tek satır özet,
transkript var mı) ve `EĞİTİMLER/KAYNAKLAR/index.md` (eğitim listesi) yazar. Özet, sayfadaki
"## Ne Öğretiyor" bölümünün ilk cümlesinden, yoksa sayfanın ilk paragrafından alınır; elle
yazılmış değildir. Klasör salt okunur olduğu için yazmadan önce izni açar, `--kilitle` ile
işin sonunda tamamını yeniden kilitler.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
KOK = VAULT / "EĞİTİMLER" / "KAYNAKLAR"
ICINDEKILER = "00 İçindekiler.md"

def _ayar() -> dict:
    try:
        veri = json.loads((VAULT / ".claude" / "beyin.json").read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


AYAR = _ayar()
CIKTI_KLASORU = {unicodedata.normalize("NFC", k): v for k, v in (AYAR.get("egitim_ciktilari") or {}).items()}   # eğitim klasörü -> işe dönük çıktı dosyasının vault'a göreli yolu
NOTLAR_DOSYASI = AYAR.get("notlar_dosyasi") or "NOTLARIM.md"  # kullanıcının kendi notu; kilitlenmez


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def dogal(s: str):
    m = re.match(r"\s*(\d+)", s)
    return (int(m.group(1)) if m else 10**6, nfc(s).casefold())


def wiki_klasorleri() -> list[Path]:
    return sorted(
        d for d in KOK.rglob("*")
        if d.is_dir() and nfc(d.name).casefold() == nfc("WİKİ").casefold()
    )


def temizle(s: str) -> str:
    s = re.sub(r"!\[\[[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"[*_`>#]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def ilk_cumle(s: str, tavan: int = 150) -> str:
    s = temizle(s)
    m = re.match(r"(.{20,}?[.!?])(\s|$)", s)
    if m:
        s = m.group(1)
    if len(s) > tavan:
        s = s[: tavan - 1].rstrip() + "…"
    return s


def ozet(metin: str) -> str:
    m = re.search(r"^## Ne Öğretiyor\s*\n+(.+?)$", metin, re.M)
    if m:
        return ilk_cumle(m.group(1))
    for satir in metin.splitlines():
        s = satir.strip()
        if not s or s.startswith(("#", "![[", "<", "---", "|", "```", "📝", "🧠")):
            continue
        if s.startswith(("- ", "* ")) and len(s) < 25:
            continue
        return ilk_cumle(s)
    return ""


def yaz(path: Path, icerik: str) -> None:
    for p in (path.parent, path):
        if p.exists():
            os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
    path.write_text(icerik, encoding="utf-8")


def egitim_uret(wiki: Path) -> dict:
    egitim = wiki.parent
    ad = egitim.relative_to(KOK).as_posix()
    sayfalar: list[tuple[str, Path]] = []
    altlar = sorted((d for d in wiki.iterdir() if d.is_dir()), key=lambda d: dogal(d.name))
    for alt in altlar:
        for p in sorted(alt.glob("*.md"), key=lambda p: dogal(p.name)):
            sayfalar.append((alt.name, p))
    for p in sorted(wiki.glob("*.md"), key=lambda p: dogal(p.name)):
        sayfalar.append(("", p))
    satirlar = [f"# {egitim.name} — İçindekiler", ""]
    transkriptli = 0
    moduller = [m for m in dict.fromkeys(m for m, _ in sayfalar)]
    govde: list[str] = []
    for modul in moduller:
        if modul:
            govde += ["", f"## {modul}", ""]
        else:
            govde += ["", "## Dersler", ""]
        govde += ["| Ders | Ne öğretiyor | Transkript |", "| --- | --- | --- |"]
        for m, p in sayfalar:
            if m != modul:
                continue
            metin = p.read_text(encoding="utf-8", errors="replace")
            tr = "var" if re.search(r"^## Transkript", metin, re.M) else "yok"
            transkriptli += tr == "var"
            yol = p.relative_to(VAULT).with_suffix("").as_posix()
            oz = ozet(metin).replace("|", "/")
            govde.append(f"| [[{yol}\\|{p.stem}]] | {oz} | {tr} |")
    ham_cikti = CIKTI_KLASORU.get(unicodedata.normalize("NFC", ad))
    cikti = ", ".join(ham_cikti) if isinstance(ham_cikti, list) else ham_cikti
    satirlar += [
        f"{len(moduller)} modül, {len(sayfalar)} ders, {transkriptli} transkript. Özetler ders sayfasındaki",
        "\"Ne Öğretiyor\" bölümünden veya ilk paragraftan otomatik alındı; ders için sayfayı, asıl söz için",
        "transkripti oku (`egitim` skill'i). Bu klasör salt okunurdur.",
    ]
    if cikti:
        satirlar.append(f"İşe dönük çıktı: {cikti}")
    notlar = egitim / NOTLAR_DOSYASI
    if not notlar.exists():
        yaz(notlar, f"# {notlar.stem}\n\nBu eğitime dair kendi notların. Ders sayfaları kilitli, bu dosya senindir.\n")
    satirlar.append(f"Kendi notların: [[{notlar.relative_to(VAULT).with_suffix('').as_posix()}\\|{notlar.stem}]] (yazılabilir).")
    satirlar += govde + ["", "---", "[[EĞİTİMLER/KAYNAKLAR/index\\|Eğitimler]]", ""]
    yaz(egitim / ICINDEKILER, "\n".join(satirlar))
    return {"ad": ad, "kok": egitim, "modul": len(moduller), "ders": len(sayfalar), "transkript": transkriptli, "cikti": cikti}


def index_uret(bilgiler: list[dict]) -> None:
    satirlar = [
        "# Eğitimler — Satın alınan kaynaklar",
        "",
        "Her eğitim kendi klasöründe, `RAW/` (video, transkript, belge) ve `WİKİ/` (her ders bir sayfa) ile",
        "durur; kökündeki `00 İçindekiler.md` dersleri tek satır özetle listeler. Klasör salt okunurdur.",
        "Soru sormak, ders anlattırmak ve damıtmak için `egitim` skill'i. Bu sayfa",
        "`python3 .claude/scripts/egitim-icindekiler.py` ile üretilir; elle düzenleme.",
        "",
        "| Eğitim | Modül | Ders | Transkript | İçindekiler | İşe dönük çıktı |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for b in bilgiler:
        yol = (b["kok"] / ICINDEKILER).relative_to(VAULT).with_suffix("").as_posix()
        cikti = ", ".join(f"`{c}`" for c in b["cikti"]) if isinstance(b["cikti"], list) else (f"`{b['cikti']}`" if b["cikti"] else "")
        satirlar.append(f"| {b['ad']} | {b['modul']} | {b['ders']} | {b['transkript']} | [[{yol}\\|İçindekiler]] | {cikti} |")
    satirlar += ["", "---", "[[index\\|Ana katalog]]", ""]
    yaz(KOK / "index.md", "\n".join(satirlar))


def kilitle() -> int:
    n = 0
    for p in KOK.rglob("*"):
        try:
            mode = os.stat(p, follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                continue
            if p.name == NOTLAR_DOSYASI:
                os.chmod(p, mode | stat.S_IWUSR)   # kullanıcının not dosyası açık kalır
                continue
            os.chmod(p, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            n += 1
        except OSError:
            pass
    os.chmod(KOK, os.stat(KOK).st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    return n


def main() -> int:
    if not KOK.is_dir():
        print("KAYNAKLAR yok", file=sys.stderr)
        return 1
    if "--sadece-kilitle" not in sys.argv:
        bilgiler = [egitim_uret(w) for w in wiki_klasorleri()]
        index_uret(bilgiler)
        for b in bilgiler:
            print(f"{b['ad']}: {b['modul']} modül, {b['ders']} ders, {b['transkript']} transkript")
    if "--kilitle" in sys.argv or "--sadece-kilitle" in sys.argv:
        print("kilitlendi:", kilitle(), "öğe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
