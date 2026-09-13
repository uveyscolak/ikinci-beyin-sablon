#!/bin/zsh
# İndirmesi biten videoların transkriptini sırayla çıkarır; indirme bitip iş kalmayınca durur.
# Kullanım: transkript-dongu.sh <dersler.json> <VİDEOLAR klasörü> <indir.log> <transkript.py venv python yolu>
DERSLER="$1"
V="$2"
INDIRLOG="$3"
PY="${4:?transkript.py için venv python yolu gerekli}"
S=$(cd "$(dirname "$DERSLER")" && pwd)
LOG="$S/transkript.log"
echo "başladı $(date +%H:%M)" >> "$LOG"
while true; do
  bekleyen=()
  while IFS= read -r base; do
    [ -s "$V/$base.mp4" ] || continue
    [ -s "$V/$base.txt" ] && continue
    if grep -F -- "$base" "$INDIRLOG" 2>/dev/null | grep -q -E '^(OK|VAR)'; then
      bekleyen+=("$V/$base.mp4")
    fi
  done < <(python3 -c "
import json
for x in json.load(open('$DERSLER')): print(x['base'])
")
  if [ ${#bekleyen[@]} -gt 0 ]; then
    echo "parti: ${#bekleyen[@]} video $(date +%H:%M)" >> "$LOG"
    "$PY" "$(dirname "$0")/transkript.py" "${bekleyen[@]}" >> "$LOG" 2>&1
    continue
  fi
  if grep -q '^BİTTİ' "$INDIRLOG" 2>/dev/null; then
    kalan=$(python3 -c "
import json, os
V='$V'
print(sum(1 for x in json.load(open('$DERSLER')) if not os.path.exists(os.path.join(V, x['base']+'.txt'))))
")
    echo "indirme bitti, transkripti olmayan: $kalan $(date +%H:%M)" >> "$LOG"
    [ "$kalan" = "0" ] && { echo "TAMAM $(date +%H:%M)" >> "$LOG"; break; }
    grep -q '^HATA' "$INDIRLOG" && { echo "indirme hatalı videolar var, döngü bitti $(date +%H:%M)" >> "$LOG"; break; }
  fi
  sleep 60
done
