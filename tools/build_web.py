#!/usr/bin/env python3
"""Build the browser version into build/web/ with pygbag (https://pygame-web.github.io).

1. Makes every sound effect and every song (as a seamless loop) once, at the browser's 48000 Hz,
   into web_sounds/*.ogg: a browser can't sequence notes evenly or synthesise them quickly.
2. Runs pygbag, which packs the game folder into build/web/.

Needs pygame, pygbag (python3 -m pip install pygbag) and ffmpeg on PATH (or FFMPEG=/path):
pygbag converts the .wav sounds to .ogg for the browser with it.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ)
ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
if not ffmpeg:
    sys.exit("ffmpeg not found (set FFMPEG=/path/to/ffmpeg)")
env["PATH"] = os.path.dirname(os.path.abspath(ffmpeg)) + os.pathsep + env.get("PATH", "")


def render_web_sounds():
    import array
    import tempfile
    import wave
    sys.path.insert(0, ROOT)
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from chemtris import audio
    audio.RATE = 48000  # what browsers mix at
    out = audio.WEB_SOUNDS
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    jobs = [("fx_" + name, samples, gain) for name, (samples, gain) in audio.effect_samples().items()]
    assert sorted(n[3:] for n, _, _ in jobs) == sorted(audio.WEB_EFFECTS)
    for name, song, tempo in audio.web_songs():
        jobs.append((name, audio.render_loop(song, tempo), 1.0))
    with tempfile.TemporaryDirectory() as tmp:
        for name, samples, gain in jobs:
            wav = os.path.join(tmp, name + ".wav")
            data = array.array("h", (max(-32767, min(32767, int(v * gain * 32767))) for v in samples))
            with wave.open(wav, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(audio.RATE)
                handle.writeframes(data.tobytes())
            subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                            os.path.join(out, name + ".ogg")], check=True)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out))
    print(f"web_sounds: {len(jobs)} files, {size // 1024} KB")


render_web_sounds()
subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "ChemTris", "--app_name", "chemtris",
                "--icon", "assets/icon.png", "."], cwd=ROOT, env=env, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("build/web ready: upload index.html, the .apk and .tar.gz and favicon.png")

# pygbag sometimes sizes the canvas before the game has opened its window, squeezing the game
# into a square: add a small script that keeps it the game's shape (tools/web_canvas_fix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_canvas_fix  # noqa: E402

web_canvas_fix.apply(os.path.join(ROOT, "build", "web", "index.html"))
