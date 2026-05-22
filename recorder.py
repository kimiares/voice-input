"""Audio recorder: captures microphone input while PTT key is held."""

import threading
import wave
import tempfile
import os
from typing import Optional

import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE


class Recorder:
    def __init__(self) -> None:
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True

        def callback(indata: np.ndarray, frames: int, time, status) -> None:
            if self._recording:
                self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> Optional[str]:
        """Stop recording and return path to a temporary WAV file, or None if no audio."""
        with self._lock:
            if not self._recording:
                return None
            self._recording = False

        self._stream.stop()
        self._stream.close()

        if not self._frames:
            return None

        audio = np.concatenate(self._frames, axis=0)

        # Ignore very short recordings (< 0.3 s) — likely accidental key press
        if len(audio) < SAMPLE_RATE * 0.3:
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        _write_wav(tmp.name, audio, SAMPLE_RATE)
        return tmp.name


def _write_wav(path: str, audio: np.ndarray, rate: int) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(rate)
        wf.writeframes(audio.tobytes())
