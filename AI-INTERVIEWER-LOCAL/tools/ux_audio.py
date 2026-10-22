"""Prepare a documented synthetic input for browser microphone testing."""
import argparse
import json
import os
import subprocess
import wave
from pathlib import Path

import av

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--source", type=Path)
args = parser.parse_args()
temporary = Path(os.environ["UX_REAL_ROOT"]).resolve()
output = args.output.resolve()
if not temporary.is_relative_to(root) or not temporary.name.startswith(".pytest-quality-ui-ux-") or not output.is_relative_to(temporary):
    raise RuntimeError("Audio output must be inside the isolated UX fixture")
source = args.source
if not source:
    source = output.with_suffix(".sapi.wav")
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "tools/ux_tts.ps1")],
        env={**os.environ, "UX_TTS_OUTPUT": str(source)}, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
chunks = []
with av.open(str(source)) as container:
    for frame in container.decode(audio=0):
        chunks.extend(item.to_ndarray().tobytes() for item in resampler.resample(frame))
    chunks.extend(item.to_ndarray().tobytes() for item in resampler.resample(None))
audio = b"".join(chunks)
with wave.open(str(output), "wb") as handle:
    handle.setnchannels(1)
    handle.setsampwidth(2)
    handle.setframerate(48000)
    handle.writeframes(b"\0\0" * 48000 * 3 + audio + b"\0\0" * 24000)
print(json.dumps({"seconds": len(audio) / 96000 + 3.5, "synthetic": not bool(args.source)}))
