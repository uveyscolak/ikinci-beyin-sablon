#!/usr/bin/env python3
"""Kaçırılmış oturum özetlerini telafi eder.

`SessionEnd` kancası ancak Claude Code düzgün kapanırsa ateşler. Uygulama zorla
kapatılırsa, makine kapanırken süreç kesilirse ya da oturum başka bir sebeple
sessizce ölürse o oturumun özeti hiç yazılmaz ve telafisi yoktur.

Bu script oturum açılışında arka planda çalışır: `~/.claude/projects` altındaki
transkriptlerden özetlenmemiş ve artık yaşamayan olanları bulur, her biri için
`flush.py`'yi kendi kancası çağırmış gibi çalıştırır. Zaman damgası oturumun
gerçekten bittiği ana ayarlanır (`BEYIN_FAKE_NOW`), böylece özet doğru günün
dosyasına doğru saatle düşer.

Bir oturumun özetlenip özetlenmediği flush.py'nin kendi durum dosyasından
okunur (`.state/flush-<sha256(session_id)>.json`); yani bu script mükerrer
özet üretemez.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = SCRIPT_DIR / ".state"
FLUSH = SCRIPT_DIR / "flush.py"
PROJECTS_ROOT = Path.home() / ".claude" / "projects"

# Beynin kendi alt çağrıları da transkript bırakır; onlar oturum değildir.
SANDBOX_ISARETLERI = ("beyin-flush", "beyin-compile-stage", "beyin-")

LOCK = STATE_DIR / "catchup.lock"
LOCK_STALE_SECONDS = 3600
FLUSH_TIMEOUT_SECONDS = 300


def _key(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def _ozetlenmis_mi(session_id: str) -> bool:
    return (STATE_DIR / f"flush-{_key(session_id)}.json").exists()


def _cwd_oku(transcript: Path) -> str:
    """Transkriptin ilk satırlarından çalışma dizinini çıkarır (proje adı için)."""
    try:
        with transcript.open(encoding="utf-8", errors="replace") as kaynak:
            for _ in range(20):
                satir = kaynak.readline()
                if not satir:
                    break
                try:
                    kayit = json.loads(satir)
                except json.JSONDecodeError:
                    continue
                if isinstance(kayit, dict):
                    cwd = kayit.get("cwd")
                    if isinstance(cwd, str) and cwd:
                        return cwd
    except OSError:
        pass
    return ""


def adaylari_bul(args: argparse.Namespace, simdi: float) -> list[tuple[float, Path]]:
    if not PROJECTS_ROOT.is_dir():
        return []
    adaylar: list[tuple[float, Path]] = []
    for proje_dizini in PROJECTS_ROOT.iterdir():
        if not proje_dizini.is_dir():
            continue
        if any(im in proje_dizini.name for im in SANDBOX_ISARETLERI):
            continue
        for transcript in proje_dizini.glob("*.jsonl"):
            session_id = transcript.stem
            if args.current_key and _key(session_id) == args.current_key:
                continue
            if _ozetlenmis_mi(session_id):
                continue
            try:
                mtime = transcript.stat().st_mtime
            except OSError:
                continue
            yas = simdi - mtime
            if yas < args.idle_seconds:          # hâlâ yaşıyor olabilir
                continue
            if yas > args.max_age_days * 86400:  # çok eski, geçmişi kazmayız
                continue
            if transcript.stat().st_size < 2048:  # boş/çok kısa oturum
                continue
            adaylar.append((mtime, transcript))
    adaylar.sort()
    return adaylar[: args.max_sessions]


def telafi_et(transcript: Path, mtime: float) -> bool:
    session_id = transcript.stem
    hookin = STATE_DIR / f"hookin-catchup-{_key(session_id)[:16]}.json"
    govde = {
        "session_id": session_id,
        "transcript_path": str(transcript),
        "cwd": _cwd_oku(transcript),
        "hook_event_name": "SessionEnd",
        "reason": "catchup",
    }
    eski_umask = os.umask(0o077)
    try:
        hookin.write_text(json.dumps(govde, ensure_ascii=False), encoding="utf-8")
    finally:
        os.umask(eski_umask)

    ortam = dict(os.environ)
    ortam["BEYIN_FAKE_NOW"] = dt.datetime.fromtimestamp(mtime).astimezone().isoformat()
    ortam.pop("BEYIN_INVOKED_BY", None)
    try:
        sonuc = subprocess.run(
            [sys.executable, str(FLUSH), "--hook-input", str(hookin),
             "--reason", "catchup"],
            env=ortam,
            timeout=FLUSH_TIMEOUT_SECONDS,
            capture_output=True,
        )
        return sonuc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            hookin.unlink()
        except OSError:
            pass


def _kilit_al(simdi: float) -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if LOCK.exists() and simdi - LOCK.stat().st_mtime > LOCK_STALE_SECONDS:
            LOCK.unlink()
    except OSError:
        pass
    try:
        tanitici = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    except OSError:
        return False
    os.close(tanitici)
    return True


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("BEYIN_INVOKED_BY"):
        return 0

    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--current-key", default="",
                            help="şu an açık olan oturumun sha256 anahtarı")
    ayristirici.add_argument("--idle-seconds", type=int, default=900)
    ayristirici.add_argument("--max-age-days", type=int, default=7)
    ayristirici.add_argument("--max-sessions", type=int, default=5)
    ayristirici.add_argument("--dry-run", action="store_true")
    args = ayristirici.parse_args(argv)

    simdi = time.time()
    adaylar = adaylari_bul(args, simdi)

    if args.dry_run:
        for mtime, transcript in adaylar:
            an = dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{an}  {transcript.parent.name}/{transcript.name}")
        print(f"toplam aday: {len(adaylar)}")
        return 0

    if not adaylar:
        return 0
    if not _kilit_al(simdi):
        return 0
    try:
        for mtime, transcript in adaylar:
            telafi_et(transcript, mtime)
    finally:
        try:
            LOCK.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
