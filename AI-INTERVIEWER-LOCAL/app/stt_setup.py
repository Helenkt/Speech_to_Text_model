from __future__ import annotations

import sys

from app.config import Settings
from app.services.speech_to_text import verify_stt_setup


def main() -> int:
    settings = Settings.from_env()
    print(
        f"STT: dang tai/kiem tra Whisper '{settings.whisper_model}' "
        f"({settings.whisper_device}, {settings.whisper_compute_type})...",
        flush=True,
    )
    try:
        result = verify_stt_setup(settings)
    except Exception as exc:
        print("\nSTT CHUA SAN SANG.", file=sys.stderr)
        print(f"Chi tiet: {exc}", file=sys.stderr)
        print(
            "Hay kiem tra Internet va Microsoft Visual C++ Redistributable x64, "
            "sau do chay lai: python -m app.stt_setup",
            file=sys.stderr,
        )
        print(
            "Huong dan Visual C++: https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist",
            file=sys.stderr,
        )
        return 1

    print(
        f"STT san sang: {result['model']} / {result['device']} / "
        f"{result['compute_type']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
