#!/bin/bash
# Stop kancası: son asistan cevabındaki dosya linklerini cevap-denetle.py'ye denetletir.
DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
exec python3 "$DIR/cevap-denetle.py"
