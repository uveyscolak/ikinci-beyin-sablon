#!/usr/bin/env python3
"""PostToolUse (Write|Edit|MultiEdit) kancası: yazılan .md dosyasının
YAML üst bilgi bloğuyla (---) başlamadığını denetler.

Alan sayfaları (`tetik:` içeren ön blok) muaftır. EĞİTİMLER/KAYNAKLAR/ ve
.claude/ altı, vault dışı ve .md olmayan dosyalar denetlenmez.
"""
import json
import sys
from pathlib import Path

VAULT_KOK = Path(__file__).resolve().parents[2]


def main():
    try:
        veri = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    try:
        tool_input = veri.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)

        file_path = tool_input.get("file_path")
        if not file_path:
            sys.exit(0)

        yol = Path(file_path)
        try:
            yol = yol.resolve()
        except Exception:
            sys.exit(0)

        try:
            goreli_yol = yol.relative_to(VAULT_KOK)
        except ValueError:
            sys.exit(0)

        if yol.suffix != ".md":
            sys.exit(0)

        goreli_str = str(goreli_yol)
        if goreli_str.startswith("EĞİTİMLER/KAYNAKLAR/") or goreli_str.startswith(".claude/"):
            sys.exit(0)

        try:
            with open(yol, "r", encoding="utf-8") as f:
                satirlar = f.readlines()
        except OSError:
            sys.exit(0)

        if not satirlar:
            sys.exit(0)

        if satirlar[0].rstrip("\n") != "---":
            sys.exit(0)

        # Ön blok kapanışına kadar tara; "tetik:" varsa muaf (Alan sayfası).
        muaf = False
        for satir in satirlar[1:]:
            if satir.rstrip("\n") == "---":
                break
            if satir.startswith("tetik:"):
                muaf = True
                break

        if muaf:
            sys.exit(0)

        sonuc = {
            "decision": "block",
            "reason": (
                "Kural: notlar YAML üst bilgi bloğuyla (---) başlamaz; Obsidian "
                "bunu her sayfada Özellikler paneli olarak gösterir, kullanıcı "
                f"istemiyor. {goreli_str} bu blokla başlıyor. Bloğu kaldır, "
                "gerekli bilgiyi gövdeye tek satır künye olarak yaz."
            ),
        }
        print(json.dumps(sonuc, ensure_ascii=False))
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
