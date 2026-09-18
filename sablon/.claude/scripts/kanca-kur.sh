#!/bin/bash
# Git kayıt öncesi sır tarama kancasını kurar.
# Mevcut bir pre-commit varsa içeriği korunur, tarama satırı sonuna eklenir.
# Kullanım: bash .claude/scripts/kanca-kur.sh
set -e

KOK="$(git rev-parse --show-toplevel)"
KANCA="$KOK/.git/hooks/pre-commit"
CAGRI='python3 "$(git rev-parse --show-toplevel)/.claude/scripts/pre-commit-sir.py" || exit 1'

if [ -f "$KANCA" ] && grep -q "pre-commit-sir.py" "$KANCA"; then
  echo "Sır tarama kancası zaten kurulu."
  exit 0
fi

if [ -f "$KANCA" ]; then
  printf '\n# İkinci beyin — sır taraması\n%s\n' "$CAGRI" >> "$KANCA"
  echo "Mevcut pre-commit korundu, sır tarama satırı eklendi."
else
  cat > "$KANCA" <<'INNER'
#!/bin/bash
# İkinci beyin — kayıt öncesi sır taraması.
KOK="$(git rev-parse --show-toplevel)"
TARAYICI="$KOK/.claude/scripts/pre-commit-sir.py"
if [ -f "$TARAYICI" ]; then
  python3 "$TARAYICI" "$KOK" || exit 1
fi
exit 0
INNER
  echo "Sır tarama kancası kuruldu."
fi

chmod +x "$KANCA"
