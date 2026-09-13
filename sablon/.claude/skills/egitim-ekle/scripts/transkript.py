"""Komut satırından toplu transkript — Widdownder'ın gömülü Whisper motoruyla birebir aynı ayarlar.

Yorumlayıcı zorunlu: pywhispercpp'nin kurulu olduğu venv'in python'ı (Widdownder projesinin venv'i;
SKILL.md içinde tam yol tarif edilir).

Kullanım:
    <venv>/bin/python transkript.py <video1> [<video2> ...]

Her video için yanına aynı adla .txt yazar; .txt zaten varsa ve boş değilse atlar.
"""

import subprocess
import sys
import time
from pathlib import Path

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
MODEL_PATH = Path.home() / "Library" / "Application Support" / "Widdownder" / "models" / "ggml-large-v3-turbo-q8_0.bin"
TMP_DIR = Path("/tmp/egitim-ekle-transkript")

_model = None


def get_model():
    global _model
    if _model is None:
        from pywhispercpp.model import Model

        _model = Model(
            str(MODEL_PATH),
            print_progress=False,
            print_realtime=False,
            redirect_whispercpp_logs_to=None,
        )
    return _model


def ses_suresi(path: Path) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def fmt_sure(saniye: float) -> str:
    s = int(saniye)
    return f"{s // 60}:{s % 60:02d}"


def transkript_cikar(video_path: Path) -> str:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = TMP_DIR / (video_path.stem + ".wav")
    subprocess.run(
        [FFMPEG, "-i", str(video_path), "-ac", "1", "-ar", "16000", str(wav_path), "-y"],
        check=True,
        capture_output=True,
    )
    try:
        model = get_model()
        segments = model.transcribe(str(wav_path), language="tr")
        return "\n".join(s.text.strip() for s in segments if s.text.strip())
    finally:
        wav_path.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 2:
        print("Kullanım: transkript.py <video1> [<video2> ...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        video_path = Path(arg)
        txt_path = video_path.with_suffix(".txt")

        if txt_path.exists() and txt_path.stat().st_size > 0:
            print(f"{video_path.name}: atlandı (txt zaten var)")
            continue

        sure = ses_suresi(video_path)
        baslangic = time.monotonic()
        metin = transkript_cikar(video_path)
        gecen = time.monotonic() - baslangic

        txt_path.write_text(metin, encoding="utf-8")

        print(
            f"{video_path.name}: süre {fmt_sure(sure)} · geçen {fmt_sure(gecen)} · "
            f"{len(metin)} karakter"
        )


if __name__ == "__main__":
    main()
