#!/bin/bash
[ -n "${BEYIN_INVOKED_BY:-}" ] && exit 0
# Kullanıcı bir proje adı geçirdiğinde o projenin yönergesini ve güncel durumunu
# doğrudan konuşmaya enjekte eder. "Şuraya bak" demek yerine önüne koyar.

BEYIN_HOOK_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
. "$BEYIN_HOOK_DIR/lib.sh" 2>/dev/null || exit 0

command -v python3 >/dev/null 2>&1 || exit 0

BEYIN_GIRDI="$BEYIN_STATE_DIR/yonerge-$$.json"
umask 077
cat > "$BEYIN_GIRDI" 2>/dev/null || exit 0

BEYIN_METIN=$(BEYIN_VAULT="$BEYIN_PROJECT_DIR" BEYIN_DURUM="$BEYIN_STATE_DIR" \
  python3 "$BEYIN_HOOK_DIR/proje-yonerge.py" "$BEYIN_GIRDI" 2>/dev/null || :)
rm -f "$BEYIN_GIRDI" 2>/dev/null || :

[ -n "$BEYIN_METIN" ] && beyin_emit UserPromptSubmit "$BEYIN_METIN"
exit 0
