#!/usr/bin/env python3
"""Vault'taki motoru şablon deposuna kişisel iz bırakmadan kopyalar.

Kaynak: bu vault'un .claude/ klasörü. Hedef: .claude/beyin.json içindeki "sablon" yolu, altındaki
`sablon/.claude/`. Yalnız genel dosyalar kopyalanır; vault'un `.claude/skills/` altındaki kişiye
özel skill'ler (egitim, hatirla, gorsel-prompt) kopyalanmaz. egitim ve hatirla'nın şablonda kendi
genel sürümü vardır, gorsel-prompt'un yoktur. (sheets ve transkript kişisel skill'leri global
`~/.claude/skills/` altındadır, bu script'in konusu değildir.) Kopyalanan her dosya yasak
kelimeler için taranır; iz bulunursa dosya silinir ve script hata verir.
"""
from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent
DOSYALAR = [
    "hooks/lib.sh", "hooks/session-start.sh", "hooks/session-start.py", "hooks/prompt-counter.sh",
    "hooks/proje-yonerge.sh", "hooks/proje-yonerge.py", "hooks/pre-compact.sh", "hooks/session-end.sh",
    "scripts/flush.py", "scripts/compile.py", "scripts/flush-catchup.py", "scripts/_gitcommit.py",
    "scripts/_portalock.py", "scripts/egitim-icindekiler.py", "scripts/saglik.py", "scripts/sablon-guncelle.py",
    "scripts/index-uret.py",
    "scripts/proje-kur.py", "skills/proje-kur/SKILL.md",
    "skills/beyin-doktor/SKILL.md", "skills/gecmis-import/SKILL.md", "skills/haftalik/SKILL.md",
    "skills/kaynak/SKILL.md",
    "agents/arastirmaci.md", "agents/amele.md", "agents/mimar.md", "agents/denetci.md",
]
YASAK = ["Üveys", "ÜVEYS", "uveys", "Minval", "MİNVAL", "minval", "/Volumes/DEPO", "genuine-tower",
         "Tomar", "Droper", "Listender", "Engin", "minvaltaki"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vault'taki motoru şablon deposuna kişisel iz bırakmadan kopyalar."
    )
    parser.add_argument(
        "sablon_kok",
        nargs="?",
        default=None,
        help='şablon kökü (verilmezse beyin.json içindeki "sablon" yolu kullanılır)',
    )
    args = parser.parse_args()
    try:
        ayar = json.loads((VAULT / ".claude" / "beyin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ayar = {}
    hedef_kok = ayar.get("sablon") if isinstance(ayar, dict) else None
    if args.sablon_kok:
        hedef_kok = args.sablon_kok
    if not hedef_kok:
        print("şablon yolu yok: beyin.json içine \"sablon\" yaz veya argüman ver", file=sys.stderr)
        return 1
    hedef = Path(hedef_kok).expanduser() / "sablon" / ".claude"
    hata = 0
    for rel in DOSYALAR:
        kaynak = VAULT / ".claude" / rel
        if not kaynak.is_file():
            print("atlandı (yok):", rel)
            continue
        cikti = hedef / rel
        cikti.parent.mkdir(parents=True, exist_ok=True)
        metin = kaynak.read_text(encoding="utf-8", errors="replace")
        bulunan = [] if rel.endswith("sablon-guncelle.py") else [k for k in YASAK if k in metin]
        if bulunan:
            # Kirli dosya kopyalanmaz; şablondaki eski temiz kopya olduğu gibi kalır.
            print(f"KİŞİSEL İZ, kopyalanmadı (eski kopya korundu): {rel} -> {bulunan}")
            hata = 1
            continue
        shutil.copy2(kaynak, cikti)
        if cikti.suffix in {".sh", ".py"}:
            cikti.chmod(cikti.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print("kopyalandı:", rel)
    (hedef / "scripts" / ".state").mkdir(parents=True, exist_ok=True)
    (hedef / "scripts" / ".state" / ".gitkeep").touch()
    return hata


if __name__ == "__main__":
    raise SystemExit(main())
