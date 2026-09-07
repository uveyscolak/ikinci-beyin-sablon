#!/usr/bin/env python3
"""Oturum başı bağlamını kurar ve Claude Code kancasının beklediği JSON'u basar.

Sıra ve ilke: en yeni bilgi önce gelir, kırpma her zaman eskiyi düşürür.
- HAFIZA/Son Oturum.md: önce "### Nerede kalındı" bölümü, sonra gerisi.
- HAFIZA/Açık Konular.md: açık başlıklar ve durum satırları.
- HAFIZA/Kurallar.md: tamamı.
- HAFIZA/Kural Adayları.md: varsa, onay bekleyenler.
- HAFIZA/Çelişki Adayları.md: varsa, derleyicinin bulduğu eski/yeni bilgi çatışmaları.
- HAFIZA/Günce.md: son giriş.
- BİLGİ/index.md: tablo, yeniden eskiye.
- GÜNLÜK/<bugün>.md: kuyruk.
Bölüm tavanları aşıldığında not düşülür; toplam tavan aşılırsa önce indeksin eski
satırları, sonra günlük kuyruğu, sonra günce kırpılır.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

TOPLAM_TAVAN = 40_000
TAVAN = {
    "son": 8_000,
    # Kurallar oturum davranışını belirler; tavana dayanıp sonu sessizce kesilirse
    # en yeni kurallar düşer. 8.000 dolmak üzereydi, 16.000'e çıkarıldı.
    "kurallar": 16_000,
    "konular": 3_000,
    "adaylar": 2_000,
    "celiskiler": 2_000,
    "gunce": 1_500,
    "indeks": 14_000,
    "gunluk": 3_000,
}
# İndeksin tamamı açılışın en pahalı parçasıydı (43 satır, ~12 KB) ve nadiren okunuyordu.
# Yalnız en yeni satırlar girer; gerisini `hatirla` skill'i dosyadan arar.
INDEKS_SATIR = 8


def oku(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def kirp(metin: str, tavan: int, ad: str) -> str:
    metin = metin.strip()
    if len(metin) <= tavan:
        return metin
    not_ = f"[not: {ad} {tavan:,} karakterde kırpıldı, tamamı için dosyayı aç]".replace(",", ".")
    return metin[: tavan - len(not_) - 1].rstrip() + "\n" + not_


def son_oturum(hafiza: Path) -> str:
    metin = oku(hafiza / "Son Oturum.md")
    if not metin:
        return ""
    satirlar = metin.splitlines()
    basla = next((i for i, s in enumerate(satirlar) if s.startswith("## Oturum:")), None)
    if basla is None:
        return ""
    bitir = next((i for i in range(basla + 1, len(satirlar)) if satirlar[i].startswith("## Önceki")), len(satirlar))
    blok = satirlar[basla:bitir]
    # "### Nerede kalındı" bölümünü öne al
    n0 = next((i for i, s in enumerate(blok) if s.strip().lower().startswith("### nerede kalındı")), None)
    if n0 is not None:
        n1 = next((i for i in range(n0 + 1, len(blok)) if blok[i].startswith("### ")), len(blok))
        nerede = blok[n0:n1]
        geri = blok[:n0] + blok[n1:]
        blok = [geri[0]] + nerede + [""] + geri[1:]
    return "\n".join(blok)


def acik_konular(hafiza: Path) -> str:
    metin = oku(hafiza / "Açık Konular.md")
    if not metin:
        return ""
    icinde = False
    cikti = []
    for s in metin.splitlines():
        if s.startswith("## Açık"):
            icinde = True
            continue
        if s.startswith("## Kapanmış"):
            break
        if icinde and (s.startswith("### ") or s.startswith("**Durum:**")):
            cikti.append(s)
    return "\n".join(cikti[:60])


def kurallar(hafiza: Path) -> str:
    return oku(hafiza / "Kurallar.md")


def kural_adaylari(hafiza: Path) -> str:
    metin = oku(hafiza / "Kural Adayları.md")
    maddeler = [s for s in metin.splitlines() if s.lstrip().startswith("- ")]
    return "\n".join(maddeler)


def celiski_adaylari(hafiza: Path) -> str:
    metin = oku(hafiza / "Çelişki Adayları.md")
    maddeler = [s for s in metin.splitlines() if s.lstrip().startswith("- ")]
    return "\n".join(maddeler)


def gunce(hafiza: Path) -> str:
    metin = oku(hafiza / "Günce.md")
    satirlar = metin.splitlines()
    basla = None
    for i, s in enumerate(satirlar):
        if s.startswith("## "):
            basla = i
    if basla is None:
        return ""
    return "\n".join(satirlar[basla : basla + 12])


def indeks_parcala(vault: Path) -> tuple[str, list[str]]:
    metin = oku(vault / "BİLGİ" / "index.md")
    if not metin:
        return "", []
    satirlar = metin.splitlines()
    baslik, satirlar_tablo = [], []
    ayrac_gecti = False
    for s in satirlar:
        if not ayrac_gecti:
            baslik.append(s)
            if re.match(r"^\|\s*-{3,}", s):
                ayrac_gecti = True
            continue
        if s.startswith("| ["):
            satirlar_tablo.append(s)
    satirlar_tablo.reverse()  # yeniden eskiye
    return "\n".join(baslik), satirlar_tablo


def gunluk(vault: Path) -> str:
    bugun = dt.date.today()
    for gun in (bugun, bugun - dt.timedelta(days=1)):
        p = vault / "GÜNLÜK" / f"{gun.isoformat()}.md"
        if p.exists():
            return "\n".join(oku(p).splitlines()[-25:])
    return ""


def ayar(vault: Path) -> dict:
    try:
        v = json.loads((vault / ".claude" / "beyin.json").read_text(encoding="utf-8"))
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def saglik(vault: Path) -> str:
    """saglik.py'nin yazdığı sonuç: sorun varsa veya haftalık bakım zamanıysa metin döner."""
    try:
        r = json.loads((vault / ".claude" / "scripts" / ".state" / "saglik.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(r, dict):
        return ""
    parca = []
    for s in r.get("sorunlar") or []:
        parca.append(f"- SORUN: {s}")
    for b in r.get("bilgi") or []:
        parca.append(f"- not: {b}")
    if r.get("haftalik"):
        son = r.get("haftalik_son") or "hiç"
        parca.append(
            f"- HAFTALIK BAKIM ZAMANI (son bakım: {son}). Kullanıcıya bugün bakım yapmayı teklif et; onay gelince"
            " `haftalik` skill'indeki adımları uygula ve bitince `python3 .claude/scripts/saglik.py --bakim-yapildi` çalıştır."
        )
    if not parca:
        return ""
    parca.append("Sorunları kullanıcıya bir cümleyle söyle, düzeltmeyi teklif et; kullanıcının bir şeyi hatırlaması gerekmez.")
    return "\n".join(parca)


def kur(vault: Path) -> str:
    hafiza = vault / "HAFIZA"
    kullanici = str(ayar(vault).get("kullanici") or "Kullanıcı")
    bolumler: list[tuple[str, str]] = []
    s = saglik(vault)
    if s:
        bolumler.append(("[Beyin sağlığı — otomatik kontrol]", s))
    son = kirp(son_oturum(hafiza), TAVAN["son"], "son oturum")
    if son:
        bolumler.append(("[Hafıza: Son Oturum]", son))
    konular = kirp(acik_konular(hafiza), TAVAN["konular"], "açık konular")
    if konular:
        bolumler.append(("[Hafıza: Açık Konular]", konular))
    kural = kirp(kurallar(hafiza), TAVAN["kurallar"], "kurallar")
    if kural:
        bolumler.append(("[Hafıza: Kurallar]", kural))
    aday = kirp(kural_adaylari(hafiza), TAVAN["adaylar"], "kural adayları")
    if aday:
        bolumler.append((f"[Hafıza: Kural Adayları — derleyici çıkardı, {kullanici} onaylarsa Kurallar'a geçer]", aday))
    celiski = kirp(celiski_adaylari(hafiza), TAVAN["celiskiler"], "çelişki adayları")
    if celiski:
        bolumler.append((f"[Hafıza: Çelişki Adayları — derleyici buldu, makaledeki eski bilgi ile günlükteki yeni bilgi çatışıyor; {kullanici} karar verir]", celiski))
    g = kirp(gunce(hafiza), TAVAN["gunce"], "günce")
    if g:
        bolumler.append(("[Hafıza: Günce, son giriş]", g))

    baslik, satirlar = indeks_parcala(vault)
    gun = kirp(gunluk(vault), TAVAN["gunluk"], "günlük")

    kapanis = (
        f"[Hafıza] Süreklilik senin sorumluluğun. Hafıza klasörü: {vault}/HAFIZA\n"
        "Başka bir klasörde çalışıyor olsan bile hafıza dosyaları HER ZAMAN bu mutlak yoldadır.\n"
        "Son Oturum'u oturum sonunda makine yazar; sen daha iyisini biliyorsan üstüne yaz.\n"
        "Açık Konular, Kurallar ve Günce senindir: sormadan güncelle. Hafıza protokolü zorunludur."
    )

    def birlestir(indeks_satir: int, gun_metni: str, gunce_dahil: bool) -> str:
        parca = []
        for etiket, metin in bolumler:
            if not gunce_dahil and etiket.startswith("[Hafıza: Günce"):
                continue
            parca.append(f"{etiket}\n{metin}\n")
        if baslik and indeks_satir > 0:
            secilen = satirlar[:indeks_satir]
            not_ = (
                f"\n[tam indeks: BİLGİ/index.md ({len(satirlar)} makale), "
                "`hatirla` skill'i oradan arar]"
            )
            parca.append("[Bilgi Tabanı: İndeks — en yeni " + str(len(secilen)) + " makale]\n"
                         + baslik + "\n" + "\n".join(secilen) + not_ + "\n")
        if gun_metni:
            parca.append("[Bugünün Logu — kuyruk]\n" + gun_metni + "\n")
        parca.append(kapanis)
        return "\n".join(parca)

    # İndeksten yalnız en yeni satırlar girer; tavan ikinci bir emniyet.
    n = min(INDEKS_SATIR, len(satirlar))
    while n > 0 and len("\n".join(satirlar[:n])) > TAVAN["indeks"]:
        n -= 1
    metin = birlestir(n, gun, True)
    while len(metin) > TOPLAM_TAVAN and n > 0:
        n -= 5 if n > 5 else 1
        metin = birlestir(n, gun, True)
    if len(metin) > TOPLAM_TAVAN:
        metin = birlestir(n, "", True)
    if len(metin) > TOPLAM_TAVAN:
        metin = birlestir(n, "", False)
    if len(metin) > TOPLAM_TAVAN:
        metin = metin[: TOPLAM_TAVAN - 80] + "\n[not: bağlam 40.000 karakter tavanında kesildi, beyin doktor çalıştır]"
    return metin


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    vault = Path(sys.argv[1])
    if not vault.is_dir():
        return 0
    metin = kur(vault)
    if "--plain" in sys.argv:
        print(metin)
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": metin}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
