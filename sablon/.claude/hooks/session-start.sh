#!/bin/bash
[ -n "${BEYIN_INVOKED_BY:-}" ] && exit 0
# Oturum başı: hafızayı bağlama koy (session-start.py), sonra arka planda telafi ve push.

BEYIN_HOOK_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)
. "$BEYIN_HOOK_DIR/lib.sh" 2>/dev/null || exit 0

mkdir -p "$BEYIN_STATE_DIR" 2>/dev/null || :
beyin_cleanup_session_state

BEYIN_SESSION_KEY=$(beyin_session_key 2>/dev/null || :)
if [ -n "$BEYIN_SESSION_KEY" ]; then
  date '+%s' > "$BEYIN_STATE_DIR/session_start_time.$BEYIN_SESSION_KEY" 2>/dev/null || :
  printf '%s\n' 0 > "$BEYIN_STATE_DIR/prompt_count.$BEYIN_SESSION_KEY" 2>/dev/null || :
fi

if command -v python3 >/dev/null 2>&1; then
  # Hızlı sağlık kontrolü (yarım saniye): sonuç .state/saglik.json'a, sorun varsa bağlama düşer.
  python3 "$BEYIN_PROJECT_DIR/.claude/scripts/saglik.py" --yaz >/dev/null 2>&1 || :
  python3 "$BEYIN_HOOK_DIR/session-start.py" "$BEYIN_PROJECT_DIR" 2>/dev/null || :
else
  beyin_mark_python_missing
  beyin_emit SessionStart 'Beyin uyarısı: python3 bulunamadı, hafıza enjekte edilemedi. beyin doktor çalıştır.'
fi

# Gecikmiş derleme (18:00 öncesi kapanan günler) ve kaçan oturum özetleri, ayrık süreçte.
if command -v python3 >/dev/null 2>&1; then
  nohup python3 "$BEYIN_PROJECT_DIR/.claude/scripts/flush.py" --maybe-compile >/dev/null 2>&1 &
  nohup python3 "$BEYIN_PROJECT_DIR/.claude/scripts/flush-catchup.py" \
    --current-key "$BEYIN_SESSION_KEY" >/dev/null 2>&1 &
fi

# Önceki oturumdan push edilmemiş commit varsa arka planda gönder.
if git -C "$BEYIN_PROJECT_DIR" remote get-url origin >/dev/null 2>&1; then
  nohup git -C "$BEYIN_PROJECT_DIR" push -q origin HEAD >/dev/null 2>&1 &
fi
exit 0
