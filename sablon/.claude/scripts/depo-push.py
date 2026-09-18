#!/usr/bin/env python3
"""Kod depolarında derleme/test geçerse push eder, geçmezse etmez.

Push işi kullanıcıdan makineye devredildi: anlamlı değişimlerde commit ve push'u sistem
kendi yapar. Şart: kod depolarında push yalnız derleme ve testler geçiyorsa yapılır
(commit hâlâ Claude'un, kullanıcının elle push etmesi gerekmiyor).

Depo listesi saglik.py ile aynı kaynaktan gelir: beyin.json'daki "projeler" kökü
altında `.git` klasörü olan her klasör (tek doğru kaynak, iki yerde ayrı liste yok).

Her depo için sıra:
  1. push bekleyen commit var mı (`git rev-list --count @{u}..HEAD`); uzak dal yoksa atla
  2. çalışma ağacı kirliyse uyar (push yine denenir, commit bu script'in işi değil)
  3. doğrulama: depo kökünde hangi araç varsa onunla derleme/test
  4. doğrulama yoksa ya da geçtiyse push; doğrulama düştüyse push YOK

Sonuç depo başına .state/push-durum.json içine yazılır. `--kuru` hiçbir şey
push etmeden ne yapılacağını yazar.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
STATE = VAULT / ".claude" / "scripts" / ".state"
DURUM_DOSYASI = STATE / "push-durum.json"

DOGRULAMA_ZAMAN_SINIRI = 300
PUSH_ZAMAN_SINIRI = 120


def simdi() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _json_oku(path: Path) -> dict:
    try:
        veri = json.loads(path.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def projeler_koku() -> Path | None:
    """beyin.json'daki `projeler` alanı: saglik.py'nin push_bekleyen'i de aynı alanı okur."""
    ayar = _json_oku(VAULT / ".claude" / "beyin.json")
    kok = ayar.get("projeler")
    if not kok:
        return None
    p = Path(str(kok))
    return p if p.is_dir() else None


def depolar(kok: Path) -> list[Path]:
    try:
        return sorted(p for p in kok.iterdir() if (p / ".git").is_dir())
    except OSError:
        return []


def _calistir(komut: list[str], cwd: Path, zaman_siniri: int) -> tuple[int, str, str]:
    """(returncode, stdout, stderr) döner; zaman aşımı ve OSError -1 koduyla yakalanır."""
    try:
        r = subprocess.run(komut, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=zaman_siniri, cwd=str(cwd))
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"zaman sınırı aşıldı ({zaman_siniri} sn)"
    except OSError as e:
        return -1, "", str(e)


def git(depo: Path, *arg: str, zaman_siniri: int = 15) -> tuple[int, str]:
    kod, out, err = _calistir(["git", "-C", str(depo)] + list(arg), depo, zaman_siniri)
    return kod, (out.strip() if kod == 0 else (out + err).strip())


def bekleyen_commit(depo: Path) -> tuple[int | None, str]:
    """(sayı, açıklama). Uzak takip dalı yoksa (None, 'uzak dal yok')."""
    kod, _ = git(depo, "remote", "get-url", "origin")
    if kod != 0:
        return None, "uzak depo tanımlı değil"
    kod, out = git(depo, "rev-parse", "--abbrev-ref", "@{u}")
    if kod != 0:
        return None, "uzak dal yok (upstream kurulmamış)"
    kod, out = git(depo, "rev-list", "--count", "@{u}..HEAD")
    if kod != 0:
        return None, f"sayılamadı: {out[:200]}"
    try:
        return int(out.strip()), ""
    except ValueError:
        return None, f"beklenmeyen çıktı: {out[:200]}"


def calisma_agaci_kirli_mi(depo: Path) -> int:
    kod, out = git(depo, "status", "--porcelain")
    if kod != 0:
        return 0
    return len([s for s in out.splitlines() if s.strip()])


def _script_var_mi(pkg: dict, ad: str) -> bool:
    scripts = pkg.get("scripts")
    if not isinstance(scripts, dict):
        return False
    deger = scripts.get(ad)
    return isinstance(deger, str) and bool(deger.strip())


def _npm_test_bos_mu(pkg: dict) -> bool:
    scripts = pkg.get("scripts")
    if not isinstance(scripts, dict):
        return True
    deger = str(scripts.get("test", "")).lower()
    return (not deger.strip()) or "no test specified" in deger


def dogrula(depo: Path) -> dict:
    """Depo türüne göre doğrulama çalıştırır. Dönüş: {tur, sonuc, ayrinti}.

    sonuc: 'yok' (araç yok, doğrulanmadan push edilir), 'gecti', 'dustu'.
    """
    pkg_yolu = depo / "package.json"
    if pkg_yolu.is_file():
        try:
            pkg = json.loads(pkg_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pkg = {}
        adimlar = []
        if _script_var_mi(pkg, "build"):
            adimlar.append("build")
        if _script_var_mi(pkg, "test") and not _npm_test_bos_mu(pkg):
            adimlar.append("test")
        if not adimlar:
            return {"tur": "node", "sonuc": "yok", "ayrinti": "build/test script'i yok"}
        for adim in adimlar:
            kod, out, err = _calistir(["npm", "run", adim], depo, DOGRULAMA_ZAMAN_SINIRI)
            if kod != 0:
                return {"tur": "node", "sonuc": "dustu",
                        "ayrinti": f"npm run {adim}: {(out + err).strip()[-300:]}"}
        return {"tur": "node", "sonuc": "gecti", "ayrinti": "npm run " + " + ".join(adimlar)}

    swift_var = (depo / "Package.swift").is_file() or any(depo.glob("*.xcodeproj"))
    if swift_var:
        if not (depo / "Package.swift").is_file():
            return {"tur": "swift", "sonuc": "yok", "ayrinti": "xcodeproj için doğrulama aracı yok"}
        kod, out, err = _calistir(["swift", "build"], depo, DOGRULAMA_ZAMAN_SINIRI)
        if kod != 0:
            return {"tur": "swift", "sonuc": "dustu", "ayrinti": (out + err).strip()[-300:]}
        return {"tur": "swift", "sonuc": "gecti", "ayrinti": "swift build"}

    py_isaretleri = (depo / "pyproject.toml").is_file() or (depo / "requirements.txt").is_file()
    py_dosyalari = list(depo.rglob("*.py")) if not py_isaretleri else None
    if py_isaretleri or (py_dosyalari and any(
        ".git" not in p.parts and "node_modules" not in p.parts for p in py_dosyalari
    )):
        # pytest var mı dene; yoksa py_compile ile sözdizimi kontrolü.
        pytest_var = _calistir(["python3", "-c", "import pytest"], depo, 10)[0] == 0
        if pytest_var:
            kod, out, err = _calistir(["python3", "-m", "pytest", "-q"], depo, DOGRULAMA_ZAMAN_SINIRI)
            if kod != 0:
                return {"tur": "python", "sonuc": "dustu", "ayrinti": (out + err).strip()[-300:]}
            return {"tur": "python", "sonuc": "gecti", "ayrinti": "pytest -q"}
        dosyalar = [
            p for p in depo.rglob("*.py")
            if ".git" not in p.parts and "node_modules" not in p.parts
            and ".venv" not in p.parts and "venv" not in p.parts
        ]
        if not dosyalar:
            return {"tur": "python", "sonuc": "yok", "ayrinti": ".py dosyası yok"}
        hatali = []
        for p in dosyalar:
            kod, out, err = _calistir(
                ["python3", "-m", "py_compile", str(p)], depo, 20
            )
            if kod != 0:
                hatali.append(f"{p.relative_to(depo)}: {(out + err).strip()[-200:]}")
        if hatali:
            return {"tur": "python", "sonuc": "dustu",
                    "ayrinti": f"{len(hatali)} dosya sözdizimi hatası: " + " | ".join(hatali[:3])}
        return {"tur": "python", "sonuc": "gecti",
                "ayrinti": f"py_compile ({len(dosyalar)} dosya)"}

    return {"tur": "yok", "sonuc": "yok", "ayrinti": "doğrulama aracı yok"}


def push_et(depo: Path) -> tuple[bool, str]:
    kod, out, err = _calistir(["git", "push", "origin", "HEAD"], depo, PUSH_ZAMAN_SINIRI)
    if kod == 0:
        return True, (out + err).strip()[-200:]
    return False, (out + err).strip()[-200:]


def bir_depo(depo: Path, kuru: bool) -> dict:
    kayit: dict = {"zaman": simdi(), "depo": depo.name}

    n, aciklama = bekleyen_commit(depo)
    kayit["bekleyen_commit"] = n
    if n is None:
        kayit["sonuc"] = "atlandi"
        kayit["ayrinti"] = aciklama
        return kayit
    if n == 0:
        kayit["sonuc"] = "temiz"
        kayit["ayrinti"] = "push bekleyen commit yok"
        return kayit

    kirli = calisma_agaci_kirli_mi(depo)
    if kirli:
        kayit["calisma_agaci_kirli"] = kirli

    dog = dogrula(depo)
    kayit["dogrulama"] = dog

    if dog["sonuc"] == "dustu":
        kayit["sonuc"] = "push_edilmedi"
        kayit["push_ayrinti"] = "doğrulama düştü, push edilmedi"
        return kayit

    if kuru:
        kayit["sonuc"] = "kuru_calistirma"
        kayit["push_ayrinti"] = (
            "doğrulanmadan push edilirdi" if dog["sonuc"] == "yok" else "push edilirdi"
        )
        return kayit

    ok, ayrinti = push_et(depo)
    if ok:
        kayit["sonuc"] = "push_edildi" if dog["sonuc"] == "gecti" else "push_edildi_dogrulanmadan"
        kayit["push_ayrinti"] = ayrinti or "tamam"
    else:
        kayit["sonuc"] = "push_hatasi"
        kayit["push_ayrinti"] = ayrinti
    return kayit


def durum_yaz(sonuclar: dict[str, dict]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    onceki = _json_oku(DURUM_DOSYASI)
    depolar_kaydi = onceki.get("depolar") if isinstance(onceki.get("depolar"), dict) else {}
    depolar_kaydi.update(sonuclar)
    yeni = {"son_calisma": simdi(), "depolar": depolar_kaydi}
    try:
        gecici = STATE / f".push-durum.{os.getpid()}.tmp"
        gecici.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(gecici, DURUM_DOSYASI)
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="Hiçbir şey push etmeden ne yapacağını yazar.")
    args = ap.parse_args()

    kok = projeler_koku()
    if kok is None:
        print("beyin.json içinde 'projeler' kökü bulunamadı ya da klasör yok.")
        return 1

    sonuclar: dict[str, dict] = {}
    for depo in depolar(kok):
        kayit = bir_depo(depo, args.kuru)
        sonuclar[depo.name] = kayit
        satir = f"{depo.name}: {kayit['sonuc']}"
        if kayit.get("dogrulama"):
            satir += f" (doğrulama: {kayit['dogrulama']['tur']}/{kayit['dogrulama']['sonuc']})"
        if kayit.get("push_ayrinti"):
            satir += f" — {kayit['push_ayrinti'][:150]}"
        print(satir)

    if not args.kuru:
        durum_yaz(sonuclar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
