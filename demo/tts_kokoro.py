"""Run inside the Python 3.12 venv on Kaggle: synthesize each narration line with Kokoro-82M (af_heart, 24 kHz)."""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

narr = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
pipe = KPipeline(lang_code="a")
durs = {}
for i, line in enumerate(narr["lines"]):
    chunks = [a for _, _, a in pipe(line["spoken"], voice=narr.get("voice", "af_heart"), speed=narr.get("speed", 1.0))]
    audio = np.concatenate([np.asarray(c, dtype=np.float32) for c in chunks])
    f = out / f"{i:02d}_{line['section']}.wav"
    sf.write(f, audio, 24000)
    durs[f.name] = round(len(audio) / 24000, 3)
    print(f.name, durs[f.name], flush=True)
(out / "durations.json").write_text(json.dumps(durs, indent=1))
