#!/usr/bin/env python3
"""Interaction states + sticky header DOM investigation."""
import json, os
from playwright.sync_api import sync_playwright

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
BASE = "http://localhost:8099"
OUT = "/root/bestball/bestball/docs/design-audit/assets"
notes = {}

with sync_playwright() as p:
    b = p.chromium.launch()

    def ctx_page(w=1440, h=900):
        c = b.new_context(viewport={"width": w, "height": h})
        return c, c.new_page()

    # 1. command_center: inspect sticky header + click first player row + tab
    c, page = ctx_page()
    page.goto(f"{BASE}/command_center.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    notes["cc_sticky"] = page.evaluate("""() => {
      const thead = document.querySelector('thead');
      const table = thead && thead.closest('table');
      const out = {};
      if (thead) {
        const cs = getComputedStyle(thead.querySelector('th') || thead);
        const csr = getComputedStyle(thead);
        out.theadPos = csr.position; out.theadTop = csr.top;
        out.thPos = cs.position; out.thTop = cs.top;
        out.theadRectY = thead.getBoundingClientRect().y;
        const tb = table.querySelector('tbody tr');
        out.firstRowY = tb ? tb.getBoundingClientRect().y : null;
        out.theadIndexInTable = Array.from(table.children).map(x=>x.tagName).join(',');
      }
      // any element with position sticky
      const sticky = [];
      document.querySelectorAll('*').forEach(el => {
        const s = getComputedStyle(el);
        if (s.position === 'sticky' && sticky.length < 8)
          sticky.push({tag: el.tagName, cls: el.className.slice(0,60), top: s.top, y: Math.round(el.getBoundingClientRect().y)});
      });
      out.sticky = sticky;
      return out;
    }""")
    # click first player row to expand drilldown
    try:
        page.click("tbody tr", timeout=5000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/command_center_row_expanded.png")
    except Exception as e:
        notes["cc_row_click"] = str(e)[:200]
    # DFS Scenarios tab
    try:
        page.click("text=DFS Scenarios", timeout=5000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/command_center_dfs_tab.png")
    except Exception as e:
        notes["cc_tab_click"] = str(e)[:200]
    c.close()

    # 2. dossier: click BUF
    c, page = ctx_page()
    page.goto(f"{BASE}/dossier.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=BUF", timeout=5000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/dossier_team_selected.png")
    except Exception as e:
        notes["dossier_click"] = str(e)[:200]
    c.close()

    # 3. dossier_deep: click first player
    c, page = ctx_page()
    page.goto(f"{BASE}/dossier_deep.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=Puka Nacua", timeout=5000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/dossier_deep_player.png")
    except Exception as e:
        notes["dd_click"] = str(e)[:200]
    c.close()

    # 4. rankings: click EPA chip on first row
    c, page = ctx_page()
    page.goto(f"{BASE}/rankings.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=▸EPA", timeout=5000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/rankings_epa_expanded.png")
    except Exception as e:
        notes["rankings_epa"] = str(e)[:200]
    c.close()

    # 5. intel: click first player
    c, page = ctx_page()
    page.goto(f"{BASE}/intel.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=Jahmyr Gibbs", timeout=5000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/intel_player_selected.png")
    except Exception as e:
        notes["intel_click"] = str(e)[:200]
    c.close()

    # 6. team_dashboard: expand first team
    c, page = ctx_page()
    page.goto(f"{BASE}/team_dashboard.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=Detroit Lions", timeout=5000)
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/team_dashboard_expanded.png")
    except Exception as e:
        notes["team_expand"] = str(e)[:200]
    c.close()

    # 7. home: Offense dossier tab
    c, page = ctx_page()
    page.goto(f"{BASE}/home.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(1200)
    try:
        page.click("text=Offense dossier", timeout=5000)
        page.wait_for_timeout(1000)
        page.screenshot(path=f"{OUT}/home_offense_tab.png")
    except Exception as e:
        notes["home_tab"] = str(e)[:200]
    c.close()

    # 8. player_explorer: click EPA + CONTEXT drilldown
    c, page = ctx_page()
    page.goto(f"{BASE}/player_explorer.html", wait_until="load", timeout=90000)
    page.wait_for_timeout(2000)
    try:
        page.click("text=EPA + CONTEXT", timeout=5000)
        page.wait_for_timeout(1500)
        page.screenshot(path=f"{OUT}/player_explorer_epa_context.png")
    except Exception as e:
        notes["pe_epa"] = str(e)[:200]
    c.close()

    b.close()

print(json.dumps(notes, indent=1))
