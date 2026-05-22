# voice-input

Push-to-Talk voice input daemon for Linux terminals.

Features:
- Hold a PTT key (Right Alt by default) to record
- Release to transcribe with faster-whisper (small.en) and inject into active terminal
- Say a trigger word (e.g. "enter") to send Enter instead of text

Quick start (after cloning or unpacking):

1. Edit `config.py` if needed (model paths, enter trigger words)
2. Run installer:

```bash
./install.sh --no-service
```

3. (Optional) to download models automatically:

```bash
./install.sh --no-service --download-models
```

4. Start daemon:

```bash
./run.sh start
```

5. Stop daemon:

```bash
./run.sh stop
```

Troubleshooting:
- Ensure `xdotool` and `xclip` are installed
- If using Vosk, download a Vosk model and set `VOSK_MODEL_PATH` in `config.py`

Packaging and transferring:
- Use `./pack.sh` to create a tar.gz archive (it will include the agent file if present and exclude `.venv/`)
- On target machine: extract, run `./install.sh --no-service --download-models` and then `./run.sh start`

Release notes & detailed installation guide:
https://github.com/kimiares/voice-input/releases/tag/v1.1

Краткое руководство на русском:
Этот проект предоставляет демон голосового ввода (PTT) для Linux-терминалов. Зажмите Right Alt, говорите, отпустите — распознанный текст будет вставлен в активную консоль. Скажите одно из кодовых слов (например, "enter", "run") чтобы отправить Enter.

Инструкция по установке и упаковке — см. релизные заметки и README выше.
