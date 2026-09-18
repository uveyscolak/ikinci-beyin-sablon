#!/usr/bin/env python3
"""Claude Code konuşma kayıtlarından gün bazında token kullanımı çıkarır.

Kaynak: ~/.claude/projects altındaki .jsonl kayıtları.
  - Ana oturumlar: <proje klasörü>/<uuid>.jsonl
  - Alt ajanlar:   <proje klasörü>/<uuid>/subagents/agent-*.jsonl

Bu script yalnız sayısal alanları okur: her assistant satırının `message.usage` bloğu
(input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens) ve
satırın `timestamp` alanı. Konuşma metnine (content, thinking, araç sonuçları) hiç
dokunmaz ve hiçbir yere yazmaz; rapora yalnız sayılar girer.

Çıktı: HAFIZA/Token Raporu.md, son otuz günün tablosu, en yeni gün üstte. Açılış kancası
bu tablodan tek satır basar ("Dün: 1,2 milyon token, 6 oturum").
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VAULT = Path(__file__).resolve().parent.parent.parent
ISTANBUL = ZoneInfo("Europe/Istanbul")
KAYIT_KOKU = Path.home() / ".claude" / "projects"
HEDEF = VAULT / "HAFIZA" / "Token Raporu.md"
GUN_SAYISI = 30

GIRIS = (
    "Claude Code'un kendi konuşma kayıtlarından çıkarılan günlük token kullanımı; bu dosyayı"
    " gece bakımı yeniden üretir, elle düzenleme.\n"
    "Sayılar yalnız kullanım alanlarından okunur, konuşma metni hiç okunmaz ve buraya hiçbir"
    " konuşma içeriği girmez.\n"
)


def satirlari_oku(yol: Path):
    """Bir .jsonl dosyasını satır satır okur, bozuk satırları atlar."""
    try:
        with yol.open("r", encoding="utf-8", errors="replace") as f:
            for satir in f:
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    yield json.loads(satir)
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return


def kullanim(kayit: dict):
    """assistant satırından dört token sayısını çıkarır; assistant değilse None."""
    mesaj = kayit.get("message")
    if not isinstance(mesaj, dict):
        return None
    u = mesaj.get("usage")
    if not isinstance(u, dict):
        return None
    return (
        int(u.get("input_tokens") or 0),
        int(u.get("cache_creation_input_tokens") or 0),
        int(u.get("cache_read_input_tokens") or 0),
        int(u.get("output_tokens") or 0),
    )


def istanbul_gunu(ts: str):
    """ISO zaman damgasını (UTC, sonu Z) İstanbul saatiyle bir güne çevirir."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        an = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return an.astimezone(ISTANBUL).date()


def kayitlari_topla(kok: Path, gun_sayisi: int) -> dict:
    """Gün başına toplamlar: dört token sayısı, oturum kümesi, alt ajan kaydı sayısı."""
    bugun = datetime.now(ISTANBUL).date()
    en_eski = bugun - timedelta(days=gun_sayisi - 1)
    gunler: dict = defaultdict(lambda: {
        "girdi": 0, "onbellek_yaz": 0, "onbellek_oku": 0, "cikti": 0,
        "oturumlar": set(), "alt_ajan": set(),
    })
    if not kok.is_dir():
        return gunler

    for proje in kok.iterdir():
        if not proje.is_dir():
            continue
        # Ana oturumlar doğrudan proje klasöründe, alt ajanlar subagents altında durur.
        for yol in list(proje.glob("*.jsonl")) + list(proje.glob("*/subagents/*.jsonl")):
            alt_ajan_mi = "subagents" in yol.parts
            kimlik = str(yol)
            for kayit in satirlari_oku(yol):
                sayilar = kullanim(kayit)
                if sayilar is None:
                    continue
                gun = istanbul_gunu(kayit.get("timestamp"))
                if gun is None or gun < en_eski or gun > bugun:
                    continue
                d = gunler[gun]
                d["girdi"] += sayilar[0]
                d["onbellek_yaz"] += sayilar[1]
                d["onbellek_oku"] += sayilar[2]
                d["cikti"] += sayilar[3]
                if alt_ajan_mi:
                    d["alt_ajan"].add(kimlik)
                else:
                    d["oturumlar"].add(kimlik)
    return gunler


def bicim(n: int) -> str:
    """Binlik ayraçlı sayı; Türkçede ayraç noktadır."""
    return f"{n:,}".replace(",", ".")


def tablo(gunler: dict) -> str:
    satirlar = [
        "| Gün | Oturum | Alt ajan kaydı | Girdi | Önbellek yazma | Önbellek okuma | Çıktı | Toplam |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for gun in sorted(gunler, reverse=True):
        d = gunler[gun]
        toplam = d["girdi"] + d["onbellek_yaz"] + d["onbellek_oku"] + d["cikti"]
        satirlar.append(
            f"| {gun.isoformat()} | {len(d['oturumlar'])} | {len(d['alt_ajan'])} | "
            f"{bicim(d['girdi'])} | {bicim(d['onbellek_yaz'])} | {bicim(d['onbellek_oku'])} | "
            f"{bicim(d['cikti'])} | {bicim(toplam)} |"
        )
    return "\n".join(satirlar)


def uret(gun_sayisi: int = GUN_SAYISI) -> str:
    gunler = kayitlari_topla(KAYIT_KOKU, gun_sayisi)
    parca = ["# Token Raporu", "", GIRIS.rstrip(), ""]
    if not gunler:
        parca.append("Son otuz günde okunabilir bir kullanım kaydı bulunamadı.")
        return "\n".join(parca) + "\n"
    parca.append(tablo(gunler))
    parca.append("")
    parca.append(f"_Son {len(gunler)} gün. Üretildi: {datetime.now(ISTANBUL).strftime('%Y-%m-%d %H:%M')}._")
    return "\n".join(parca) + "\n"


def main() -> int:
    gun_sayisi = GUN_SAYISI
    for i, arg in enumerate(sys.argv):
        if arg == "--gun" and i + 1 < len(sys.argv):
            try:
                gun_sayisi = max(1, int(sys.argv[i + 1]))
            except ValueError:
                pass
    metin = uret(gun_sayisi)
    if "--goster" in sys.argv:
        print(metin, end="")
        return 0
    try:
        HEDEF.parent.mkdir(parents=True, exist_ok=True)
        HEDEF.write_text(metin, encoding="utf-8")
    except OSError as e:
        print(f"Token Raporu.md yazılamadı: {e}", file=sys.stderr)
        return 1
    print(f"Token Raporu.md üretildi: {len(metin.splitlines())} satır")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
