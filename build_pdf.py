#!/usr/bin/env python3
"""
Build bestball_2026_team_analysis.pdf from the four team analysis markdown files.
Toolchain: reportlab (Platypus) with HTML-style paragraph markup.
"""

import json
import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable

# ── Brand colours ──────────────────────────────────────────────────────────────
BRAND_GREEN   = colors.HexColor("#003c33")  # deep green
ELITE_BG      = colors.HexColor("#004d3d")  # deep-green
ELITE_FG      = colors.white
HIGH_BG       = colors.HexColor("#1a7a5e")  # mint/teal
HIGH_FG       = colors.white
MID_BG        = colors.HexColor("#4a6fa5")  # slate-blue
MID_FG        = colors.white
LOW_BG        = colors.HexColor("#b85c3c")  # coral
LOW_FG        = colors.white

TIER_BG  = {"ELITE": ELITE_BG, "HIGH": HIGH_BG, "MID": MID_BG, "LOW": LOW_BG}
TIER_FG  = {"ELITE": ELITE_FG, "HIGH": HIGH_FG, "MID": MID_FG, "LOW": LOW_FG}

BODY_DARK   = colors.HexColor("#1a1a1a")
RULE_LIGHT  = colors.HexColor("#dddddd")
PAGE_BG     = colors.white

# ── Load ceiling data ───────────────────────────────────────────────────────────
BASE = "/root/bestball/bestball"
with open(f"{BASE}/team_ceiling.json") as f:
    ceiling_raw = json.load(f)
CEILING = ceiling_raw["teams"]   # dict keyed by abbr

ADP_DATE = "2026-07-02"          # from stack_menu._meta.built and slot_paths._meta.built_date

# ── Correct alphabetical order ─────────────────────────────────────────────────
TEAM_ORDER = [
    "Arizona Cardinals",
    "Atlanta Falcons",
    "Baltimore Ravens",
    "Buffalo Bills",
    "Carolina Panthers",
    "Chicago Bears",
    "Cincinnati Bengals",
    "Cleveland Browns",
    "Dallas Cowboys",
    "Denver Broncos",
    "Detroit Lions",
    "Green Bay Packers",
    "Houston Texans",
    "Indianapolis Colts",
    "Jacksonville Jaguars",
    "Kansas City Chiefs",
    "Las Vegas Raiders",
    "Los Angeles Chargers",
    "Los Angeles Rams",
    "Miami Dolphins",
    "Minnesota Vikings",
    "New England Patriots",
    "New Orleans Saints",
    "New York Giants",
    "New York Jets",
    "Philadelphia Eagles",
    "Pittsburgh Steelers",
    "San Francisco 49ers",
    "Seattle Seahawks",
    "Tampa Bay Buccaneers",
    "Tennessee Titans",
    "Washington Commanders",
]

# abbreviation lookup
ABBR_MAP = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

# ── Parse the four markdown files ──────────────────────────────────────────────
MD_FILES = [
    f"{BASE}/analysis/team_analysis_1.md",
    f"{BASE}/analysis/team_analysis_2.md",
    f"{BASE}/analysis/team_analysis_3.md",
    f"{BASE}/analysis/team_analysis_4.md",
]

def parse_md_files(paths):
    """Return dict: full_team_name -> list of (subsection_label, body_text) pairs."""
    teams = {}
    current_team = None
    current_subsec = None
    current_body = []

    def flush_subsec():
        if current_team and current_subsec is not None:
            teams[current_team].append((current_subsec, "\n".join(current_body).strip()))

    for path in paths:
        with open(path) as f:
            raw = f.read()
        # Split into lines
        for line in raw.splitlines():
            # Team header: ## Full Team Name (ABBR)
            m = re.match(r'^##\s+(.+?)\s*\(([A-Z]+)\)\s*$', line)
            if m:
                flush_subsec()
                full_name = m.group(1).strip()
                current_team = full_name
                current_subsec = None
                current_body = []
                if full_name not in teams:
                    teams[full_name] = []
                continue

            # Numbered heading (Set 4 format): "1. **Verdict.**" etc.
            m_num = re.match(r'^\d+\.\s+\*\*(.+?)\*\*(.*)$', line)
            # Regular subsection: "**Verdict.**" at start of line
            m_sub = re.match(r'^\*\*([A-Za-z][^*]+?)\*\*[.\s]?(.*)', line)

            if current_team and (m_num or m_sub):
                label_candidate = (m_num.group(1) if m_num else m_sub.group(1)).strip()
                known_labels = [
                    "Verdict", "Full-season environment", "Schedule arc",
                    "Key fantasy players", "Stacks & correlation", "Draft takeaway",
                    "Schedule arc — full season",
                ]
                # normalise: strip trailing period/dots
                label_clean = label_candidate.rstrip(". ")
                # check if it matches one of the six subsection types
                is_subsec = any(
                    label_clean.lower().startswith(kl.lower().rstrip(". ")) or
                    kl.lower().rstrip(". ").startswith(label_clean.lower())
                    for kl in known_labels
                )
                if not is_subsec and label_clean.lower() in [
                    "verdict", "full-season environment",
                    "schedule arc", "schedule arc — full season",
                    "key fantasy players", "stacks & correlation",
                    "draft takeaway"
                ]:
                    is_subsec = True

                if is_subsec or label_clean.lower() in [
                    "verdict", "full-season environment",
                    "schedule arc", "schedule arc — full season",
                    "key fantasy players", "stacks & correlation",
                    "draft takeaway"
                ]:
                    flush_subsec()
                    current_subsec = label_clean
                    # remainder of the line is part of the body
                    if m_num:
                        rest = m_num.group(2).strip()
                    else:
                        rest = m_sub.group(2).strip()
                    current_body = [rest] if rest else []
                    continue

            # Skip file-level preamble (before first ## team header)
            if current_team is None:
                continue

            # Accumulate body
            current_body.append(line)

    flush_subsec()
    return teams

TEAM_DATA = parse_md_files(MD_FILES)
print(f"Parsed {len(TEAM_DATA)} teams")
missing = [t for t in TEAM_ORDER if t not in TEAM_DATA]
extra   = [t for t in TEAM_DATA if t not in TEAM_ORDER]
if missing:
    print(f"MISSING teams: {missing}")
if extra:
    print(f"UNEXPECTED teams: {extra}")

# ── Markdown → ReportLab paragraph markup ──────────────────────────────────────
def md_to_rl(text: str) -> str:
    """Convert lightweight markdown to ReportLab XML markup."""
    # escape XML chars first (but not & that are already entities)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    # bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # italic: *text*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text

def body_lines_to_paragraphs(raw_body: str, styles) -> list:
    """Convert a multi-line body string into a list of Platypus Flowables."""
    flowables = []
    lines = raw_body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # blank line
        if not line.strip():
            i += 1
            continue

        # horizontal rule
        if re.match(r'^[-*]{3,}$', line.strip()):
            i += 1
            continue

        # bullet: "- " or "  - "
        m_bullet = re.match(r'^(\s*)[-*]\s+(.+)$', line)
        if m_bullet:
            indent = len(m_bullet.group(1))
            bullet_text = m_bullet.group(2)
            # collect continuation lines (indented more than bullet or continuation)
            while i + 1 < len(lines):
                nxt = lines[i+1]
                if re.match(r'^\s{2,}', nxt) and not re.match(r'^\s*[-*]\s', nxt):
                    bullet_text += " " + nxt.strip()
                    i += 1
                else:
                    break
            style = styles['BulletBody'] if indent == 0 else styles['BulletBodyIndent']
            p = Paragraph(md_to_rl(bullet_text), style)
            flowables.append(p)
            i += 1
            continue

        # numbered list: "1. " etc.
        m_num = re.match(r'^(\s*)\d+\.\s+(.+)$', line)
        if m_num:
            num_text = m_num.group(2)
            while i + 1 < len(lines):
                nxt = lines[i+1]
                if re.match(r'^\s{3,}', nxt) and not re.match(r'^\s*\d+\.', nxt):
                    num_text += " " + nxt.strip()
                    i += 1
                else:
                    break
            p = Paragraph(md_to_rl(num_text), styles['BulletBody'])
            flowables.append(p)
            i += 1
            continue

        # sub-bullet inside numbered list body (sub-item with leading spaces)
        m_sub_bullet = re.match(r'^\s{3,}[-*]\s+(.+)$', line)
        if m_sub_bullet:
            sub_text = m_sub_bullet.group(1)
            p = Paragraph(md_to_rl(sub_text), styles['BulletBodyIndent'])
            flowables.append(p)
            i += 1
            continue

        # regular paragraph line — collect until blank or bullet
        para_lines = [line]
        while i + 1 < len(lines):
            nxt = lines[i+1].rstrip()
            if (not nxt.strip() or
                re.match(r'^\s*[-*]\s', nxt) or
                re.match(r'^\s*\d+\.\s', nxt) or
                re.match(r'^[-*]{3,}$', nxt.strip())):
                break
            para_lines.append(nxt)
            i += 1
        full_para = " ".join(l.strip() for l in para_lines if l.strip())
        if full_para:
            p = Paragraph(md_to_rl(full_para), styles['BodyText'])
            flowables.append(p)
        i += 1

    return flowables


# ── Custom Flowable: Tier Chip ──────────────────────────────────────────────────
class TierChip(Flowable):
    def __init__(self, tier, width=68, height=16):
        super().__init__()
        self.tier = tier
        self.width = width
        self.height = height

    def draw(self):
        bg = TIER_BG.get(self.tier, colors.grey)
        fg = TIER_FG.get(self.tier, colors.white)
        self.canv.setFillColor(bg)
        self.canv.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        self.canv.setFillColor(fg)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawCentredString(self.width / 2, self.height / 2 - 3, self.tier)

    def wrap(self, availW, availH):
        return self.width, self.height


# ── Page templates (header/footer) ─────────────────────────────────────────────
_current_team_name = [""]   # mutable container so callback can read it

class _SetTeamName(Flowable):
    """Zero-height flowable that records the team name at render time."""
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.width = 0
        self.height = 0

    def draw(self):
        _current_team_name[0] = self.name

    def wrap(self, aW, aH):
        return 0, 0


def make_page_number_canvas(canvas, doc):
    """Draw footer with page number and current team name."""
    canvas.saveState()
    w, h = letter
    # footer line
    canvas.setStrokeColor(RULE_LIGHT)
    canvas.setLineWidth(0.5)
    canvas.line(inch * 0.75, 0.55 * inch, w - inch * 0.75, 0.55 * inch)
    # page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(w / 2, 0.35 * inch, f"Page {doc.page}")
    # team name in footer (set by _SetTeamName flowable at render time)
    if _current_team_name[0]:
        canvas.drawString(inch * 0.75, 0.35 * inch, _current_team_name[0])
    canvas.restoreState()


# ── Style registry ─────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    styles = {}

    # Title (cover page)
    styles['CoverTitle'] = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=BRAND_GREEN,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    styles['CoverSubtitle'] = ParagraphStyle(
        'CoverSubtitle',
        fontName='Helvetica',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#444444"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    styles['CoverDate'] = ParagraphStyle(
        'CoverDate',
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=24,
    )
    styles['CoverMethodology'] = ParagraphStyle(
        'CoverMethodology',
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=BODY_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
        leftIndent=18,
        rightIndent=18,
    )

    # Section header (team name + score line)
    styles['TeamHeader'] = ParagraphStyle(
        'TeamHeader',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=BRAND_GREEN,
        spaceAfter=2,
        spaceBefore=4,
    )
    styles['TeamMeta'] = ParagraphStyle(
        'TeamMeta',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )

    # Subsection label
    styles['SubLabel'] = ParagraphStyle(
        'SubLabel',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=BRAND_GREEN,
        spaceBefore=8,
        spaceAfter=2,
    )

    # Body text
    styles['BodyText'] = ParagraphStyle(
        'BodyText',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=BODY_DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=4,
    )

    # Bullet body
    styles['BulletBody'] = ParagraphStyle(
        'BulletBody',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=BODY_DARK,
        leftIndent=14,
        firstLineIndent=-10,
        bulletIndent=4,
        spaceAfter=3,
    )
    styles['BulletBodyIndent'] = ParagraphStyle(
        'BulletBodyIndent',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=BODY_DARK,
        leftIndent=26,
        firstLineIndent=-10,
        spaceAfter=2,
    )

    # TOC / Legend table cell styles
    styles['TOCHead'] = ParagraphStyle(
        'TOCHead',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )
    styles['TOCCell'] = ParagraphStyle(
        'TOCCell',
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=BODY_DARK,
    )
    styles['TOCCellBold'] = ParagraphStyle(
        'TOCCellBold',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=BODY_DARK,
    )

    # Legend heading
    styles['LegendTitle'] = ParagraphStyle(
        'LegendTitle',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=BRAND_GREEN,
        spaceBefore=18,
        spaceAfter=6,
    )

    return styles

STYLES = make_styles()


# ── TOC / Legend ───────────────────────────────────────────────────────────────
def build_toc_table():
    """32-row table: Rank | Team | Tier | Score."""
    header = [
        Paragraph("Rank", STYLES['TOCHead']),
        Paragraph("Team", STYLES['TOCHead']),
        Paragraph("Tier", STYLES['TOCHead']),
        Paragraph("Score", STYLES['TOCHead']),
    ]
    rows = [header]

    # Sort by alpha for TOC display
    for full_name in TEAM_ORDER:
        abbr = ABBR_MAP[full_name]
        cd = CEILING.get(abbr, {})
        rank = cd.get('rank', '?')
        score = cd.get('ceiling_score', 0)
        tier = cd.get('tier', 'MID')
        bg = TIER_BG.get(tier, colors.grey)

        rows.append([
            Paragraph(str(rank), STYLES['TOCCell']),
            Paragraph(f"{full_name} ({abbr})", STYLES['TOCCellBold']),
            Paragraph(tier, STYLES['TOCCell']),
            Paragraph(f"{score:.1f}", STYLES['TOCCell']),
        ])

    col_widths = [0.5*inch, 3.5*inch, 0.85*inch, 0.75*inch]
    t = Table(rows, colWidths=col_widths)

    # Build per-row styles
    ts_cmds = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]
    # Color the tier column cell background per tier
    for row_idx, full_name in enumerate(TEAM_ORDER, start=1):
        abbr = ABBR_MAP[full_name]
        tier = CEILING.get(abbr, {}).get('tier', 'MID')
        bg = TIER_BG.get(tier, colors.grey)
        fg = TIER_FG.get(tier, colors.white)
        ts_cmds.append(('BACKGROUND', (2, row_idx), (2, row_idx), bg))
        ts_cmds.append(('TEXTCOLOR', (2, row_idx), (2, row_idx), fg))
        ts_cmds.append(('FONTNAME', (2, row_idx), (2, row_idx), 'Helvetica-Bold'))
        ts_cmds.append(('ALIGNMENT', (2, row_idx), (2, row_idx), 'CENTER'))

    t.setStyle(TableStyle(ts_cmds))
    return t


# ── Per-team section ───────────────────────────────────────────────────────────
SUBSEC_DISPLAY = {
    "Verdict": "Verdict",
    "Full-season environment": "Full-Season Environment",
    "Schedule arc": "Schedule Arc — Full Season",
    "Schedule arc — full season": "Schedule Arc — Full Season",
    "Key fantasy players": "Key Fantasy Players",
    "Stacks & correlation": "Stacks & Correlation",
    "Draft takeaway": "Draft Takeaway",
}

def normalise_subsec(label: str) -> str:
    clean = label.strip().rstrip(". ")
    for k in SUBSEC_DISPLAY:
        if clean.lower() == k.lower():
            return SUBSEC_DISPLAY[k]
    # partial match
    for k in SUBSEC_DISPLAY:
        if clean.lower().startswith(k.lower()[:8]):
            return SUBSEC_DISPLAY[k]
    return clean.title()


def build_team_section(full_name: str) -> list:
    """Return list of Platypus flowables for one team."""
    abbr = ABBR_MAP[full_name]
    cd = CEILING.get(abbr, {})
    tier = cd.get('tier', 'MID')
    score = cd.get('ceiling_score', 0)
    rank = cd.get('rank', '?')
    bg = TIER_BG.get(tier, colors.grey)
    fg = TIER_FG.get(tier, colors.white)

    flowables = []

    # Set team name for footer at render time
    flowables.append(_SetTeamName(full_name))

    # ── Team header band ───────────────────────────────────────────────
    # Tier colour rule at top
    flowables.append(HRFlowable(
        width="100%", thickness=4, color=bg, spaceAfter=4, spaceBefore=0
    ))

    # Team name
    header_txt = f"{full_name} <font color='#888888' size='11'>({abbr})</font>"
    flowables.append(Paragraph(header_txt, STYLES['TeamHeader']))

    # Tier chip + score/rank on same line via a small table
    chip_label = f"<b>{tier}</b>"
    chip_style = ParagraphStyle(
        'ChipInline', fontName='Helvetica-Bold', fontSize=9,
        textColor=fg, backColor=bg,
        leftIndent=4, rightIndent=4, spaceBefore=1, spaceAfter=1,
        borderPadding=3,
    )
    meta_txt = (
        f"Ceiling Score <b>{score:.1f}</b> &nbsp;|&nbsp; "
        f"Rank <b>{rank}/32</b> &nbsp;|&nbsp; Tier "
        f"<b><font backColor='{bg.hexval()}' color='{fg.hexval()}'>"
        f" {tier} </font></b>"
    )
    flowables.append(Paragraph(meta_txt, STYLES['TeamMeta']))

    # Rule under header
    flowables.append(HRFlowable(
        width="100%", thickness=0.75, color=bg, spaceAfter=6, spaceBefore=2
    ))

    # ── Subsections ────────────────────────────────────────────────────
    subsections = TEAM_DATA.get(full_name, [])
    for label, body in subsections:
        disp = normalise_subsec(label)
        flowables.append(Paragraph(disp, STYLES['SubLabel']))
        body_flows = body_lines_to_paragraphs(body, STYLES)
        flowables.extend(body_flows)
        flowables.append(Spacer(1, 3))

    return flowables


# ── Assemble document ──────────────────────────────────────────────────────────
OUTPUT_PATH = f"{BASE}/bestball_2026_team_analysis.pdf"

doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.75 * inch,
    bottomMargin=0.75 * inch,
    title="2026 Best Ball — Full-Season Team Analysis",
    author="2026 Best Ball Model",
    subject="32-team draft guide",
)

story = []

# ══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════
story.append(_SetTeamName(""))
story.append(Spacer(1, 1.2 * inch))

# Top rule
story.append(HRFlowable(width="100%", thickness=3, color=BRAND_GREEN, spaceAfter=18))

story.append(Paragraph("2026 Best Ball", STYLES['CoverTitle']))
story.append(Paragraph("Full-Season Team Analysis", STYLES['CoverTitle']))
story.append(Spacer(1, 0.15 * inch))
story.append(Paragraph(
    "32-Team Draft Guide · Ceiling Tiers · Full-Season Outlook &amp; Stacks",
    STYLES['CoverSubtitle']
))

story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_GREEN, spaceAfter=14))

story.append(Paragraph(
    f"ADP Snapshot Date: {ADP_DATE} &nbsp;|&nbsp; Underdog Best Ball Mania VII",
    STYLES['CoverDate']
))

story.append(Spacer(1, 0.3 * inch))

story.append(Paragraph("Methodology", ParagraphStyle(
    'MethodHead', fontName='Helvetica-Bold', fontSize=11,
    textColor=BRAND_GREEN, alignment=TA_CENTER, spaceAfter=8
)))
methodology = (
    "This guide is model-grounded, built on per-team ceiling-season probability "
    "scores (0–100 relative scale) derived from offensive-environment quality, "
    "win-total projections, pace, pass-rate, QB trajectory, scheme changes, "
    "and shootout-script likelihood. All analysis is framed for the full Underdog "
    "Best Ball Mania VII structure: Weeks 1–14 accumulate to ADVANCE (top-2 of 12 "
    "teams); Weeks 15–17 are single-elimination rounds to WIN the championship. "
    "Ceiling tiers (ELITE / HIGH / MID / LOW) represent ceiling-season <i>upside</i> "
    "probability — the likelihood a team's offense dramatically overperforms "
    "its projection — not expected value. ADP figures are Underdog ADP sourced "
    "via ffdataroma export. Adjusted ranks reflect model nudges (capped ±8 ADP "
    "spots) layered on market price. Stack scores are correlation-weighted "
    "combination values from the repo's stack-menu model. All figures are "
    "forward-looking 2026 signals."
)
story.append(Paragraph(methodology, STYLES['CoverMethodology']))

story.append(HRFlowable(width="100%", thickness=1, color=RULE_LIGHT, spaceAfter=10))

# Tier legend boxes
legend_data = [
    [
        Paragraph("<b>ELITE</b>", ParagraphStyle('LE', fontName='Helvetica-Bold', fontSize=9, textColor=ELITE_FG)),
        Paragraph("Top 6 teams — premier ceiling environments; concentrate &amp; stack.", STYLES['CoverMethodology']),
    ],
    [
        Paragraph("<b>HIGH</b>", ParagraphStyle('LH', fontName='Helvetica-Bold', fontSize=9, textColor=HIGH_FG)),
        Paragraph("Next 8 — strong environments; selective concentration.", STYLES['CoverMethodology']),
    ],
    [
        Paragraph("<b>MID</b>", ParagraphStyle('LM', fontName='Helvetica-Bold', fontSize=9, textColor=MID_FG)),
        Paragraph("Middle 12 — mixed; mine individuals or cheap stacks.", STYLES['CoverMethodology']),
    ],
    [
        Paragraph("<b>LOW</b>", ParagraphStyle('LL', fontName='Helvetica-Bold', fontSize=9, textColor=LOW_FG)),
        Paragraph("Bottom 6 — fade the team; roster studs on their own merits.", STYLES['CoverMethodology']),
    ],
]
legend_col_w = [0.9*inch, 5.0*inch]
legend_tbl = Table(legend_data, colWidths=legend_col_w)
legend_tbl.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (0, 0), ELITE_BG),
    ('BACKGROUND', (0, 1), (0, 1), HIGH_BG),
    ('BACKGROUND', (0, 2), (0, 2), MID_BG),
    ('BACKGROUND', (0, 3), (0, 3), LOW_BG),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
]))
story.append(legend_tbl)

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# CEILING-TIER TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════════════
story.append(_SetTeamName(""))
story.append(Paragraph(
    "Ceiling-Tier Legend &amp; Table of Contents",
    ParagraphStyle('TocPageTitle', fontName='Helvetica-Bold', fontSize=16,
                   textColor=BRAND_GREEN, spaceAfter=8, leading=20)
))
story.append(Paragraph(
    "Teams listed alphabetically by city name. Tier colours: "
    "<font color='#004d3d'><b>ELITE</b></font> (deep green) · "
    "<font color='#1a7a5e'><b>HIGH</b></font> (teal) · "
    "<font color='#4a6fa5'><b>MID</b></font> (slate) · "
    "<font color='#b85c3c'><b>LOW</b></font> (coral). "
    "Score = ceiling-season probability (0–100 relative scale). "
    "Rank = ceiling rank out of 32 teams.",
    STYLES['BodyText']
))
story.append(Spacer(1, 6))
story.append(build_toc_table())

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PER-TEAM SECTIONS (alphabetical)
# ══════════════════════════════════════════════════════════════════════════════
for idx, full_name in enumerate(TEAM_ORDER):
    section_flows = build_team_section(full_name)
    # Keep the team header together with first subsection
    story.append(KeepTogether(section_flows[:8]))
    if len(section_flows) > 8:
        story.extend(section_flows[8:])
    # Page break after each team (except last)
    if idx < len(TEAM_ORDER) - 1:
        story.append(PageBreak())

# ── Build ──────────────────────────────────────────────────────────────────────
doc.build(story, onFirstPage=make_page_number_canvas, onLaterPages=make_page_number_canvas)
print(f"\nPDF written to: {OUTPUT_PATH}")
print(f"File size: {os.path.getsize(OUTPUT_PATH):,} bytes")
