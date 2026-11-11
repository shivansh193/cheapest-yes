"""Record the demo chapters with a scripted browser.

    python demo/record.py [base_url]        # default http://127.0.0.1:8017 (app running locally, PayPal sandbox)

Writes demo/out/rec/<chapter>.webm and demo/out/rec/marks.json (seconds from each recording's start).
The payment uses PayPal's sandbox guest-card checkout with a published test card number; no real money,
no real account. Nothing secret is typed.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.async_api import Page, async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8017"
OUT = Path(__file__).resolve().parent / "out" / "rec"
VIEW = {"width": 1440, "height": 900}
SEEDS = {"split": ("split-payment person", 1), "anyway": ("will buy anyway", 1), "student": ("price-sensitive student", 3)}
TEST_CARD = {"number": "4111111111111111", "exp": "1230", "cvv": "123"}
BILLING = {"first": "Test", "last": "Buyer", "line1": "1 Main St", "city": "San Jose", "state": "CA", "zip": "95131",
           "phone": "4085550100", "email": "buyer@example.com"}

CURSOR_JS = """
(() => {
  const add = () => {
    if (document.getElementById('__cur')) return;
    const d = document.createElement('div'); d.id = '__cur';
    d.style.cssText = 'position:fixed;left:-40px;top:-40px;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;' +
      'background:rgba(29,78,216,.35);border:2px solid rgba(29,78,216,.95);z-index:2147483647;pointer-events:none;transition:transform .12s';
    document.documentElement.appendChild(d);
    addEventListener('mousemove', e => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => d.style.transform = 'scale(1.6)', true);
    addEventListener('mouseup', () => d.style.transform = 'scale(1)', true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
"""


class Marks:
    def __init__(self):
        self.data: dict[str, dict[str, float]] = {}
        self.t0: dict[str, float] = {}

    def start(self, rec: str):
        self.t0[rec] = time.monotonic()
        self.data[rec] = {}

    def mark(self, rec: str, name: str):
        self.data[rec][name] = round(time.monotonic() - self.t0[rec], 2)
        print(f"  [{rec}] {name} @ {self.data[rec][name]}s")


M = Marks()
_pos = {"x": 720, "y": 450}


async def glide(page: Page, x: float, y: float, steps: int = 28):
    await page.mouse.move(x, y, steps=steps)
    _pos.update(x=x, y=y)


async def click(page: Page, locator, pause: float = 0.8):
    await locator.scroll_into_view_if_needed()
    box = await locator.bounding_box()
    await glide(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    await page.wait_for_timeout(250)
    await locator.click()
    await page.wait_for_timeout(int(pause * 1000))


async def smooth_scroll_to(page: Page, selector: str, offset: int = 90, ms: int = 1200):
    await page.evaluate(
        """([sel, off, ms]) => new Promise(r => {
            const el = document.querySelector(sel); if (!el) return r();
            const start = scrollY, end = el.getBoundingClientRect().top + scrollY - off, t0 = performance.now();
            const step = now => { const k = Math.min(1, (now - t0) / ms), e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
              scrollTo(0, start + (end - start) * e); k < 1 ? requestAnimationFrame(step) : r(); };
            requestAnimationFrame(step); })""", [selector, offset, ms])


async def replay_chapter(ctx, rec: str, persona: str, seed: int, reveal: bool = False, checkout: bool = False):
    page = await ctx.new_page()
    M.start(rec)
    await page.goto(f"{BASE}/replay?persona={persona.replace(' ', '%20')}&seed={seed}")
    M.mark(rec, "loaded")
    await glide(page, 300, 300)
    await page.wait_for_selector(".verdict", timeout=90000)
    M.mark(rec, "decision")
    await page.wait_for_timeout(1500)
    reasons = page.locator("h3", has_text="Top reasons")
    box = await reasons.bounding_box()
    await glide(page, box["x"] + 120, box["y"] + 40)
    try:
        await page.wait_for_function("() => { const t = document.querySelector('#ai-text'); return t && !t.querySelector('.spinner'); }", timeout=30000)
        M.mark(rec, "ai")
    except Exception:  # noqa: BLE001
        M.mark(rec, "ai_timeout")
    await page.wait_for_timeout(1800)
    await smooth_scroll_to(page, ".options", offset=200)
    M.mark(rec, "options")
    rows = page.locator(".options tr.chosen")
    b = await rows.bounding_box()
    await glide(page, b["x"] + 160, b["y"] + b["height"] / 2)
    await page.wait_for_timeout(2600)
    if reveal:
        await click(page, page.locator("summary", has_text="Reveal the hidden truth"), pause=0.4)
        M.mark(rec, "truth")
        await smooth_scroll_to(page, "details[open]", offset=260, ms=900)
        await page.wait_for_timeout(2600)
    if checkout:
        await smooth_scroll_to(page, "#checkout-card", offset=80)
        await page.wait_for_selector("#paypal-buttons iframe", timeout=60000)
        await page.wait_for_timeout(2500)
        M.mark(rec, "checkout")
        msg = page.locator("#incentive .incentive")
        b = await msg.bounding_box()
        await glide(page, b["x"] + b["width"] * 0.6, b["y"] + 30)
        await page.wait_for_timeout(2500)
        return page
    await page.wait_for_timeout(800)
    M.mark(rec, "end")
    await page.close()
    return None


async def type_into(loc, text: str, delay: int = 55):
    await loc.click()
    await loc.type(text, delay=delay)


async def pay_with_test_card(ctx, page: Page, rec: str):
    fr = page.frame_locator("#paypal-buttons iframe").first
    card_btn = fr.locator("[data-funding-source='card']").first
    box = await page.locator("#paypal-buttons").bounding_box()
    await glide(page, box["x"] + box["width"] / 2, box["y"] + 150)
    await page.wait_for_timeout(400)
    M.start("pay_popup")
    async with ctx.expect_page(timeout=30000) as pinfo:
        await card_btn.click()
    M.mark(rec, "card_clicked")
    pop = await pinfo.value
    await pop.wait_for_load_state("domcontentloaded")
    await pop.wait_for_selector("#cardNumber", timeout=60000)
    M.mark("pay_popup", "form")
    await pop.wait_for_timeout(1200)
    await type_into(pop.locator("#cardNumber"), TEST_CARD["number"])
    await type_into(pop.locator("#cardExpiry"), TEST_CARD["exp"])
    await type_into(pop.locator("#cardCvv"), TEST_CARD["cvv"])
    await type_into(pop.locator("#firstName"), BILLING["first"], 40)
    await type_into(pop.locator("#lastName"), BILLING["last"], 40)
    await type_into(pop.locator("#billingLine1"), BILLING["line1"], 30)
    await type_into(pop.locator("#billingCity"), BILLING["city"], 30)
    await pop.locator("#billingState").select_option(BILLING["state"])
    await type_into(pop.locator("#billingPostalCode"), BILLING["zip"], 30)
    await type_into(pop.locator("#phone"), BILLING["phone"], 30)
    await type_into(pop.locator("#email"), BILLING["email"], 25)
    M.mark("pay_popup", "filled")
    await pop.wait_for_timeout(800)
    vis = await pop.locator("button, input[type=submit], [role=button]").evaluate_all(
        "els => els.filter(e => e.offsetParent !== null).map(e => [e.tagName, e.id, e.type, (e.innerText || e.value || '').trim().slice(0, 40)].join('|'))")
    print("  visible buttons:", [v.encode('ascii', 'replace').decode() for v in vis])
    await pop.screenshot(path=str(OUT / "pay_filled.png"), full_page=True)
    import re
    submit = pop.get_by_role("button", name=re.compile(r"pay now as guest", re.I)).first
    await submit.scroll_into_view_if_needed()
    b = await submit.bounding_box()
    await glide(pop, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    await submit.click()
    M.mark("pay_popup", "submitted")
    try:
        await page.wait_for_selector(".receipt", timeout=90000)
    except Exception:  # noqa: BLE001
        if not pop.is_closed():
            await pop.screenshot(path=str(OUT / "pay_error.png"), full_page=True)
        raise
    M.mark(rec, "receipt")
    rc = page.locator(".receipt")
    await rc.scroll_into_view_if_needed()
    b = await rc.bounding_box()
    await glide(page, b["x"] + 200, b["y"] + 60)
    await page.wait_for_timeout(4000)
    M.mark(rec, "end")
    return pop


async def dashboard_chapter(ctx, rec: str):
    page = await ctx.new_page()
    M.start(rec)
    await page.goto(f"{BASE}/dashboard")
    await page.wait_for_selector(".kpi .value", timeout=60000)
    M.mark(rec, "kpis")
    await page.wait_for_timeout(1000)
    for i in range(4):
        b = await page.locator(".kpi").nth(i).bounding_box()
        await glide(page, b["x"] + 120, b["y"] + 70, steps=22)
        await page.wait_for_timeout(1100)
    await smooth_scroll_to(page, "#policy-chart", offset=170)
    M.mark(rec, "chart")
    b = await page.locator("#policy-chart").bounding_box()
    await glide(page, b["x"] + b["width"] * 0.55, b["y"] + b["height"] * 0.58)
    await page.wait_for_timeout(3000)
    await smooth_scroll_to(page, "#grid", offset=150)
    M.mark(rec, "grid")
    await page.locator("#source").select_option("replay")
    M.mark(rec, "grid_filtered")
    await page.wait_for_timeout(1200)
    hdr = page.locator(".ag-header-cell", has_text="PayPal order")
    await page.locator("#grid .ag-body-horizontal-scroll-viewport").evaluate("e => e.scrollTo({left: 900, behavior: 'smooth'})")
    await page.wait_for_timeout(1800)
    if await hdr.count():
        b = await hdr.first.bounding_box()
        if b:
            await glide(page, b["x"] + 60, b["y"] + 50)
    await page.wait_for_timeout(3000)
    await page.locator("#grid .ag-body-horizontal-scroll-viewport").evaluate("e => e.scrollTo({left: 0, behavior: 'smooth'})")
    await page.wait_for_timeout(1200)
    await smooth_scroll_to(page, ".copilot", offset=120)
    M.mark(rec, "copilot")
    await click(page, page.locator("#suggest .chip", has_text="Which incentive made the most profit?"), pause=0.3)
    M.mark(rec, "asked")
    try:
        await page.wait_for_function("() => { const a = document.querySelector('#answer'); return a && !a.querySelector('.spinner') && a.innerText.length > 40; }", timeout=60000)
        M.mark(rec, "answer")
    except Exception:  # noqa: BLE001
        M.mark(rec, "answer_timeout")
    b = await page.locator("#answer").bounding_box()
    await glide(page, b["x"] + 160, b["y"] + 30)
    await page.wait_for_timeout(5000)
    M.mark(rec, "end")
    await page.close()


async def main(only: set[str]):
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def ctx_for(name):
            d = OUT / f"_{name}"
            shutil.rmtree(d, ignore_errors=True)
            c = await browser.new_context(viewport=VIEW, record_video_dir=str(d), record_video_size=VIEW, device_scale_factor=1)
            await c.add_init_script(CURSOR_JS)
            return c, d

        async def save_pages(c, d, pages):
            vids = {name: pg.video for name, pg in pages.items()}
            await c.close()
            for name, v in vids.items():
                shutil.move(str(await v.path()), OUT / f"{name}.webm")
            shutil.rmtree(d, ignore_errors=True)

        async def save(c, d, mapping):
            await c.close()
            vids = sorted(d.glob("*.webm"), key=lambda f: f.stat().st_mtime)
            for src, name in zip(vids, mapping):
                shutil.move(str(src), OUT / f"{name}.webm")
            shutil.rmtree(d, ignore_errors=True)

        if "split" in only:
            c, d = await ctx_for("split")
            page = await replay_chapter(c, "ch1_split", *SEEDS["split"], checkout=True)
            pop = await pay_with_test_card(c, page, "ch1_split")
            await save_pages(c, d, {"ch1_split": page, "pay_popup": pop})
        for key, rec, reveal in [("anyway", "ch2_anyway", False), ("student", "ch3_student", True)]:
            if key in only:
                c, d = await ctx_for(key)
                await replay_chapter(c, rec, *SEEDS[key], reveal=reveal)
                await save(c, d, [rec])
        if "dashboard" in only:
            c, d = await ctx_for("dashboard")
            await dashboard_chapter(c, "ch4_dashboard")
            await save(c, d, ["ch4_dashboard"])
        await browser.close()
    mp = OUT / "marks.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    old.update(M.data)
    mp.write_text(json.dumps(old, indent=1))
    print(json.dumps(M.data, indent=1))


if __name__ == "__main__":
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else {"split", "anyway", "student", "dashboard"}
    asyncio.run(main(only))
