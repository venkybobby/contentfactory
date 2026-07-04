from __future__ import annotations

import base64
import json
import math
import os
import platform
import shutil
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    candidates = [Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/segoeui.ttf")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _wrapped(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def scene_cards(sections: list[dict], output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    for index, section in enumerate(sections, 1):
        image = Image.new("RGB", (1920, 1080), (5, 12, 23))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 28, 1080), fill=(24, 161, 173))
        draw.text((100, 95), "THE AI CONFESSION", font=_font(30), fill=(126, 226, 232))
        draw.text((100, 205), section["section"].upper(), font=_font(68), fill="white")
        y = 350
        for line in _wrapped(draw, section["narration"], _font(42), 1650)[:7]:
            draw.text((100, y), line, font=_font(42), fill=(210, 218, 230))
            y += 62
        draw.text((100, 980), f"CASE FILE  •  SCENE {index:02}", font=_font(26), fill=(120, 135, 155))
        path = output / f"scene_{index:02}.png"
        image.save(path)
        cards.append(path)
    return cards


def synthesize_voice(text: str, output: Path) -> None:
    if platform.system() != "Windows":
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        if not espeak:
            raise RuntimeError("A speech engine is required: install espeak-ng")
        subprocess.run([espeak, "-v", "en-us", "-s", "145", "-w", str(output), text],
                       check=True, capture_output=True)
        return
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    safe_path = str(output.resolve()).replace("'", "''")
    script = ("Add-Type -AssemblyName System.Speech; "
              "$s=[System.Speech.Synthesis.SpeechSynthesizer]::new(); "
              "$s.SelectVoice('Microsoft David Desktop'); $s.Rate=-1; "
              f"$s.SetOutputToWaveFile('{safe_path}'); "
              f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}')); "
              "$s.Speak($t); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def subtitles(sections: list[dict], duration: float, output: Path) -> None:
    slice_seconds = duration / len(sections)
    def stamp(value: float) -> str:
        ms = int((value - int(value)) * 1000)
        value = int(value)
        return f"{value // 3600:02}:{(value % 3600) // 60:02}:{value % 60:02},{ms:03}"
    blocks = []
    for index, section in enumerate(sections, 1):
        blocks.append(f"{index}\n{stamp((index-1)*slice_seconds)} --> {stamp(index*slice_seconds)}\n{section['narration']}\n")
    output.write_text("\n".join(blocks), encoding="utf-8")


def render_video(cards: list[Path], audio: Path, output: Path, ffmpeg: str) -> None:
    duration = wav_duration(audio)
    each = duration / len(cards)
    concat = output.parent / "timeline.txt"
    lines = []
    for card in cards:
        lines.extend([f"file '{card.as_posix()}'", f"duration {each:.3f}"])
    lines.append(f"file '{cards[-1].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-i", str(audio), "-shortest", "-r", "30", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", str(output)],
                   check=True, capture_output=True)


def ffmpeg_path() -> str:
    explicit = os.environ.get("FFMPEG_PATH")
    if explicit:
        return explicit
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("Install imageio-ffmpeg or set FFMPEG_PATH") from exc
