#!/bin/bash
# PostToolUse kancası: yazılan .md dosyasını dosya-denetle.py'ye denetletir.
DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
exec python3 "$DIR/dosya-denetle.py"
