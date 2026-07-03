#!/usr/bin/env python3
"""render_dfs_weekly_pdf.py — render dfs_weekly_breakdown.md -> dfs_weekly_breakdown.pdf

House style (deep enterprise green), reportlab/Platypus. Each week starts on a fresh
page so the document reads as actual per-week breakdowns. Pure formatter — it renders
the written breakdown build_dfs_weekly_breakdown.py already produced; no data logic here.
"""
import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                HRFlowable)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'dfs_weekly_breakdown.md')
OUT = os.path.join(HERE, 'dfs_weekly_breakdown.pdf')

BRAND = colors.HexColor("#003c33")
ACCENT = colors.HexColor("#1a7a5e")
BODY = colors.HexColor("#1a1a1a")
MUTE = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#cfd8d4")

ss = getSampleStyleSheet()
S = {}
S['Title'] = ParagraphStyle('Title', parent=ss['Title'], textColor=BRAND, fontName='Helvetica-Bold',
                            fontSize=22, leading=26, spaceAfter=6)
S['Intro'] = ParagraphStyle('Intro', parent=ss['BodyText'], textColor=MUTE, fontName='Helvetica-Oblique',
                            fontSize=9.5, leading=13, spaceAfter=8)
S['H2'] = ParagraphStyle('H2', parent=ss['Heading2'], textColor=colors.white, fontName='Helvetica-Bold',
                         fontSize=15, leading=18, spaceBefore=2, spaceAfter=8,
                         backColor=BRAND, borderPadding=(6, 8, 6, 8), leftIndent=0)
S['H3'] = ParagraphStyle('H3', parent=ss['Heading3'], textColor=BRAND, fontName='Helvetica-Bold',
                         fontSize=11.5, leading=14, spaceBefore=9, spaceAfter=3)
S['Body'] = ParagraphStyle('Body', parent=ss['BodyText'], textColor=BODY, fontName='Helvetica',
                           fontSize=9.5, leading=13.5, spaceAfter=5, alignment=TA_JUSTIFY)
S['Bullet'] = ParagraphStyle('Bullet', parent=S['Body'], leftIndent=14, bulletIndent=3, spaceAfter=4)
S['Num'] = ParagraphStyle('Num', parent=S['Body'], leftIndent=16, spaceAfter=5)
S['Glossary'] = ParagraphStyle('Glossary', parent=S['Body'], leftIndent=14, bulletIndent=3, spaceAfter=4)

def esc(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', t)
    t = t.replace('`', '')
    return t

def render():
    md = open(SRC, encoding='utf-8').read()
    lines = md.splitlines()
    flow = []
    i = 0
    first_week_seen = False
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1; continue
        if s.startswith('# ') and not s.startswith('## '):
            flow.append(Paragraph(esc(s[2:]), S['Title']))
            i += 1; continue
        if s.startswith('## '):
            # each week / major section on a fresh page (except the very first section)
            if first_week_seen:
                flow.append(PageBreak())
            first_week_seen = True
            flow.append(Paragraph(esc(s[3:]), S['H2']))
            flow.append(Spacer(1, 4))
            i += 1; continue
        if re.match(r'^---+$', s):
            flow.append(Spacer(1, 3)); flow.append(HRFlowable(width='100%', color=RULE, thickness=0.6))
            flow.append(Spacer(1, 3)); i += 1; continue
        # standalone bold-led subheads that we want as H3 (e.g. "**The slate.** ...") stay as body,
        # but a line that is ONLY *italic* intro -> Intro style
        if s.startswith('*') and s.endswith('*') and not s.startswith('**'):
            flow.append(Paragraph(esc(s), S['Intro'])); i += 1; continue
        # bullet
        m = re.match(r'^-\s+(.*)$', s)
        if m:
            flow.append(Paragraph(esc(m.group(1)), S['Bullet'], bulletText='•'))
            i += 1; continue
        # numbered list item
        m = re.match(r'^(\d+)\.\s+(.*)$', s)
        if m:
            flow.append(Paragraph(f"<b>{m.group(1)}.</b> " + esc(m.group(2)), S['Num']))
            i += 1; continue
        # regular paragraph (single md line already = one logical paragraph here)
        flow.append(Paragraph(esc(s), S['Body']))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7.5); canvas.setFillColor(MUTE)
        canvas.drawString(0.7*inch, 0.45*inch, "2026 DFS — Written Weekly Breakdowns · forward-looking baseline")
        canvas.drawRightString(letter[0]-0.7*inch, 0.45*inch, f"{doc.page}")
        canvas.setStrokeColor(RULE); canvas.setLineWidth(0.5)
        canvas.line(0.7*inch, 0.6*inch, letter[0]-0.7*inch, 0.6*inch)
        canvas.restoreState()

    doc = SimpleDocTemplate(OUT, pagesize=letter, topMargin=0.7*inch, bottomMargin=0.8*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch,
                            title="2026 DFS Weekly Breakdowns", author="bestball")
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    sz = os.path.getsize(OUT)
    print(f"dfs_weekly_breakdown.pdf: {sz:,} bytes | {len(flow)} flowables")

if __name__ == '__main__':
    render()
