#!/bin/zsh
# Wistia videolarını ders adıyla indirir. Var olanı atlar, 3 paralel çalışır.
# Kullanım: indir.sh <dersler.json yolu> <hedef VİDEOLAR klasörü> <site domaini>
S=$(cd "$(dirname "$1")" && pwd)
DERSLER="$1"
V="$2"
SITE="$3"
LOG="$S/indir.log"
export V LOG DERSLER

python3 - <<'EOF' > "$S/indir-kuyruk.txt"
import json, os
V=os.environ['V']; LOG=os.environ['LOG']; DERSLER=os.environ['DERSLER']
kuyruk=[]
with open(LOG,'a') as log:
    for x in json.load(open(DERSLER)):
        p=os.path.join(V, x['base']+'.mp4')
        if os.path.exists(p) and os.path.getsize(p)>0:
            log.write('VAR   '+x['base']+'\n')
        else:
            kuyruk.append(x['wistia']+'\t'+x['base'])
    log.write('kuyruk: %d video, başlangıç %s\n' % (len(kuyruk), __import__('time').strftime('%H:%M')))
print('\0'.join(kuyruk), end='')
EOF

# macOS xargs -d desteklemiyor, NUL ayraç için -0 kullanılır.
xargs -0 -P 3 -n 1 sh -c '
  satir="$0"; wid="${satir%%	*}"; base="${satir#*	}"
  if yt-dlp -q --no-warnings --referer "'"$SITE"'" -f "hd_mp4-1080p/best" --no-part -o "'"$V"'/$base.mp4" "wistia:$wid" >> "'"$LOG"'" 2>&1; then
    echo "OK    $(date +%H:%M) $base" >> "'"$LOG"'"
  else
    echo "HATA  $(date +%H:%M) $base ($wid)" >> "'"$LOG"'"
  fi
' < "$S/indir-kuyruk.txt"
echo "BİTTİ $(date +%H:%M)" >> "$LOG"
