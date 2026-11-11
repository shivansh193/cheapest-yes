"""Kaggle kernel: build the Hyperframes composition and render the demo video (CPU, internet on).
Outputs in /kaggle/working: cheapest-yes-demo.mp4 (poster baked in), preview_sheet.jpg, logs/*.log, sections.json."""
import glob
import os
import shutil
import subprocess
from pathlib import Path

W = Path("/kaggle/working")
TMP = Path("/kaggle/tmp")
LOGS = W / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
MEDIA = Path(glob.glob("/kaggle/input/**/marks.json", recursive=True)[0]).parent
PROJ = TMP / "proj"
COMP = PROJ / "composition"
POSTER_T = 47.0


def sh(cmd, log=None, check=True, cwd=None, env=None):
    print(">>", cmd[:200], flush=True)
    r = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if log:
        with open(LOGS / log, "a") as f:
            f.write(f"$ {cmd}\n{out}\n")
    print(out[-3000:], flush=True)
    if check and r.returncode != 0:
        raise SystemExit(f"failed ({r.returncode}): {cmd}")
    return r.returncode, out


# ---------------------------------------------------------------- toolchain
NODE = TMP / "node"
if not (NODE / "bin" / "node").exists():
    sh(f"curl -fsSL https://nodejs.org/dist/v22.11.0/node-v22.11.0-linux-x64.tar.xz -o {TMP}/node.tar.xz && "
       f"mkdir -p {NODE} && tar -xJf {TMP}/node.tar.xz -C {NODE} --strip-components=1", "setup.log")
env = dict(os.environ, PATH=f"{NODE}/bin:" + os.environ["PATH"], NPM_CONFIG_UPDATE_NOTIFIER="false")
sh("node --version && npm --version", "setup.log", env=env)
if shutil.which("ffmpeg") is None:
    sh("apt-get update -qq && apt-get install -y -qq ffmpeg", "setup.log", check=False)
sh("apt-get update -qq", "setup.log", check=False)
for lib in ["libnss3", "libatk1.0-0", "libatk1.0-0t64", "libatk-bridge2.0-0", "libatk-bridge2.0-0t64", "libcups2", "libcups2t64",
            "libdrm2", "libxkbcommon0", "libxcomposite1", "libxdamage1", "libxfixes3", "libxrandr2", "libgbm1",
            "libpango-1.0-0", "libcairo2", "libasound2", "libasound2t64", "libatspi2.0-0", "libatspi2.0-0t64",
            "libxshmfence1", "fonts-liberation"]:
    sh(f"apt-get install -y -qq {lib}", "setup.log", check=False)

# ---------------------------------------------------------------- composition
shutil.rmtree(PROJ, ignore_errors=True)
PROJ.mkdir(parents=True)
sh(f"python {MEDIA}/build.py {MEDIA} {COMP}", "build.log")
(COMP / "fonts").mkdir(exist_ok=True)
base = "https://cdn.jsdelivr.net/npm/geist@1.3.1/dist/fonts"
for f in ["geist-sans/Geist-Regular.woff2", "geist-sans/Geist-Medium.woff2", "geist-sans/Geist-SemiBold.woff2",
          "geist-sans/Geist-Bold.woff2", "geist-mono/GeistMono-Regular.woff2"]:
    sh(f"curl -fsSL {base}/{f} -o {COMP}/fonts/{f.split('/')[-1]}", "setup.log")
sh(f"curl -fsSL https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js -o {COMP}/gsap.min.js", "setup.log")
shutil.copy(COMP / "sections.json", W / "sections.json")

# ---------------------------------------------------------------- hyperframes
sh("npx -y hyperframes@latest --version", "hyperframes.log", check=False, cwd=COMP, env=env)
sh("npx -y hyperframes@latest --help", "hyperframes.log", check=False, cwd=COMP, env=env)
sh("npx -y hyperframes@latest render --help", "hyperframes.log", check=False, cwd=COMP, env=env)
sh("npx -y hyperframes@latest browser ensure", "hyperframes.log", check=False, cwd=COMP, env=env)
sh("npx -y hyperframes@latest lint", "lint.log", check=False, cwd=COMP, env=env)
sh("npx -y hyperframes@latest check", "check.log", check=False, cwd=COMP, env=env)
code, _ = sh("npx -y hyperframes@latest render --quality high", "render.log", check=False, cwd=COMP, env=env)

found = sorted(glob.glob(f"{PROJ}/**/*.mp4", recursive=True) + glob.glob(f"{COMP}/*.mp4"), key=os.path.getmtime)
found = [f for f in found if "/media/" not in f]
print("rendered candidates:", found)
if not found:
    raise SystemExit("no render output; see logs/render.log")
raw = found[-1]
shutil.copy(raw, W / "render_raw.mp4")

# ---------------------------------------------------------------- poster + preview
sh(f"ffmpeg -v error -y -ss {POSTER_T} -i {raw} -frames:v 1 {TMP}/poster.png", "post.log")
sh(f"ffmpeg -v error -y -i {raw} -i {TMP}/poster.png -filter_complex \"[0:v][1:v]overlay=0:0:enable='eq(n,0)'\" "
   f"-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a copy -movflags +faststart {W}/cheapest-yes-demo.mp4", "post.log")
_, dur = sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 {W}/cheapest-yes-demo.mp4", "post.log")
d = float(dur.strip().splitlines()[-1])
sh(f"ffmpeg -v error -y -i {W}/cheapest-yes-demo.mp4 -vf \"fps=20/{d},scale=480:-1,tile=5x4\" -frames:v 1 {W}/preview_sheet.jpg", "post.log")
os.remove(W / "render_raw.mp4")
print("DONE", d)
