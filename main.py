#!/usr/bin/env python3
"""
voice-input — Push-to-Talk voice input daemon for the terminal.

Usage:
  python main.py

Hold the PTT key (default: Right Alt) to record.
Release to transcribe and inject the text into the active terminal.
Say a code word (e.g. "отправь" / "enter") to send Enter instead.
"""

import os
import sys
import tempfile
import time
import threading
import subprocess
import shutil

from pynput import keyboard

from config import PTT_KEY, SHOW_FEEDBACK
from recorder import Recorder
from stt import transcribe
from injector import inject, get_active_window_id


# ---------------------------------------------------------------------------
# Copilot window monitor
# ---------------------------------------------------------------------------
def _can_monitor_windows() -> bool:
    return bool(shutil.which("wmctrl") or shutil.which("xdotool"))


def _copilot_window_exists() -> bool:
    """Return True if a window with 'copilot' in its title exists.
    Falls back between wmctrl and xdotool. If neither available, returns True
    to avoid accidentally exiting the daemon.
    """
    try:
        if shutil.which("wmctrl"):
            r = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            return "copilot" in r.stdout.lower()
        if shutil.which("xdotool"):
            r = subprocess.run(["xdotool", "search", "--name", "copilot"], capture_output=True, text=True)
            return bool(r.stdout.strip())
    except Exception as e:
        print(f"[voice-input] window check failed: {e}", flush=True)
    # If cannot determine, assume it's present
    return True


def _monitor_copilot_and_exit(poll_interval: float = 2.0) -> None:
    if not _can_monitor_windows():
        print("[voice-input] wmctrl/xdotool not found — skipping Copilot window monitor", flush=True)
        return
    while True:
        try:
            if not _copilot_window_exists():
                print("[voice-input] Copilot window not found — exiting.", flush=True)
                # Immediate process exit
                os._exit(0)
        except Exception as e:
            print(f"[voice-input] monitor error: {e}", flush=True)
        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

recorder = Recorder()
_ptt_active = False
_target_window: str | None = None  # window ID captured at PTT press

# Muted flag file path (created by run.sh mute/unmute)
MUTED_FILE = os.path.join(os.path.dirname(__file__), ".muted")

def is_muted() -> bool:
    return os.path.exists(MUTED_FILE)


# ---------------------------------------------------------------------------
# Keyboard listener callbacks
# ---------------------------------------------------------------------------

def on_press(key) -> None:
    global _ptt_active, _target_window
    if key == PTT_KEY and not _ptt_active:
        if is_muted():
            print("\r🔇 Muted — ignoring PTT", flush=True)
            return
        _ptt_active = True
        _target_window = get_active_window_id()  # remember focused window
        _on_ptt_start()


def on_release(key) -> None:
    global _ptt_active
    if key == PTT_KEY and _ptt_active:
        _ptt_active = False
        _on_ptt_stop()


# ---------------------------------------------------------------------------
# PTT handlers
# ---------------------------------------------------------------------------

def _on_ptt_start() -> None:
    print("\r🎙️  Recording…  ", end="", flush=True)
    recorder.start()


def _on_ptt_stop() -> None:
    wav_path = recorder.stop()

    if wav_path is None:
        print("\r⚠️  Too short, ignored.       ", flush=True)
        return

    print("\r🔄  Transcribing…", end="", flush=True)

    try:
        text = transcribe(wav_path)
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    if not text:
        print("\r⚠️  Nothing recognized.       ", flush=True)
        return

    if SHOW_FEEDBACK:
        print(f'\r📝  "{text}"          ', flush=True)

    try:
        sent_text = inject(text, window_id=_target_window)
        if not sent_text:
            print(f"\r⏎  Code word detected → Enter", flush=True)
    except Exception as exc:
        print(f"\r❌  inject error: {exc}", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"🎤 voice-input started. Hold [{_key_name(PTT_KEY)}] to speak.")
    if is_muted():
        print("   🔇 Currently muted — PTT is disabled.")
    print(f"   Code words for Enter: see config.py → ENTER_TRIGGER_WORDS")
    print(f"   Ctrl+C to quit.\n")

    # Start background monitor that exits when Copilot window closes
    monitor_thread = threading.Thread(target=_monitor_copilot_and_exit, daemon=True)
    monitor_thread.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\n👋 Stopped.")


def _key_name(key) -> str:
    try:
        return key.name
    except AttributeError:
        return str(key)


if __name__ == "__main__":
    main()
