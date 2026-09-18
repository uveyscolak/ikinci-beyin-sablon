#!/usr/bin/env python3
"""Vault'un kendi git deposunu push eder, sonucu .state/push-durum.json'a "vault" anahtarıyla yazar.

session-end.sh commit'ten sonra bunu çağırır; session-start.sh de önceki oturumdan kalan
push'u aynı yoldan dener. Ağ yoksa ya da uzak erişilemiyorsa hata değil "ertelendi" sayılır
(bir sonraki oturumda tekrar denenir, açılış kancası bunu sorun olarak basmaz).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
STATE = VAULT / ".claude" / "scripts" / ".state"
DURUM_DOSYASI = STATE / "push-durum.json"
ZAMAN_SINIRI = 60

# Ağ/uzak erişim sorunlarına işaret eden ifadeler: hata değil, ertelendi sayılır.
ERTELEME_IFADELERI = (
    "could not resolve host",
    "could not resolve proxy",
    "network is unreachable",
    "connection timed out",
    "connection refused",
    "operation timed out",
    "no route to host",
    "temporary failure in name resolution",
    "unable to access",
    "failed to connect",
)


def simdi() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _json_oku(path: Path) -> dict:
    try:
        veri = json.loads(path.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def durum_yaz(kayit: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    onceki = _json_oku(DURUM_DOSYASI)
    if not isinstance(onceki.get("depolar"), dict):
        onceki["depolar"] = {}
    onceki["vault"] = kayit
    try:
        gecici = STATE / f".push-durum.{os.getpid()}.tmp"
        gecici.write_text(json.dumps(onceki, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(gecici, DURUM_DOSYASI)
    except OSError:
        pass


def main() -> int:
    if not (VAULT / ".git").is_dir():
        return 0
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10, cwd=str(VAULT),
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if r.returncode != 0:
        return 0  # uzak depo yok; saglik.py zaten bunu ayrı raporluyor.

    try:
        r = subprocess.run(
            ["git", "push", "-q", "origin", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=ZAMAN_SINIRI, cwd=str(VAULT),
        )
    except subprocess.TimeoutExpired:
        durum_yaz({"zaman": simdi(), "sonuc": "ertelendi", "ayrinti": "zaman sınırı aşıldı"})
        return 0
    except OSError as e:
        durum_yaz({"zaman": simdi(), "sonuc": "hata", "cikis_kodu": -1, "ayrinti": str(e)[:200]})
        return 0

    if r.returncode == 0:
        durum_yaz({"zaman": simdi(), "sonuc": "tamam", "ayrinti": ""})
        return 0

    hata_metni = ((r.stdout or "") + (r.stderr or "")).strip()
    kucuk = hata_metni.lower()
    if any(ifade in kucuk for ifade in ERTELEME_IFADELERI):
        durum_yaz({
            "zaman": simdi(), "sonuc": "ertelendi",
            "cikis_kodu": r.returncode, "ayrinti": hata_metni[-200:],
        })
        return 0

    durum_yaz({
        "zaman": simdi(), "sonuc": "hata",
        "cikis_kodu": r.returncode, "ayrinti": hata_metni[-200:],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
