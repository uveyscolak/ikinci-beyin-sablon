#!/usr/bin/env python3
"""Her gece çalışan bakım: sayar, tarar, indeks üretir, sonra tek bir model çağrısı yapar.

Sıra:
  1. saglik.py --yaz --sayim   : kırık link, yapı, madde ve boyut sayımı, bağlanmamış dosya
  2. index-uret.py             : kök index.md ve .claude/tetik-indeks.json
  3. token-rapor.py            : HAFIZA/Token Raporu.md
  4. compile.py (aday modu)    : günlükten kural adayı çıkarır, Bekleyenler'e yazar

İlk üç adım model çağırmaz. Dördüncü adım Sonnet çağırır ve yalnız bugün henüz
çalışmadıysa yapılır; haftalık abonelik sınırına takılırsa atlanır, atlandığı görünür
kaydedilir ve bir sonraki açılışta tek satırla söylenir.

Bir adım düşerse diğerleri devam eder. Sonuç .state/gece-bakim.json ve .state/gece-bakim.log
dosyalarına yazılır; sonuç "basarisiz" ise açılış kancası tek satır basar.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = VAULT / ".claude" / "scripts"
STATE = SCRIPTS / ".state"
DURUM_DOSYASI = STATE / "gece-bakim.json"
LOG_DOSYASI = STATE / "gece-bakim.log"
LOG_EN_FAZLA_SATIR = 400

# Her adımın kendi zaman sınırı; bir adım takılırsa gece bakımı bütün gece asılı kalmasın.
ADIMLAR = [
    ("saglik", [sys.executable, str(SCRIPTS / "saglik.py"), "--yaz", "--sayim"], 900),
    ("index", [sys.executable, str(SCRIPTS / "index-uret.py")], 600),
    ("token", [sys.executable, str(SCRIPTS / "token-rapor.py")], 600),
]
COMPILE_ZAMAN_SINIRI = 1800


def simdi() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def log_yaz(satir: str) -> None:
    """Log dosyasına tek satır ekler ve dosyayı son LOG_EN_FAZLA_SATIR satıra indirir."""
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        eski = LOG_DOSYASI.read_text(encoding="utf-8").splitlines() if LOG_DOSYASI.exists() else []
        eski.append(f"[{simdi()}] {satir}")
        LOG_DOSYASI.write_text("\n".join(eski[-LOG_EN_FAZLA_SATIR:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def calistir(ad: str, komut: list[str], zaman_siniri: int) -> dict:
    """Bir adımı çalıştırır ve sonucunu sözlük olarak döner; hata fırlatmaz."""
    ortam = os.environ.copy()
    # BEYIN_INVOKED_BY kancaların kendi kendini tetiklemesini engelliyor; compile.py bu
    # değişken doluysa hiç çalışmıyor, bu yüzden alt süreçlere geçirilmez.
    ortam.pop("BEYIN_INVOKED_BY", None)
    try:
        r = subprocess.run(komut, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=zaman_siniri, cwd=str(VAULT), env=ortam)
    except subprocess.TimeoutExpired:
        log_yaz(f"{ad}: zaman sınırı ({zaman_siniri} sn) aşıldı")
        return {"sonuc": "zaman_asimi", "ayrinti": f"{zaman_siniri} sn"}
    except OSError as e:
        log_yaz(f"{ad}: çalıştırılamadı: {e}")
        return {"sonuc": "calismadi", "ayrinti": str(e)[:200]}
    cikti = (r.stdout or "").strip().splitlines()
    hata = (r.stderr or "").strip()[-400:]
    if r.returncode == 0:
        log_yaz(f"{ad}: tamam — {cikti[-1] if cikti else 'çıktı yok'}")
        return {"sonuc": "tamam", "ayrinti": cikti[-1] if cikti else ""}
    log_yaz(f"{ad}: düştü (kod {r.returncode}) — {hata}")
    return {"sonuc": "dustu", "kod": r.returncode, "ayrinti": hata}


def compile_bugun_calisti_mi() -> bool:
    """compile-state.json'daki son koşu bugüne ait mi; aynı gece iki kez çağrı yapılmasın."""
    try:
        durum = json.loads((STATE / "compile-state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    son = durum.get("last_run")
    if not isinstance(son, str):
        return False
    return son[:10] == dt.date.today().isoformat()


def compile_hatasi_oku() -> str:
    """Derleyicinin son hatasını .state/compile-hatalar.json'dan okur (boşsa boş döner)."""
    try:
        kayitlar = json.loads((STATE / "compile-hatalar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(kayitlar, list) or not kayitlar:
        return ""
    son = kayitlar[-1]
    if not isinstance(son, dict):
        return ""
    return f"{son.get('tur', '?')}: {str(son.get('ayrinti', ''))[:200]}"


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    baslangic = simdi()
    log_yaz("gece bakımı başladı")
    adimlar: dict = {}

    for ad, komut, sinir in ADIMLAR:
        adimlar[ad] = calistir(ad, komut, sinir)

    # Model çağrısı en sona bırakılır: ilk üç adım onsuz da tamamlanmış olur.
    if "--derleme-yok" in sys.argv:
        adimlar["derleme"] = {"sonuc": "atlandi", "ayrinti": "--derleme-yok"}
    elif compile_bugun_calisti_mi():
        adimlar["derleme"] = {"sonuc": "atlandi", "ayrinti": "bugün zaten çalıştı"}
        log_yaz("derleme: bugün zaten çalıştı, atlandı")
    else:
        sonuc = calistir("derleme", [sys.executable, str(SCRIPTS / "compile.py")],
                         COMPILE_ZAMAN_SINIRI)
        # compile.py hatayı kendi içinde yutup 0 dönüyor; gerçek sonuç hata kaydındadır.
        hata = compile_hatasi_oku()
        if sonuc["sonuc"] == "tamam" and hata:
            try:
                kayitlar = json.loads((STATE / "compile-hatalar.json").read_text(encoding="utf-8"))
                son_zaman = kayitlar[-1].get("zaman", "") if kayitlar else ""
            except (OSError, ValueError, AttributeError, IndexError):
                son_zaman = ""
            if son_zaman >= baslangic:
                sonuc = {"sonuc": "dustu", "ayrinti": hata}
                log_yaz(f"derleme: model çağrısı düştü — {hata}")
        adimlar["derleme"] = sonuc

    basarisiz = [ad for ad, d in adimlar.items()
                 if d.get("sonuc") not in ("tamam", "atlandi")]
    durum = {
        "baslangic": baslangic,
        "bitis": simdi(),
        "sonuc": "basarisiz" if basarisiz else "tamam",
        "adimlar": adimlar,
    }
    try:
        gecici = STATE / f".gece-bakim.{os.getpid()}.tmp"
        gecici.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(gecici, DURUM_DOSYASI)
    except OSError:
        pass
    log_yaz(f"gece bakımı bitti: {durum['sonuc']}" + (f" (düşen: {', '.join(basarisiz)})" if basarisiz else ""))
    print(f"gece bakımı: {durum['sonuc']}")
    for ad, d in adimlar.items():
        print(f"  {ad}: {d['sonuc']} {d.get('ayrinti', '')}".rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
