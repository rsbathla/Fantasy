#!/usr/bin/env python3
"""Design-audit screenshot harness: desktop+mobile shots + console capture."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
BASE = "http://localhost:8099"
OUT = "/root/bestball/bestball/docs/design-audit/assets"
LOG = "/root/bestball/bestball/docs/design-audit/console_log.json"

PAGES = [
    ("home", "home.html"),
    ("command_center", "command_center.html"),
    ("rankings", "rankings.html"),
    ("adp_cluster_board", "adp_cluster_board.html"),
    ("big_board", "big_board_2026.html"),
    ("dossier", "dossier.html"),
    ("dossier_deep", "dossier_deep.html"),
    ("player_explorer", "player_explorer.html"),
    ("lever_board", "lever_board.html"),
    ("upside_cases", "upside_cases.html"),
    ("dfs_week", "dfs_week.html"),
    ("pick_dashboard", "pick_dashboard.html"),
    ("decision_dashboard", "decision_dashboard.html"),
    ("team_dashboard", "team_dashboard.html"),
    ("team_scout", "team_scout.html"),
    ("intel", "intel.html"),
]

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}

def main(only=None):
    results = {}
    if os.path.exists(LOG):
        with open(LOG) as f:
            results = json.load(f)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fname in PAGES:
            if only and name not in only:
                continue
            results[name] = {"file": fname}
            for vp_name, (w, h) in VIEWPORTS.items():
                ctx = browser.new_context(viewport={"width": w, "height": h},
                                          device_scale_factor=1)
                page = ctx.new_page()
                console_msgs, page_errors = [], []
                page.on("console", lambda m, c=console_msgs: c.append(
                    {"type": m.type, "text": m.text[:300]}))
                page.on("pageerror", lambda e, c=page_errors: c.append(str(e)[:300]))
                t0 = time.time()
                try:
                    page.goto(f"{BASE}/{fname}", wait_until="load", timeout=90000)
                    page.wait_for_timeout(2500)
                    load_s = round(time.time() - t0, 1)
                    metrics = page.evaluate("""() => ({
                        scrollW: document.documentElement.scrollWidth,
                        scrollH: document.documentElement.scrollHeight,
                        innerW: window.innerWidth,
                        title: document.title,
                        hasViewportMeta: !!document.querySelector('meta[name=viewport]'),
                        nLinks: document.querySelectorAll('a[href]').length,
                        bodyTextLen: (document.body.innerText||'').length
                    })""")
                    shot = f"{OUT}/{name}_{vp_name}.png"
                    page.screenshot(path=shot)
                    results[name][vp_name] = {
                        "load_s": load_s, "metrics": metrics,
                        "console": [m for m in console_msgs if m["type"] in ("error", "warning")][:15],
                        "console_all_count": len(console_msgs),
                        "pageerrors": page_errors[:10],
                    }
                except Exception as e:
                    results[name][vp_name] = {"ERROR": str(e)[:400],
                                              "console": console_msgs[:15],
                                              "pageerrors": page_errors[:10]}
                ctx.close()
            print(name, "done", flush=True)
        browser.close()
    with open(LOG, "w") as f:
        json.dump(results, f, indent=1)
    print("ALL DONE")

if __name__ == "__main__":
    only = set(sys.argv[1:]) or None
    main(only)
