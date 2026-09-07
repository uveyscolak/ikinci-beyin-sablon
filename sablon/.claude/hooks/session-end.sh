#!/bin/bash
[ -n "${BEYIN_INVOKED_BY:-}" ] && exit 0
# Oturum sonu: vault'un tamamını commit'le, özeti (flush.py) çalıştır, push et. Hepsi ayrık.

BEYIN_HOOK_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
. "$BEYIN_HOOK_DIR/lib.sh" 2>/dev/null || exit 0

BEYIN_HOOK_INPUT="$BEYIN_STATE_DIR/hookin-$$.json"
umask 077
if ! cat > "$BEYIN_HOOK_INPUT" 2>/dev/null; then
  rm -f "$BEYIN_HOOK_INPUT" 2>/dev/null || :
  BEYIN_HOOK_INPUT=""
fi

BEYIN_SESSION_KEY=""
[ -n "$BEYIN_HOOK_INPUT" ] && BEYIN_SESSION_KEY=$(beyin_session_key < "$BEYIN_HOOK_INPUT" 2>/dev/null || :)

BEYIN_START=0
if [ -n "$BEYIN_SESSION_KEY" ]; then
  BEYIN_SESSION_START_FILE="$BEYIN_STATE_DIR/session_start_time.$BEYIN_SESSION_KEY"
  BEYIN_PROMPT_COUNT_FILE="$BEYIN_STATE_DIR/prompt_count.$BEYIN_SESSION_KEY"
  [ -f "$BEYIN_SESSION_START_FILE" ] && BEYIN_START=$(sed -n '1p' "$BEYIN_SESSION_START_FILE" 2>/dev/null || :)
  rm -f "$BEYIN_SESSION_START_FILE" "$BEYIN_PROMPT_COUNT_FILE" 2>/dev/null || :
fi
case "$BEYIN_START" in ''|*[!0-9]*) BEYIN_START=0 ;; esac

BEYIN_DAMGA=$(date '+%Y-%m-%d %H:%M' 2>/dev/null)
BEYIN_FLUSH=""
if [ -n "$BEYIN_HOOK_INPUT" ]; then
  if command -v python3 >/dev/null 2>&1; then
    BEYIN_FLUSH="python3 '$BEYIN_PROJECT_DIR/.claude/scripts/flush.py' --hook-input '$BEYIN_HOOK_INPUT' --session-start '$BEYIN_START'"
  else
    beyin_mark_python_missing
    rm -f "$BEYIN_HOOK_INPUT" 2>/dev/null || :
    beyin_emit SessionEnd 'Beyin arka plan özeti başlatılamadı: python3 bulunamadı. beyin doktor çalıştır.'
  fi
fi

# Sıra: önce kök index'i üret (commit'e girsin), sonra anlık görüntü (vault'un tamamı),
# sonra özet (kendi dosyasını commit'ler), sonra push.
nohup bash -c "
  cd '$BEYIN_PROJECT_DIR' || exit 0
  python3 '$BEYIN_PROJECT_DIR/.claude/scripts/index-uret.py' >/dev/null 2>&1 || :
  git add -A >/dev/null 2>&1 && git commit -q -m 'oturum: $BEYIN_DAMGA' >/dev/null 2>&1
  $BEYIN_FLUSH
  git remote get-url origin >/dev/null 2>&1 && git push -q origin HEAD >/dev/null 2>&1
" >/dev/null 2>&1 &
exit 0
