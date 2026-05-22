#!/usr/bin/env bash
# pack.sh — create a portable archive of the voice-input project (excludes .venv and large models)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_NAME="voice-input-package-$(date +%Y%m%d%H%M%S).tar.gz"
TMP_DIR="${SCRIPT_DIR}/.pack_tmp"
AGENT_FILE="$HOME/.copilot/agents/voice-input.agent.md"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/voice-input"

# Copy project files (exclude .venv and large models)
rsync -av --exclude ".venv" --exclude "*.log" --exclude "*.pid" --exclude "__pycache__" --exclude "*.pyc" \
  "$SCRIPT_DIR/" "$TMP_DIR/voice-input/" >/dev/null

# Include agent file if present
if [[ -f "$AGENT_FILE" ]]; then
  mkdir -p "$TMP_DIR/agent"
  cp "$AGENT_FILE" "$TMP_DIR/agent/"
fi

# Remove any model files if accidentally copied
find "$TMP_DIR" -name "ggml-*.bin" -delete || true
find "$TMP_DIR" -name "*.onnx" -delete || true

# Pack
pushd "$TMP_DIR" >/dev/null
tar -czf "$SCRIPT_DIR/$OUT_NAME" .
popd >/dev/null

# Clean
rm -rf "$TMP_DIR"

echo "Created package: $SCRIPT_DIR/$OUT_NAME"
