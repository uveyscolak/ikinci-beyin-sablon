#!/bin/bash
[ -n "${BEYIN_INVOKED_BY:-}" ] && exit 0
# Detach a pre-compaction flush without changing live session state.

BEYIN_HOOK_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
. "$BEYIN_HOOK_DIR/lib.sh" 2>/dev/null || exit 0

BEYIN_HOOK_INPUT="$BEYIN_STATE_DIR/hookin-$$.json"
umask 077
if ! cat > "$BEYIN_HOOK_INPUT" 2>/dev/null; then
  rm -f "$BEYIN_HOOK_INPUT" 2>/dev/null || :
  BEYIN_HOOK_INPUT=""
fi

if [ -n "$BEYIN_HOOK_INPUT" ]; then
  # Proje ve alan blokları oturumda bir kez enjekte ediliyor, izi oturum kimliğinin
  # sha256'sına bağlı bir dosyada duruyor. Bağlam özetlenince kimlik değişmiyor, iz
  # kalıyor ve blok o oturumda bir daha hiç gelmiyordu. İz burada silinir; konu tekrar
  # geçince blok yeniden gelir. Hash hesabı proje-yonerge.py ile birebir aynıdır.
  if command -v python3 >/dev/null 2>&1; then
    BEYIN_SESSION_KEY=$(beyin_session_key < "$BEYIN_HOOK_INPUT" 2>/dev/null || :)
    if [ -n "$BEYIN_SESSION_KEY" ]; then
      rm -f "$BEYIN_STATE_DIR/yonerge-verilen.$BEYIN_SESSION_KEY" 2>/dev/null || :
    fi
  fi

  if command -v python3 >/dev/null 2>&1; then
    nohup python3 "$BEYIN_PROJECT_DIR/.claude/scripts/flush.py" \
      --hook-input "$BEYIN_HOOK_INPUT" --reason precompact >/dev/null 2>&1 &
  else
    beyin_mark_python_missing
    rm -f "$BEYIN_HOOK_INPUT" 2>/dev/null || :
    beyin_emit PreCompact 'Beyin sıkıştırma öncesi özeti başlatılamadı: python3 bulunamadı. beyin-doktor çalıştır.'
  fi
fi
exit 0
