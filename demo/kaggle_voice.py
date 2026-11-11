"""Kaggle kernel: Kokoro voiceover, music bed, mix and subtitles for the rendered demo video (CPU).

Inputs: the render kernel's output (cheapest-yes-demo.mp4, sections.json) and the media dataset
(narration.json, tts_kokoro.py). Outputs in /kaggle/working:
  cheapest-yes-demo-voice.mp4, cheapest-yes-demo-music.mp4, cheapest-yes-demo.srt, voice_fit.json, logs/
"""
import glob
import json
import os
import re
import subprocess
from pathlib import Path

W = Path("/kaggle/working")
TMP = Path("/kaggle/tmp")
LOGS = W / "logs"
for d in (LOGS, TMP):
    d.mkdir(parents=True, exist_ok=True)
VIDEO = glob.glob("/kaggle/input/**/cheapest-yes-demo.mp4", recursive=True)[0]
SECTIONS = json.loads(Path(glob.glob("/kaggle/input/**/sections.json", recursive=True)[0]).read_text())
NARR_PATH = glob.glob("/kaggle/input/**/narration.json", recursive=True)[0]
NARR = json.loads(Path(NARR_PATH).read_text(encoding="utf-8-sig"))
TTS = glob.glob("/kaggle/input/**/tts_kokoro.py", recursive=True)[0]
MAX_TEMPO = 1.18


def sh(cmd, log="voice.log", check=True):
    print(">>", cmd[:220], flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    with open(LOGS / log, "a") as f:
        f.write(f"$ {cmd}\n{out}\n")
    print(out[-2500:], flush=True)
    if check and r.returncode != 0:
        raise SystemExit(f"failed: {cmd}")
    return out


# ---------------------------------------------------------------- TTS (Python 3.12 venv; Kokoro needs < 3.13)
sh("apt-get update -qq && apt-get install -y -qq espeak-ng", "setup.log", check=False)
venv = TMP / "tts"
if not (venv / "bin" / "python").exists():
    sh(f"pip install -q uv && uv venv -p 3.12 {venv}", "setup.log")
    sh(f'uv pip install --python {venv}/bin/python "kokoro>=0.9.4" soundfile "numpy<2.3" '
       "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl", "setup.log")
wav_dir = TMP / "wav"
sh(f"{venv}/bin/python {TTS} {NARR_PATH} {wav_dir}", "tts.log")
durs = json.loads((wav_dir / "durations.json").read_text())

# ---------------------------------------------------------------- place lines
sec = {s["id"]: s for s in SECTIONS["sections"]}
TOTAL = SECTIONS["total"]
lines = NARR["lines"]
starts = [sec[l["section"]]["start"] + l.get("offset", 0.3) for l in lines]
report, placed = [], []
for i, l in enumerate(lines):
    f = wav_dir / f"{i:02d}_{l['section']}.wav"
    dur = durs[f.name]
    nxt = starts[i + 1] if i + 1 < len(lines) else TOTAL - 0.3
    room = round(nxt - starts[i] - 0.25, 2)
    tempo = 1.0 if dur <= room else dur / room
    fits = tempo <= MAX_TEMPO
    tempo = min(tempo, MAX_TEMPO)
    g = TMP / f"placed_{i:02d}.wav"
    sh(f"ffmpeg -v error -y -i {f} -af \"atempo={tempo:.4f},aresample=48000\" -ac 1 {g}")
    final = round(dur / tempo, 2)
    placed.append({"i": i, "section": l["section"], "start": round(starts[i], 2), "end": round(starts[i] + final, 2),
                   "written": l["written"], "file": str(g)})
    report.append({"section": l["section"], "start": round(starts[i], 2), "length": dur, "room": room,
                   "tempo": round(tempo, 3), "fits": fits})
(W / "voice_fit.json").write_text(json.dumps(report, indent=1))
for r in report:
    print(r)

# voice track
inputs = " ".join(f"-i {p['file']}" for p in placed)
delays = ";".join(f"[{k}:a]adelay={int(p['start'] * 1000)}|{int(p['start'] * 1000)}[v{k}]" for k, p in enumerate(placed))
mix = "".join(f"[v{k}]" for k in range(len(placed)))
sh(f"ffmpeg -v error -y {inputs} -filter_complex \"{delays};{mix}amix=inputs={len(placed)}:normalize=0,apad=whole_dur={TOTAL}[out]\" "
   f"-map [out] -ar 48000 -ac 2 -t {TOTAL} {TMP}/voice.wav")

# ---------------------------------------------------------------- music bed (synthesized here: no licensing questions)
# Two soft chords alternating every 8 s (Cmaj7 / Am9 voicings), slow swell, low-passed.
chord = ("if(lt(mod(t,16),8),"
         "sin(2*PI*130.81*t)+sin(2*PI*196.00*t)+0.8*sin(2*PI*246.94*t)+0.6*sin(2*PI*329.63*t),"
         "sin(2*PI*110.00*t)+sin(2*PI*164.81*t)+0.8*sin(2*PI*246.94*t)+0.6*sin(2*PI*261.63*t))")
expr = f"0.09*({chord})*(0.65+0.35*sin(2*PI*t/8-PI/2))"
sh(f"ffmpeg -v error -y -f lavfi -i \"aevalsrc='{expr}|{expr}':s=48000:d={TOTAL}\" "
   f"-af \"lowpass=f=1800,aecho=0.6:0.5:120:0.25,afade=t=in:d=2.5,afade=t=out:st={TOTAL - 4}:d=4\" {TMP}/music.wav")

# ---------------------------------------------------------------- mixes
sh(f"ffmpeg -v error -y -i {VIDEO} -i {TMP}/music.wav -i {TMP}/voice.wav -filter_complex "
   f"\"[1:a]volume=0.16[m];[2:a]asplit=2[vo][sc];[m][sc]sidechaincompress=threshold=0.02:ratio=9:attack=15:release=350[duck];"
   f"[duck][vo]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]\" "
   f"-map 0:v -map [a] -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest {W}/cheapest-yes-demo-voice.mp4")
sh(f"ffmpeg -v error -y -i {VIDEO} -i {TMP}/music.wav -filter_complex \"[1:a]volume=0.5,loudnorm=I=-18:TP=-1.5:LRA=11[a]\" "
   f"-map 0:v -map [a] -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest {W}/cheapest-yes-demo-music.mp4")
for f in ("cheapest-yes-demo-voice.mp4", "cheapest-yes-demo-music.mp4"):
    sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 {W}/{f}", "check.log")
    sh(f"ffmpeg -hide_banner -i {W}/{f} -af volumedetect -vn -f null - 2>&1 | grep -E 'mean_volume|max_volume'", "check.log", check=False)


# ---------------------------------------------------------------- subtitles
def chunks(text, width=42):
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|(?<=,)\s+", text) if p.strip()]
    cues, cur = [], ""
    for p in parts:
        cand = (cur + " " + p).strip()
        if len(cand) <= width * 2:
            cur = cand
        else:
            if cur:
                cues.append(cur)
            cur = p
    if cur:
        cues.append(cur)
    out = []
    for c in cues:
        if len(c) > width:
            words, l1 = c.split(), ""
            while words and len((l1 + " " + words[0]).strip()) <= width:
                l1 = (l1 + " " + words.pop(0)).strip()
            c = l1 + "\n" + " ".join(words)
        out.append(c)
    return out


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


srt, n = [], 1
cue_list = []
for p in placed:
    cs = chunks(p["written"])
    total_chars = sum(len(c) for c in cs)
    t = p["start"]
    for c in cs:
        d = (p["end"] - p["start"]) * len(c) / total_chars
        cue_list.append([t, t + d, c])
        t += d
for k in range(len(cue_list) - 1):
    cue_list[k][1] = min(cue_list[k][1], cue_list[k + 1][0] - 0.04)
for a, b, c in cue_list:
    srt.append(f"{n}\n{ts(a)} --> {ts(b)}\n{c}\n")
    n += 1
(W / "cheapest-yes-demo.srt").write_text("\n".join(srt), encoding="utf-8")
print("DONE")
