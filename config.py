"""Configuration for voice-input PTT daemon."""

from pynput.keyboard import Key

# Push-to-Talk key (hold to record)
PTT_KEY = Key.alt_r  # Right Alt

# STT backend: "whisper" | "faster-whisper" | "vosk"
STT_BACKEND = "faster-whisper"

# Whisper model size: "tiny", "base", "small", "medium", "large-v3-turbo"
# small.en ~465 MB — English-only model, faster and more accurate for English
# large-v3-turbo ~800 MB — best quality
WHISPER_MODEL = "small.en"

# Initial prompt — helps Whisper stay in English and understand terminal context
WHISPER_INITIAL_PROMPT = "The user is typing a terminal command in English."

# Vosk model path (only used if STT_BACKEND = "vosk")
VOSK_MODEL_PATH = "/home/constantine/vosk-models/vosk-model-small-en-us-0.15"

# Recognition language hint (used by Whisper)
LANGUAGE = "en"

# Code words that trigger Enter instead of inserting text.
# After detecting one of these, Enter is sent to the terminal.
ENTER_TRIGGER_WORDS = {
    "submit", "enter", "run", "go", "send", "execute", "confirm",
}

# Silence threshold in seconds — stop recording if silent for this long
# (for future VAD / auto-stop feature, not used in PTT mode)
SILENCE_TIMEOUT = 2.0

# Sample rate for audio recording (Hz)
SAMPLE_RATE = 16000

# Visual feedback: show recorded text in terminal before injecting
SHOW_FEEDBACK = True
