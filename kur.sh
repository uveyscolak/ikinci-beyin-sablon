#!/bin/bash
# İkinci Beyin kurulum script'i.
# Kullanım: ./kur.sh <VAULT_YOLU> --ad "Ayşe" --projeler "/Users/ayse/Projeler" [--global-ayar ~/.claude/settings.json]
# Mevcut dosyaların üzerine yazmaz; global kanca ayarını yedekleyip birleştirir.
set -e
BURASI=$(CDPATH= cd "$(dirname "$0")" && pwd)
SABLON="$BURASI/sablon"
VAULT=""; AD=""; PROJELER=""; GLOBAL="$HOME/.claude/settings.json"
while [ $# -gt 0 ]; do
  case "$1" in
    --ad) AD="$2"; shift 2 ;;
    --projeler) PROJELER="$2"; shift 2 ;;
    --global-ayar) GLOBAL="$2"; shift 2 ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) [ -z "$VAULT" ] && VAULT="$1" || { echo "bilinmeyen argüman: $1"; exit 1; }; shift ;;
  esac
done
[ -n "$VAULT" ] || { echo "vault yolu gerekli. Örnek: ./kur.sh ~/Belgeler/Beyin --ad Ayşe --projeler ~/Projeler"; exit 1; }
[ -d "$SABLON" ] || { echo "sablon/ klasörü bulunamadı: $SABLON"; exit 1; }
if [ -z "$AD" ] && [ -t 0 ]; then read -r -p "Adın ne? " AD; fi
if [ -z "$PROJELER" ] && [ -t 0 ]; then read -r -p "Projelerin hangi klasörde? (boş bırakabilirsin) " PROJELER; fi
[ -n "$AD" ] || AD="Kullanıcı"

echo "== Ön koşul"
EKSIK=0
command -v python3 >/dev/null 2>&1 && echo "python3: $(python3 -V 2>&1)" || { echo "python3 YOK (macOS: xcode-select --install)"; EKSIK=1; }
command -v git >/dev/null 2>&1 && echo "git: var" || { echo "git YOK"; EKSIK=1; }
command -v claude >/dev/null 2>&1 && echo "claude: var" || echo "claude CLI yolda değil: arka plan özeti ve derleme çalışmaz, kurulum devam ediyor"
[ "$EKSIK" = 0 ] || { echo "önce eksikleri kur"; exit 1; }

echo "== Vault: $VAULT"
mkdir -p "$VAULT"
VAULT=$(CDPATH= cd "$VAULT" && pwd)
if command -v rsync >/dev/null 2>&1; then
  rsync -a --ignore-existing "$SABLON/" "$VAULT/"
else
  cp -Rn "$SABLON/." "$VAULT/" 2>/dev/null || true
fi
[ -f "$VAULT/.gitignore" ] || mv "$VAULT/gitignore.sablon" "$VAULT/.gitignore"
rm -f "$VAULT/gitignore.sablon"
chmod +x "$VAULT/.claude/hooks/"*.sh "$VAULT/.claude/hooks/"*.py "$VAULT/.claude/scripts/"*.py
for h in "$VAULT/.claude/hooks/"*.sh; do bash -n "$h"; done
python3 -m py_compile "$VAULT/.claude/scripts/"*.py "$VAULT/.claude/hooks/"*.py
BUGUN=$(date +%F)
python3 - "$VAULT" "$AD" "$PROJELER" "$BUGUN" <<'PY'
import json, sys
from pathlib import Path
vault, ad, projeler, bugun = sys.argv[1:5]
V = Path(vault)
ayar = {"kullanici": ad, "projeler": projeler, "notlar_dosyasi": "NOTLARIM.md", "egitim_ciktilari": {}, "yedek": ""}
(V / ".claude" / "beyin.json").write_text(json.dumps(ayar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
# yer tutucular
for rel in ["CLAUDE.md", "HAFIZA/Son Oturum.md", "HAFIZA/Açık Konular.md", "HAFIZA/Kurallar.md", "HAFIZA/Günce.md",
            "PROJELER/Projeler.md", "KİŞİSEL/Kimlik.md"]:
    p = V / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    t = t.replace("<AD>", ad).replace("<YYYY-AA-GG>", bugun).replace("<VAULT>", str(V))
    t = t.replace("<VAULT ADI>", V.name)
    if projeler:
        t = t.replace("<PROJE-KÖKÜ>", projeler)
    p.write_text(t, encoding="utf-8")
print("yer tutucular dolduruldu")
PY

echo "== Global kancalar: $GLOBAL"
python3 - "$VAULT" "$GLOBAL" "$BUGUN" <<'PY'
import json, sys, shutil
from pathlib import Path
vault, gpath, bugun = sys.argv[1:4]
V = Path(vault); G = Path(gpath).expanduser()
ornek = json.loads((V / ".claude" / "settings.global.ornek.json").read_text(encoding="utf-8"))
G.parent.mkdir(parents=True, exist_ok=True)
data = {}
if G.exists():
    shutil.copy2(G, G.with_name(f"settings.json.yedek-{bugun}"))
    try:
        data = json.loads(G.read_text(encoding="utf-8"))
    except ValueError:
        data = {}
hooks = data.setdefault("hooks", {})
eklenen = 0
for ev, grup in ornek["hooks"].items():
    mevcut = hooks.setdefault(ev, [])
    for g in grup:
        g = json.loads(json.dumps(g).replace("<VAULT>", str(V)))
        ad = g["hooks"][0]["command"].split("/.claude/hooks/")[-1].split('"')[0]
        varmi = any(ad in (h.get("command") or "") for m in mevcut for h in (m.get("hooks") or []))
        if not varmi:
            mevcut.append(g); eklenen += 1
G.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"kanca eklendi: {eklenen} (zaten olanlar atlandı)")
PY

echo "== Global CLAUDE.md"
GLOBAL_KLASOR=$(dirname "$GLOBAL")
GLOBAL_CLAUDE="$GLOBAL_KLASOR/CLAUDE.md"
if [ -f "$GLOBAL_CLAUDE" ]; then
  echo "var, dokunulmadı; içindeki hafıza yolunu kontrol et: $GLOBAL_CLAUDE"
else
  python3 - "$VAULT" "$GLOBAL_CLAUDE" <<'PY'
import sys
from pathlib import Path
vault, hedef = sys.argv[1:3]
V = Path(vault)
kaynak = V / ".claude" / "CLAUDE.global.ornek.md"
metin = kaynak.read_text(encoding="utf-8").replace("<VAULT>", str(V))
H = Path(hedef)
H.parent.mkdir(parents=True, exist_ok=True)
H.write_text(metin, encoding="utf-8")
print(f"oluşturuldu: {H}")
PY
fi

echo "== Git"
cd "$VAULT"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -q
  git add -A
  if git diff --cached --name-only | grep -qE '^GİZLİ/|settings\.local\.json|\.env$'; then echo "DUR: sır sahnede, .gitignore'u kontrol et"; exit 1; fi
  git -c user.name="${AD}" -c user.email="beyin@localhost" commit -q -m "İkinci beyin kuruldu" && echo "ilk commit atıldı"
else
  echo "zaten git deposu, dokunulmadı"
fi

python3 "$VAULT/.claude/scripts/saglik.py" --bakim-yapildi >/dev/null 2>&1 || true

echo "== Deneme"
python3 "$VAULT/.claude/hooks/session-start.py" "$VAULT" --plain | head -c 400; echo
echo
echo "KURULUM TAMAM."
echo "1) Obsidian'ı aç, 'Open folder as vault' ile $VAULT klasörünü seç."
echo "2) Terminalde: cd \"$VAULT\" && claude   (ilk konuşmanı yap, kapat, GÜNLÜK/ klasörüne bak)"
echo "3) Yedek için özel bir uzak depo: gh repo create <ad> --private --source=. --remote=origin --push"
echo "4) Bir şey ters giderse Claude'a 'beyin doktor' yaz."
