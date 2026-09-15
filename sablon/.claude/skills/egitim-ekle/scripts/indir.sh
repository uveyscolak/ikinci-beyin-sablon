#!/bin/zsh
# Wistia videolarını ders adıyla indirir. Var olanı atlar, 3 paralel çalışır.
# Kullanım: indir.sh <dersler.json yolu> <hedef VİDEOLAR klasörü> <site domaini> [format]
# format verilmezse hd_mp4-1080p/best. Büyük eğitimlerde 720p için şu ifade kullanılır:
#   'hd_mp4-720p/best[width<=1280][format_id!=original]/best[width<=1280]/best'
# Saatte ~210 MB tutar (1080p ~2,4 GB). Üç tuzağın üçünü birden kapatır:
#  1) Sadece ada bakma (`hd_mp4-720p/best`): bir videonun iki kopyası varsa Wistia kimlikleri
#     `hd_mp4-720p-0`, `hd_mp4-720p-1` diye sonek alır, ad tutmaz, seçim `best`e düşer.
#  2) Yükseklikle filtreleme: 720p katmanının yüksekliği kaynağın en-boy oranına göre 582 ile
#     832 arasında değişiyor; sabit olan genişlik (1280).
#  3) Sadece genişlikle filtreleme (`best[width<=1280]`): ham `original` kopya bazen 1280'den
#     dar oluyor (ör. 1244px) ve bitrate'i yüksek olduğu için "en iyi" sayılıp seçiliyor;
#     2,2 GB'lık ham dosya 645 MB'lık 720p yerine iniyor. `format_id!=original` bunu keser.
# 2026-09-14 OTÜ panelinde üçü de yaşandı; 946 videonun 17'si ham kopya inip 13,7 GB fazla yer
# kaplamıştı, bitrate taramasıyla yakalanıp yeniden indirildi.
S=$(cd "$(dirname "$1")" && pwd)
DERSLER="$1"
V="$2"
SITE="$3"
FORMAT="${4:-hd_mp4-1080p/best}"
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
  if yt-dlp -q --no-warnings --referer "'"$SITE"'" -f "'"$FORMAT"'" --no-part -o "'"$V"'/$base.mp4" "wistia:$wid" >> "'"$LOG"'" 2>&1; then
    echo "OK    $(date +%H:%M) $base" >> "'"$LOG"'"
  else
    echo "HATA  $(date +%H:%M) $base ($wid)" >> "'"$LOG"'"
  fi
' < "$S/indir-kuyruk.txt"
echo "BİTTİ $(date +%H:%M)" >> "$LOG"
