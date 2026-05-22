#!/usr/bin/env bash
# run.sh — starts voice-input daemon in background (no terminal window)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/voice-input.log"
PID_FILE="$SCRIPT_DIR/voice-input.pid"

case "${1:-start}" in
  start)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Already running (PID $(cat "$PID_FILE")). Use: $0 stop"
      exit 0
    fi
    source "$SCRIPT_DIR/.venv/bin/activate"
    nohup python -u "$SCRIPT_DIR/main.py" > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ voice-input started (PID $!)"
    echo "   Logs: tail -f $LOG"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]]; then
      kill "$(cat "$PID_FILE")" 2>/dev/null && echo "⏹  Stopped." || echo "Not running."
      rm -f "$PID_FILE"
    else
      echo "Not running."
    fi
    ;;
  status)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "🟢 Running (PID $(cat "$PID_FILE"))"
      echo "--- last 10 log lines ---"
      tail -10 "$LOG" 2>/dev/null
    else
      echo "🔴 Not running"
    fi
    ;;
  log)
    tail -f "$LOG"
    ;;
  *)
    echo "Usage: $0 {start|stop|status|log}"
    ;;
esac
