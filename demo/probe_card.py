"""Probe PayPal's guest card checkout popup (sandbox, localhost app). Prints inputs and buttons."""
import asyncio
import sys

from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8017"


async def dump(pg, label):
    print("=====", label, pg.url[:120])
    for f in pg.frames:
        try:
            ins = await f.locator("input, select").evaluate_all(
                "els => els.filter(e => e.type !== 'hidden').map(e => [e.tagName, e.name, e.id, e.type, e.getAttribute('aria-label') || e.placeholder || ''].join('|'))")
            bts = await f.locator("button, [role=button]").evaluate_all("els => els.map(e => (e.innerText||'').trim().slice(0,40)).filter(Boolean)")
            if ins or bts:
                print(" FRAME", f.url[:90])
                for i in ins:
                    print("   ", i)
                print("   buttons:", bts[:12])
        except Exception as e:  # noqa: BLE001
            print("   err", str(e)[:100])


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        await page.goto(f"{BASE}/replay?persona=split-payment%20person&seed=8")
        await page.wait_for_selector("#paypal-buttons iframe", timeout=60000)
        await page.wait_for_timeout(3000)
        fr = page.frame_locator("#paypal-buttons iframe").first
        async with ctx.expect_page(timeout=30000) as pinfo:
            await fr.locator("[data-funding-source='card']").first.click()
        pop = await pinfo.value
        await pop.wait_for_load_state("domcontentloaded")
        await pop.wait_for_timeout(10000)
        await dump(pop, "popup")
        await pop.screenshot(path="demo/out/probe_popup.png", full_page=True)
        await b.close()


asyncio.run(main())
