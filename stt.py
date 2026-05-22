"""Speech-to-Text abstraction: supports whisper.cpp (pywhispercpp) and Vosk."""

import os
from typing import Optional

from config import STT_BACKEND, WHISPER_MODEL, VOSK_MODEL_PATH, LANGUAGE, WHISPER_INITIAL_PROMPT

# ---------------------------------------------------------------------------
# Lazy-loaded backends
# ---------------------------------------------------------------------------

_whisper_model = None
_faster_whisper_model = None
_vosk_recognizer = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            from pywhispercpp.model import Model
            _whisper_model = Model(
                WHISPER_MODEL,
                language=LANGUAGE,
                redirect_whispercpp_logs_to=None,
                params_sampling_strategy=1,
                no_speech_thold=0.6,
                logprob_thold=-1.0,
            )
        except ImportError:
            raise RuntimeError(
                "pywhispercpp is not installed. Run: pip install pywhispercpp"
            )
    return _whisper_model


def _get_faster_whisper():
    global _faster_whisper_model
    if _faster_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print(f"[voice-input] Loading faster-whisper model '{WHISPER_MODEL}'...")
            _faster_whisper_model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",  # quantized: fastest on CPU, ~same accuracy
            )
            print("[voice-input] Model loaded.")
        except ImportError:
            raise RuntimeError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            )
    return _faster_whisper_model


def _get_vosk():
    global _vosk_recognizer
    if _vosk_recognizer is None:
        try:
            from vosk import Model, KaldiRecognizer
            import json
            if not os.path.isdir(VOSK_MODEL_PATH):
                raise RuntimeError(
                    f"Vosk model not found at {VOSK_MODEL_PATH}. "
                    "Download from https://alphacephei.com/vosk/models"
                )
            model = Model(VOSK_MODEL_PATH)
            _vosk_recognizer = (KaldiRecognizer, model, json)
        except ImportError:
            raise RuntimeError(
                "vosk is not installed. Run: pip install vosk"
            )
    return _vosk_recognizer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe(wav_path: str) -> Optional[str]:
    """Transcribe a WAV file and return the recognized text, or None on failure."""
    try:
        if STT_BACKEND == "whisper":
            return _transcribe_whisper(wav_path)
        elif STT_BACKEND == "faster-whisper":
            return _transcribe_faster_whisper(wav_path)
        elif STT_BACKEND == "vosk":
            return _transcribe_vosk(wav_path)
        else:
            raise ValueError(f"Unknown STT_BACKEND: {STT_BACKEND!r}")
    except Exception as exc:
        print(f"[voice-input] STT error: {exc}")
        return None


def _transcribe_whisper(wav_path: str) -> Optional[str]:
    model = _get_whisper()
    segments = model.transcribe(
        wav_path,
        initial_prompt=WHISPER_INITIAL_PROMPT,
        temperature=0.0,
        suppress_blank=True,
    )
    text = " ".join(s.text for s in segments).strip()
    junk = {"[music]", "[applause]", "[silence]", "..."}
    if text.lower().strip("[]()") in {j.lower().strip("[]()") for j in junk}:
        return None
    return text or None


def _transcribe_faster_whisper(wav_path: str) -> Optional[str]:
    model = _get_faster_whisper()
    segments, info = model.transcribe(
        wav_path,
        language=LANGUAGE,
        initial_prompt=WHISPER_INITIAL_PROMPT,
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        vad_filter=True,           # skip silent segments
        vad_parameters=dict(min_silence_duration_ms=300),
    )
    text = " ".join(s.text for s in segments).strip()
    return text or None


def _transcribe_vosk(wav_path: str) -> Optional[str]:
    import wave
    KaldiRecognizer, vosk_model, json = _get_vosk()

    with wave.open(wav_path, "rb") as wf:
        rate = wf.getframerate()
        rec = KaldiRecognizer(vosk_model, rate)
        result_parts = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                result_parts.append(res.get("text", ""))
        final = json.loads(rec.FinalResult())
        result_parts.append(final.get("text", ""))

    text = " ".join(p for p in result_parts if p).strip()
    return text or None
