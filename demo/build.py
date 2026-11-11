"""Build the Hyperframes composition for the Cheapest Yes demo video.

    python build.py <media_dir> <out_dir>

Reads marks.json + the chapter mp4s from <media_dir>, writes <out_dir>/index.html (1920x1080, 30 fps) and
<out_dir>/sections.json (start/end of every section, used to place the voiceover). Every number shown comes
from the repo (docs/EVAL.md, docs/EVIDENCE.md) or from the recorded run.
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

MEDIA = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "composition")
TARGET_MAX = 175.0
marks = json.loads((MEDIA / "marks.json").read_text())
M1, MP, M2, M3, M4 = (marks[k] for k in ("ch1_split", "pay_popup", "ch2_anyway", "ch3_student", "ch4_dashboard"))

E = html.escape

# ------------------------------------------------------------------ plan
# ("slide", id, duration, html) | ("card", id, duration, num, title, sub) | ("clip", id, file, media_in, media_out, captions[(t, text)], layout)
PLAN = [
    ("slide", "hook", 4.0, """<div class="hook"><div class="big">7 in 10 online carts are abandoned.</div>
        <div class="mono src">Baymard Institute · average of 50 studies · 70.22%</div></div>"""),
    ("slide", "title", 4.0, """<div class="titlecard"><div class="mono kicker">PayPal AI Hackathon 2026 · PayPal + AI</div>
        <div class="name">Cheapest Yes</div><div class="tag">The cheapest thing that turns “maybe” into “yes”.</div></div>"""),
    ("slide", "problem", 10.0, """<div class="slide"><div class="mono label">The problem</div><h2>Blanket discounts pay people who would have bought anyway.</h2>
        <div class="cards c3">
        <div class="card"><div class="mono">Baymard</div><div class="stat">40%</div><p>of checkout abandoners say extra costs were too high</p></div>
        <div class="card"><div class="mono">The usual answer</div><div class="stat">10% off</div><p>for everyone, including shoppers who were already buying</p></div>
        <div class="card"><div class="mono">The missed lever</div><div class="stat">Not price</div><p>Splitting the payment, free shipping or a small add-on often does the job</p></div>
        </div></div>"""),
    ("slide", "ladder", 12.0, """<div class="slide"><div class="mono label">What each “yes” costs the merchant · $240 cart</div><h2>The ladder, cheapest first.</h2>
        <div class="cards c4">
        <div class="card hl"><div class="mono">01 · PayPal Pay Later</div><div class="stat">≈ $3.60</div><p>4.99% vs 3.49% for PayPal Checkout. Charged only if the shopper actually pays with it.</p></div>
        <div class="card"><div class="mono">02 · Free shipping</div><div class="stat">$8.99</div><p>The shipping fee the merchant absorbs</p></div>
        <div class="card"><div class="mono">03 · Free add-on</div><div class="stat">$4.00</div><p>Cost of goods for a small accessory</p></div>
        <div class="card"><div class="mono">04 · 10% off</div><div class="stat">$24.00</div><p>Given away on every order it touches</p></div>
        </div><div class="rule">List price is the ceiling. Nothing ever costs more than list.</div>
        <div class="mono src">Fees: PayPal US merchant fee page, updated Nov 4, 2026</div></div>"""),
    ("slide", "glance", 9.0, """<div class="slide"><div class="mono label">At a glance</div><h2>AI scores the session. A profit engine decides. PayPal checks out.</h2>
        <div class="flow">
        <div class="card"><div class="mono">Signals</div><p>Session behaviour only: cart, pauses, comparisons, returns. No demographics or location.</p></div><div class="arrow">→</div>
        <div class="card"><div class="mono">AI models</div><p>Intent model (UCI, AUC 0.910) + one uplift model per incentive, SHAP reasons</p></div><div class="arrow">→</div>
        <div class="card hl"><div class="mono">Profit engine</div><p>Deterministic. Max expected profit after fees. Guardrails.</p></div><div class="arrow">→</div>
        <div class="card"><div class="mono">PayPal</div><p>Orders v2 · JS SDK · Pay Later messaging · verified webhooks</p></div>
        </div><div class="rule">Gemini explains each decision and answers the merchant. It never decides.</div></div>"""),
    ("card", "c1", 1.5, "01", "Split-payment person", "Big cart, stalls at the total"),
    ("clip", "r1a", "ch1_split.mp4", 0.3, M1["card_clicked"], [
        (0.0, "Replay: a simulated shopper. A $288 smartwatch, a 67-second pause at the total."),
        (M1["decision"] - 0.3, "Decision: PayPal Pay Later. P(buy) 20% → 73%, with SHAP reasons."),
        (M1["options"] - 0.3, "Every option is scored on expected profit after PayPal fees."),
        (M1["checkout"] - 0.3, "Checkout shows the exact Pay Later instalments for this cart."),
    ], "full"),
    ("clip", "r1b", "pay_popup.mp4", MP["form"] - 0.4, MP["submitted"] + 5.6, [
        (0.0, "A real PayPal sandbox payment: guest checkout with a published test card."),
        (MP["filled"] - MP["form"] + 0.4, "No real money moves. $296.99 is sent to the sandbox."),
    ], "popup"),
    ("clip", "r1c", "ch1_split.mp4", M1["receipt"] - 0.3, M1["receipt"] + 5.7, [
        (0.0, "Captured. Order 2VY87021CY7959918, PayPal fee $10.85, logged with the decision."),
    ], "full"),
    ("card", "c2", 1.5, "02", "Will buy anyway", "Returning customer, knows what they want"),
    ("clip", "r2", "ch2_anyway.mp4", 0.3, min(M2["end"], 13.1), [
        (0.0, "A returning customer with two past orders."),
        (M2["decision"] - 0.3, "Decision: no incentive. They're 80% likely to buy already."),
        (M2["options"] - 0.3, "Any offer here would mostly give margin away."),
    ], "full"),
    ("card", "c3", 1.5, "03", "Price-sensitive student", "Compares prices in other tabs"),
    ("clip", "r3", "ch3_student.mp4", 3.5, 20.7, [
        (0.0, "A student comparing prices: copied product names, switched tabs."),
        (M3["decision"] - 3.5, "Decision: 10% off. P(buy) 16% → 48%."),
        (M3["options"] - 3.5, "Pay Later barely moves this shopper. Price does."),
        (M3["truth"] - 3.5, "The hidden truth the engine never saw agrees."),
    ], "full"),
    ("slide", "how", 10.0, """<div class="slide"><div class="mono label">How it decides</div><h2>Pick the incentive with the highest expected profit, or none.</h2>
        <div class="formula mono">gain(o) = P(buy | o) × (margin − cost(o)) − P(buy | none) × margin</div>
        <div class="cards c4">
        <div class="card"><div class="mono">Threshold</div><p>Nothing unless it beats doing nothing by $0.50</p></div>
        <div class="card"><div class="mono">Pay Later cost</div><p>1.5% × total × P(shopper pays with Pay Later)</p></div>
        <div class="card"><div class="mono">Guardrails</div><p>List-price ceiling · max 10% off · daily budget · 2 offers per shopper per week</p></div>
        <div class="card"><div class="mono">Tested</div><p>55 tests, incl. “no incentive ever raises a price”</p></div>
        </div></div>"""),
    ("card", "c4", 1.5, "04", "Merchant dashboard", "Every decision, its cost and its outcome"),
    ("clip", "r4a", "ch4_dashboard.mp4", 0.4, 9.4, [
        (0.0, "Simulator A/B: 20,000 fresh shoppers with hidden true responses."),
        (4.2, "+$8.3k profit per 1,000 shoppers vs a blanket 10% off."),
    ], "full"),
    ("clip", "r4b", "ch4_dashboard.mp4", M4["grid"] - 0.3, M4["end"] - 0.3, [
        (0.0, "AG Grid decision log, with PayPal order and capture IDs."),
        (M4["copilot"] - M4["grid"], "Gemini copilot answers from decision-log aggregates only."),
    ], "full"),
    ("slide", "results", 13.0, """<div class="slide"><div class="mono label">Results · simulator, 20,000 fresh shoppers, 95% CIs</div><h2>Where the profit comes from, and where it doesn't.</h2>
        <div class="cards c3">
        <div class="card hl"><div class="mono">vs blanket 10% off</div><div class="stat">+$8,290</div><p>profit per 1,000 shoppers (CI +7,924 to +8,656)</p></div>
        <div class="card"><div class="mono">Ablation</div><div class="stat">−$6,587</div><p>if Pay Later is removed from the ladder</p></div>
        <div class="card"><div class="mono">Margin wasted</div><div class="stat">$798</div><p>on would-buy-anyway shoppers, vs $4,276 for 10% off</p></div>
        <div class="card weak"><div class="mono">Weak spot</div><div class="stat">+$833</div><p>over simply always showing Pay Later (CI +720 to +955). Pay Later does most of the work.</p></div>
        <div class="card weak"><div class="mono">Oracle agreement</div><div class="stat">47%</div><p>same pick as an oracle that sees the hidden truth; 95% of its profit</p></div>
        <div class="card"><div class="mono">Public data</div><div class="stat">0.910 · 1.73×</div><p>intent AUC on UCI · uplift vs random on Criteo</p></div>
        </div><div class="mono src">Simulator results, not field results. Full tables: docs/EVAL.md</div></div>"""),
    ("slide", "outro", 7.0, """<div class="titlecard"><div class="outro">List price is the ceiling.<br>Profit is the goal.<br><b>PayPal Pay Later is the cheapest yes.</b></div>
        <div class="mono links">cheapest-yes.onrender.com · github.com/shivansh193/cheapest-yes</div>
        <div class="mono kicker">Built with PayPal · Gemini · Channel3 · AG Grid · Render · APIMatic</div></div>"""),
]

# ------------------------------------------------------------------ timeline
t = 0.0
sections, items = [], []
for p in PLAN:
    kind, sid = p[0], p[1]
    dur = p[2] if kind != "clip" else round(p[4] - p[3], 2)
    sections.append({"id": sid, "kind": kind, "start": round(t, 2), "end": round(t + dur, 2)})
    items.append((p, round(t, 2), dur))
    t += dur
TOTAL = round(t, 2)
assert TOTAL <= TARGET_MAX, f"plan is {TOTAL}s, over {TARGET_MAX}s"
for a, b in zip(sections, sections[1:]):
    assert a["end"] <= b["start"] + 1e-6, (a, b)
for p, start, dur in items:
    if p[0] == "clip":
        for ct, _ in p[5]:
            assert 0 <= ct < dur, (p[1], ct, dur)

# ------------------------------------------------------------------ html
FPS = 30
parts, tl = [], []
for p, start, dur in items:
    kind, sid = p[0], p[1]
    if kind == "slide":
        parts.append(f'<section id="{sid}" class="scene clip" data-start="{start}" data-duration="{dur}">{p[3]}</section>')
        tl.append(f'tl.fromTo("#{sid}", {{opacity:0}}, {{opacity:1, duration:.35}}, {start});')
        tl.append(f'tl.from("#{sid} .card, #{sid} h2, #{sid} .rule, #{sid} .big, #{sid} .name, #{sid} .tag, #{sid} .outro", {{y:18, opacity:0, duration:.45, stagger:.09, ease:"power2.out"}}, {start + 0.15});')
        tl.append(f'tl.to("#{sid}", {{opacity:0, duration:.3}}, {start + dur - 0.3});')
    elif kind == "card":
        _, _, _, num, title, sub = p
        parts.append(f'<section id="{sid}" class="scene clip chapter" data-start="{start}" data-duration="{dur}"><div class="mono num">{num}</div>'
                     f'<div class="ctitle">{E(title)}</div><div class="csub">{E(sub)}</div></section>')
        tl.append(f'tl.fromTo("#{sid}", {{opacity:0}}, {{opacity:1, duration:.25}}, {start});')
        tl.append(f'tl.from("#{sid} .ctitle", {{x:-24, duration:.5, ease:"power2.out"}}, {start});')
        tl.append(f'tl.to("#{sid}", {{opacity:0, duration:.25}}, {start + dur - 0.25});')
    else:
        _, _, file, m_in, m_out, caps, layout = p
        cls = "frame popupframe" if layout == "popup" else "frame"
        side = ""
        if layout == "popup":
            side = ('<div class="side"><div class="mono label">PayPal sandbox</div><h3>Guest card checkout</h3>'
                    '<p>Orders v2 order created on the server from the stored decision: $288.00 items + $8.99 shipping.</p>'
                    '<p>Paid with a published sandbox test card. No real money, no real account.</p>'
                    '<p class="mono small">Capture + fee recorded · webhook signature verified</p></div>')
        parts.append(f'<section id="{sid}" class="scene clipscene">'
                     f'<div class="{cls}"><video id="{sid}_v" class="clip" src="media/{file}" muted playsinline data-start="{start}" data-duration="{dur}" '
                     f'data-media-start="{m_in}" data-track-index="1"></video></div>{side}<div class="capstrip">'
                     + "".join(f'<div class="cap" id="{sid}_c{i}">{E(text)}</div>' for i, (_, text) in enumerate(caps))
                     + "</div></section>")
        tl.append(f'tl.fromTo("#{sid}", {{opacity:0}}, {{opacity:1, duration:.3}}, {start});')
        tl.append(f'tl.to("#{sid}", {{opacity:0, duration:.25}}, {start + dur - 0.25});')
        for i, (ct, _) in enumerate(caps):
            c_start = start + ct + 0.1
            c_end = start + (caps[i + 1][0] if i + 1 < len(caps) else dur) - 0.05
            tl.append(f'tl.fromTo("#{sid}_c{i}", {{opacity:0, y:8}}, {{opacity:1, y:0, duration:.3}}, {c_start:.2f});')
            tl.append(f'tl.to("#{sid}_c{i}", {{opacity:0, duration:.2}}, {max(c_start + 0.4, c_end - 0.2):.2f});')

CSS = """
@font-face { font-family: Geist; src: url(fonts/Geist-Regular.woff2) format('woff2'); font-weight: 400; }
@font-face { font-family: Geist; src: url(fonts/Geist-Medium.woff2) format('woff2'); font-weight: 500; }
@font-face { font-family: Geist; src: url(fonts/Geist-SemiBold.woff2) format('woff2'); font-weight: 600; }
@font-face { font-family: Geist; src: url(fonts/Geist-Bold.woff2) format('woff2'); font-weight: 700; }
@font-face { font-family: GeistMono; src: url(fonts/GeistMono-Regular.woff2) format('woff2'); }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1920px; height: 1080px; background: #f5f6f8; overflow: hidden; }
#root { position: relative; width: 1920px; height: 1080px; background: #f5f6f8; color: #111827; font-family: Geist, sans-serif; }
.scene { position: absolute; inset: 0; opacity: 0; }
.mono { font-family: GeistMono, monospace; letter-spacing: .02em; }
.label { font-size: 22px; color: #1d4ed8; text-transform: uppercase; }
.slide { padding: 110px 150px; }
.slide h2 { font-size: 58px; font-weight: 650; letter-spacing: -0.02em; margin: 18px 0 54px; max-width: 1500px; line-height: 1.12; }
.cards { display: grid; gap: 26px; }
.c3 { grid-template-columns: repeat(3, 1fr); } .c4 { grid-template-columns: repeat(4, 1fr); }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 20px; padding: 30px 30px 32px; box-shadow: 0 2px 10px rgba(17,24,39,.05); }
.card .mono { font-size: 19px; color: #6b7280; }
.card .stat { font-size: 60px; font-weight: 700; letter-spacing: -0.03em; margin: 10px 0 8px; }
.card p { font-size: 25px; line-height: 1.35; color: #374151; margin-top: 8px; }
.card.hl { border: 2px solid #1d4ed8; } .card.hl .mono { color: #1d4ed8; }
.card.weak { background: #fffaf0; border-color: #f3d9a4; } .card.weak .mono { color: #b45309; }
.rule { margin-top: 44px; font-size: 32px; font-weight: 600; }
.src { position: absolute; left: 150px; bottom: 60px; font-size: 18px; color: #9ca3af; }
.hook, .titlecard { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; padding: 0 180px; }
.hook .big { font-size: 112px; font-weight: 700; letter-spacing: -0.04em; line-height: 1.02; max-width: 1400px; }
.hook .src { left: 180px; bottom: 120px; font-size: 22px; }
.titlecard .kicker { font-size: 24px; color: #1d4ed8; }
.titlecard .name { font-size: 150px; font-weight: 700; letter-spacing: -0.05em; margin: 10px 0 4px; }
.titlecard .tag { font-size: 46px; color: #374151; }
.outro { font-size: 74px; font-weight: 600; letter-spacing: -0.03em; line-height: 1.12; }
.outro b { color: #1d4ed8; font-weight: 700; }
.titlecard .links { font-size: 28px; margin: 54px 0 14px; color: #111827; }
.flow { display: grid; grid-template-columns: 1fr 60px 1fr 60px 1fr 60px 1fr; align-items: stretch; }
.flow .arrow { display: grid; place-items: center; font-size: 44px; color: #9ca3af; }
.formula { font-size: 34px; background: #111827; color: #f9fafb; padding: 28px 34px; border-radius: 16px; margin: -20px 0 40px; }
.chapter { display: flex; flex-direction: column; justify-content: center; padding: 0 200px; background: #111827; color: #f9fafb; }
.chapter .num { font-size: 30px; color: #93c5fd; }
.chapter .ctitle { font-size: 104px; font-weight: 700; letter-spacing: -0.04em; margin: 6px 0; }
.chapter .csub { font-size: 38px; color: #cbd5e1; }
.frame { position: absolute; left: 192px; top: 22px; width: 1536px; height: 960px; border-radius: 18px; overflow: hidden;
  background: #fff; box-shadow: 0 18px 50px rgba(17,24,39,.16), 0 0 0 1px rgba(17,24,39,.06); }
.frame video { width: 100%; height: 100%; display: block; object-fit: cover; }
.popupframe { left: 260px; top: 22px; width: 727px; height: 958px; }
.side { position: absolute; left: 1070px; top: 200px; width: 640px; }
.side h3 { font-size: 54px; font-weight: 700; letter-spacing: -0.03em; margin: 12px 0 24px; }
.side p { font-size: 28px; line-height: 1.4; color: #374151; margin-bottom: 18px; }
.side .small { font-size: 21px; color: #6b7280; }
.capstrip { position: absolute; left: 192px; right: 192px; top: 992px; height: 76px; }
.cap { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 34px; font-weight: 550; opacity: 0; color: #111827; }
"""

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "media").mkdir(exist_ok=True)
for p in PLAN:
    if p[0] == "clip":
        src = MEDIA / p[2]
        if src.exists() and not (OUT / "media" / p[2]).exists():
            shutil.copy(src, OUT / "media" / p[2])
doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Cheapest Yes demo</title><style>{CSS}</style>
<script src="gsap.min.js"></script></head><body>
<div id="root" data-composition-id="main" data-duration="{TOTAL}" data-width="1920" data-height="1080" data-fps="{FPS}">
{"".join(parts)}
</div>
<script>
const tl = gsap.timeline({{paused: true}});
{chr(10).join(tl)}
tl.set({{}}, {{}}, {TOTAL});
window.__timelines = window.__timelines || {{}};
window.__timelines.main = tl;
</script></body></html>"""
(OUT / "index.html").write_text(doc, encoding="utf-8")
(OUT / "sections.json").write_text(json.dumps({"total": TOTAL, "sections": sections}, indent=1))
print(f"composition: {TOTAL}s, {len(sections)} sections")
for s in sections:
    print(f"  {s['start']:7.2f}-{s['end']:7.2f}  {s['kind']:5s} {s['id']}")
