"""Text injector: inserts recognized text into a specific terminal window.

Strategy:
  1. xdotool type --window <WID>  (primary — works with gnome-terminal)
  2. Clipboard + Ctrl+Shift+V     (fallback)
"""

import os
import subprocess
import shutil
import time

from config import ENTER_TRIGGER_WORDS


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def get_active_window_id() -> str | None:
    """Return the X11 window ID of the currently focused window."""
    if not _has("xdotool"):
        return None
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, check=True,
        )
        wid = result.stdout.strip()
        print(f"[voice-input] captured window_id={wid}", flush=True)
        return wid
    except subprocess.CalledProcessError as e:
        print(f"[voice-input] getactivewindow failed: {e}", flush=True)
        return None


def inject(text: str, window_id: str | None = None) -> bool:
    """
    Inject *text* into *window_id*.

    Returns True if text was injected, False if a code word triggered Enter.
    Raises RuntimeError if xdotool is missing.
    """
    if not _has("xdotool"):
        raise RuntimeError("xdotool not installed. Run: sudo apt install xdotool")

    normalized = text.strip().lower().rstrip(".,!?")

    # Full text is a trigger word
    if normalized in ENTER_TRIGGER_WORDS:
        _send_key("Return", window_id)
        return False

    # Last word is a trigger (e.g. "list files, enter")
    last_word = normalized.split()[-1].rstrip(".,!?") if normalized.split() else ""
    if last_word in ENTER_TRIGGER_WORDS:
        # Type everything before the trigger word, then press Enter
        prefix = text.strip()
        # Strip the trigger word from end
        idx = prefix.lower().rfind(last_word)
        if idx > 0:
            prefix = prefix[:idx].rstrip(" ,.")
            _type_text(prefix, window_id)
        _send_key("Return", window_id)
        return False

    _type_text(text.strip(), window_id)
    return True


def _type_text(text: str, window_id: str | None) -> None:
    # Method 1: xdotool type with window focus
    if window_id:
        try:
            # Focus the window first, then type
            subprocess.run(
                ["xdotool", "windowfocus", "--sync", window_id],
                check=True, capture_output=True,
            )
            time.sleep(0.1)
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "20", "--", text],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"[voice-input] injected via xdotool type into {window_id}", flush=True)
                return
            else:
                print(f"[voice-input] xdotool type error: {result.stderr}", flush=True)
        except subprocess.CalledProcessError as e:
            print(f"[voice-input] xdotool windowfocus failed: {e}", flush=True)

    # Method 2: clipboard + Ctrl+Shift+V
    if _has("xclip") and window_id:
        try:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text, text=True, check=True,
            )
            time.sleep(0.05)
            subprocess.run(
                ["xdotool", "key", "--window", window_id, "ctrl+shift+v"],
                check=True,
            )
            print(f"[voice-input] injected via clipboard+paste into {window_id}", flush=True)
            return
        except subprocess.CalledProcessError as e:
            print(f"[voice-input] clipboard method failed: {e}", flush=True)

    print("[voice-input] all injection methods failed", flush=True)


def _send_key(key: str, window_id: str | None) -> None:
    try:
        if window_id:
            subprocess.run(
                ["xdotool", "windowfocus", "--sync", window_id],
                check=True, capture_output=True,
            )
            time.sleep(0.1)
        cmd = ["xdotool", "key", "--clearmodifiers"]
        if window_id:
            cmd += ["--window", window_id]
        cmd.append(key)
        subprocess.run(cmd, check=True)
        print(f"[voice-input] sent key {key} to {window_id}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[voice-input] send_key failed: {e}", flush=True)
