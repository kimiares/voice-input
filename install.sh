#!/usr/bin/env bash
# install.sh — Set up voice-input PTT daemon
# Usage: ./install.sh [--no-service] [--vosk]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
INSTALL_SERVICE=true
USE_VOSK=false
DOWNLOAD_MODELS=false
VENV_DIR="$SCRIPT_DIR/.venv"

# --- Parse args ---
for arg in "$@"; do
  case "$arg" in
    --no-service) INSTALL_SERVICE=false ;;
    --vosk)       USE_VOSK=true ;;
    --download-models) DOWNLOAD_MODELS=true ;;
    --help|-h)
      echo "Usage: $0 [--no-service] [--vosk] [--download-models]"
      echo "  --no-service       Skip systemd user service installation"
      echo "  --vosk             Install Vosk instead of Whisper (lighter, faster)"
      echo "  --download-models  Attempt to download STT models after installing Python packages"
      exit 0 ;;
  esac
done

# --- Colors ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; exit 1; }

echo "=============================="
echo "  voice-input installer"
echo "=============================="
echo ""

# --- Check Python ---
if ! command -v "$PYTHON" &>/dev/null; then
  err "Python3 not found. Install with: sudo apt install python3"
fi
PY_VER=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PY_VER  ($("$PYTHON" -c 'import sys; print(sys.executable)'))"

# --- System packages ---
echo ""
echo "[1/4] Installing system packages..."
MISSING_PKGS=()
for pkg in xdotool xclip portaudio19-dev python3-venv python3-dev; do
  dpkg -s "$pkg" &>/dev/null || MISSING_PKGS+=("$pkg")
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  echo "  Installing: ${MISSING_PKGS[*]}"
  sudo apt-get update -qq
  sudo apt-get install -y "${MISSING_PKGS[@]}"
  ok "System packages installed."
else
  ok "System packages already present."
fi

# --- Virtual environment ---
echo ""
echo "[2/4] Setting up Python virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
  ok "Virtual environment created at $VENV_DIR"
else
  ok "Virtual environment already exists."
fi
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# --- Python packages ---
echo ""
echo "[3/4] Installing Python packages..."
"$VENV_PIP" install --upgrade pip -q

if [[ "$USE_VOSK" == "true" ]]; then
  warn "Using Vosk backend. Remember to set STT_BACKEND = 'vosk' and VOSK_MODEL_PATH in config.py"
  warn "Download model from: https://alphacephei.com/vosk/models  (e.g. vosk-model-ru-0.42)"
  "$VENV_PIP" install sounddevice pynput numpy vosk
else
  # Install faster-whisper to enable faster on-CPU inference and model download helper
  "$VENV_PIP" install sounddevice pynput numpy pywhispercpp faster-whisper || "$VENV_PIP" install sounddevice pynput numpy pywhispercpp
fi
ok "Python packages installed."

# Optional: download models into cache (faster-whisper will populate HF cache)
if [[ "$DOWNLOAD_MODELS" == "true" ]]; then
  echo ""
  echo "[3.5] Downloading STT models..."
  if [[ "$USE_VOSK" == "true" ]]; then
    # Download and extract vosk-model-small-en-us-0.15 to ~/vosk-models/
    VOSK_DIR="$HOME/vosk-models"
    VOSK_MODEL_NAME="vosk-model-small-en-us-0.15"
    VOSK_URL="https://alphacephei.com/vosk/models/$VOSK_MODEL_NAME.zip"

    mkdir -p "$VOSK_DIR"
    echo "Downloading $VOSK_MODEL_NAME into $VOSK_DIR (may take a minute)..."
    TMPZIP="$VOSK_DIR/$VOSK_MODEL_NAME.zip"
    if command -v curl &>/dev/null; then
      curl -L "$VOSK_URL" -o "$TMPZIP"
    elif command -v wget &>/dev/null; then
      wget -O "$TMPZIP" "$VOSK_URL"
    else
      warn "curl/wget not found — cannot download Vosk model automatically. Please download manually: $VOSK_URL"
    fi

    if [[ -f "$TMPZIP" ]]; then
      echo "Unpacking..."
      unzip -o "$TMPZIP" -d "$VOSK_DIR" >/dev/null || true
      rm -f "$TMPZIP"
      ok "Vosk model downloaded to $VOSK_DIR/$VOSK_MODEL_NAME"
      echo "Add or update VOSK_MODEL_PATH in config.py to: $VOSK_DIR/$VOSK_MODEL_NAME"
    else
      warn "Vosk model zip not found, skipped."
    fi
  else
    echo "Downloading faster-whisper model 'small.en' into HuggingFace cache (may take several minutes)..."
    "$VENV_PYTHON" - <<PY
from faster_whisper import WhisperModel
print('Instantiating faster-whisper model small.en (will download to cache)')
WhisperModel('small.en', device='cpu', compute_type='int8')
print('Model download (or cache check) finished')
PY
    ok "Model download step finished."
  fi
fi

# --- Launcher script ---
echo ""
LAUNCHER="$SCRIPT_DIR/run.sh"
cat > "$LAUNCHER" <<LAUNCHER
#!/usr/bin/env bash
# Auto-generated launcher — activates venv and starts voice-input
source "$VENV_DIR/bin/activate"
exec python "$SCRIPT_DIR/main.py" "\$@"
LAUNCHER
chmod +x "$LAUNCHER"
ok "Launcher created: $LAUNCHER"

# --- systemd user service ---
echo ""
echo "[4/4] systemd user service..."
if [[ "$INSTALL_SERVICE" == "false" ]]; then
  warn "Skipped (--no-service). Run manually: $LAUNCHER"
else
  SERVICE_DIR="$HOME/.config/systemd/user"
  SERVICE_FILE="$SERVICE_DIR/voice-input.service"
  mkdir -p "$SERVICE_DIR"

  cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=Voice Input PTT Daemon
After=graphical-session.target
PartOf=graphical-session.target

[Service]
ExecStart=$LAUNCHER
Restart=on-failure
RestartSec=3
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
SERVICE

  systemctl --user daemon-reload
  systemctl --user enable voice-input.service
  ok "Service installed: $SERVICE_FILE"
  echo ""
  echo "  Start now:   systemctl --user start voice-input"
  echo "  Stop:        systemctl --user stop voice-input"
  echo "  Status/logs: systemctl --user status voice-input"
  echo "  Live logs:   journalctl --user -u voice-input -f"
fi

echo ""
echo "=============================="
ok "Installation complete!"
echo "=============================="
echo ""
echo "  Run directly: $LAUNCHER"
if [[ "$USE_VOSK" == "false" ]]; then
  echo "  Note: Whisper 'base' model (~150 MB) will download on first run."
fi
