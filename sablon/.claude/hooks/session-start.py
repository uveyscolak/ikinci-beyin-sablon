#!/usr/bin/env python3
"""Oturum başı bağlamını kurar ve Claude Code kancasının beklediği JSON'u basar.

Kurallar, Açık Konular ve Son Oturum artık CLAUDE.md §12'deki @ bağlarıyla tam ve
kırpılmadan yüklenir; bu kanca onları basmaz. Kanca yalnız o an üretilen bilgiyi taşır:
sağlık kontrolü, boyut bekçisi, push bekleyen depolar, kural ve çelişki adayları,
bilgi indeksinin son satırları, bugünün günlük kuyruğu.

Sıra ve ilke: en yeni bilgi önce gelir, kırpma her zaman eskiyi düşürür.
- Beyin sağlığı ve boyut bekçisi: en önde.
- Push/commit durumu.
- HAFIZA/Kural Adayları.md: varsa, onay bekleyenler.
- HAFIZA/Çelişki Adayları.md: varsa, derleyicinin bulduğu eski/yeni bilgi çatışmaları.
- BİLGİ/index.md: tablo, yeniden eskiye.
- GÜNLÜK/<bugün>.md: kuyruk.
Bölüm tavanları aşıldığında not düşülür; toplam tavan (9.000) aşılırsa önce indeks
satır sayısı, sonra günlük kuyruğu, sonra düz kesme uygulanır.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

TOPLAM_TAVAN = 9_000
TAVAN = {
    "adaylar": 2_000,
    "celiskiler": 2_000,
    "indeks": 14_000,
    "gunluk": 3_000,
}
# İndeksin tamamı açılışın en pahalı parçasıydı (43 satır, ~12 KB) ve nadiren okunuyordu.
# Yalnız en yeni satırlar girer; gerisini `hatirla` skill'i dosyadan arar.
INDEKS_SATIR = 8

# Boyut bekçisinin izlediği üç dosya: CLAUDE.md §12'de tam yüklenenlerle aynı üçlü.
BOYUT_SINIRLARI = {
    "HAFIZA/Kurallar.md": 8_000,
    "HAFIZA/Açık Konular.md": 6_000,
    "HAFIZA/Son Oturum.md": 5_000,
}


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


def kural_adaylari(hafiza: Path) -> str:
    metin = oku(hafiza / "Kural Adayları.md")
    maddeler = [s for s in metin.splitlines() if s.lstrip().startswith("- ")]
    return "\n".join(maddeler)


def celiski_adaylari(hafiza: Path) -> str:
    metin = oku(hafiza / "Çelişki Adayları.md")
    maddeler = [s for s in metin.splitlines() if s.lstrip().startswith("- ")]
    return "\n".join(maddeler)


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


def boyut_bekcisi(vault: Path) -> str:
    """CLAUDE.md §12'de tam yüklenen üç dosyanın boyutunu izler; sınır aşılırsa uyarır."""
    parca = []
    for ad, sinir in BOYUT_SINIRLARI.items():
        n = len(oku(vault / ad))
        if n > sinir:
            parca.append(f"- {ad}: {n:,} karakter (sınır {sinir:,}) — sadeleştirme zamanı, kullanıcıya teklif et.".replace(",", "."))
    if not parca:
        return ""
    return "\n".join(parca)


def push_bekleyen(vault: Path) -> str:
    """Kod depolarında push bekleyen commit ve commit bekleyen değişiklik taraması.

    Commit Claude'a, push kullanıcıya ait (anayasa §8). Kullanıcı push'u unutuyor;
    hatırlatma bu yüzden mekanizmaya bağlı, Claude'un aklında tutmasına değil.
    """
    kok = ayar(vault).get("projeler")
    if not kok:
        return ""  # kod klasörü beyin.json'da tanımlı değilse tarama yapılmaz
    kokp = Path(str(kok))
    if not kokp.is_dir():
        return ""

    def git(depo: Path, *arg: str) -> str:
        try:
            r = subprocess.run(("git", "-C", str(depo)) + arg, capture_output=True,
                               text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    pushlar: list[str] = []
    kirliler: list[str] = []
    for depo in sorted(p for p in kokp.iterdir() if (p / ".git").is_dir()):
        if not git(depo, "remote"):
            continue  # uzak deposu yoksa push diye bir şey yok
        bekleyen = git(depo, "log", "--branches", "--not", "--remotes", "--oneline")
        if bekleyen:
            n = len(bekleyen.splitlines())
            ilk = bekleyen.splitlines()[0]
            pushlar.append(f"  - {depo.name}: {n} commit bekliyor (en yenisi: {ilk})")
        kirli = git(depo, "status", "--porcelain")
        if kirli:
            kirliler.append(f"  - {depo.name}: {len(kirli.splitlines())} dosya")

    if not pushlar and not kirliler:
        return ""
    parca = []
    if pushlar:
        parca.append("Push bekleyen depolar (push kullanıcıya ait, sen atma):")
        parca.extend(pushlar)
        parca.append("Kullanıcıya hatırlat: değişikliklerin çalıştığına kanaat getirdiyse"
                     " beraber push edilir. Her commit değil, çalışan sürüm push edilir.")
    if kirliler:
        parca.append("Commit bekleyen değişiklik (commit sana ait, sormadan yap):")
        parca.extend(kirliler)
    return "\n".join(parca)


def kur(vault: Path) -> str:
    hafiza = vault / "HAFIZA"
    kullanici = str(ayar(vault).get("kullanici") or "Kullanıcı")
    bolumler: list[tuple[str, str]] = []
    s = saglik(vault)
    if s:
        bolumler.append(("[Beyin sağlığı — otomatik kontrol]", s))
    b = boyut_bekcisi(vault)
    if b:
        bolumler.append(("[Boyut bekçisi]", b))
    p = push_bekleyen(vault)
    if p:
        bolumler.append(("[Kod depoları — push ve commit durumu]", p))
    aday = kirp(kural_adaylari(hafiza), TAVAN["adaylar"], "kural adayları")
    if aday:
        bolumler.append((f"[Hafıza: Kural Adayları — derleyici çıkardı, {kullanici} onaylarsa Kurallar'a geçer]", aday))
    celiski = kirp(celiski_adaylari(hafiza), TAVAN["celiskiler"], "çelişki adayları")
    if celiski:
        bolumler.append((f"[Hafıza: Çelişki Adayları — derleyici buldu, makaledeki eski bilgi ile günlükteki yeni bilgi çatışıyor; {kullanici} karar verir]", celiski))

    baslik, satirlar = indeks_parcala(vault)
    gun = kirp(gunluk(vault), TAVAN["gunluk"], "günlük")

    kapanis = (
        "[Hafıza] Kurallar, Açık Konular ve Son Oturum bu anayasanın parçası olarak zaten tam yüklü (CLAUDE.md §12); "
        "üstlerine sormadan güncellemek senin sorumluluğun."
    )

    def birlestir(indeks_satir: int, gun_metni: str) -> str:
        parca = []
        for etiket, metin in bolumler:
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
    metin = birlestir(n, gun)
    while len(metin) > TOPLAM_TAVAN and n > 0:
        n -= 5 if n > 5 else 1
        metin = birlestir(n, gun)
    if len(metin) > TOPLAM_TAVAN:
        metin = birlestir(n, "")
    if len(metin) > TOPLAM_TAVAN:
        not_ = "\n[not: kanca çıktısı 9.000 karakter tavanında kesildi; beyin doktor çalıştır]"
        metin = metin[: TOPLAM_TAVAN - len(not_) - 40] + not_
    # Son satırın kendi uzunluğu toplam hesaba katılır; yaklaşık değer yeterli (kapanış tek kez eklenir).
    kuyruk_sablon = "\n[Kanca çıktısı: {} karakter; tavan 9.000]"
    tahmini_toplam = len(metin) + len(kuyruk_sablon.format("00.000"))
    metin = metin + kuyruk_sablon.format(f"{tahmini_toplam:,}".replace(",", "."))
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
