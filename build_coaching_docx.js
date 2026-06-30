const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType } = require('docx');
const fs = require('fs');

const ACCENT = "2E5090";
const H = (text, level) => new Paragraph({ heading: level, children: [new TextRun(text)] });
const P = (runs) => new Paragraph({ spacing: { after: 120 }, children: Array.isArray(runs) ? runs : [new TextRun(runs)] });
const T = (t, opt={}) => new TextRun({ text: t, ...opt });
const bullet = (runs) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 40 },
  children: Array.isArray(runs) ? runs : [new TextRun(runs)] });

// A play-caller profile: bold header + labeled bullets
function profile(team, head, items) {
  const out = [ new Paragraph({ spacing: { before: 120, after: 40 },
    children: [ T(team + " — ", { bold: true, color: ACCENT }), T(head, { bold: true }) ] }) ];
  for (const [label, body] of items) {
    out.push(new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 30 },
      children: [ T(label + ": ", { bold: true }), T(body) ] }));
  }
  return out;
}

const children = [];
// ---- Title ----
children.push(new Paragraph({ spacing: { after: 60 }, children: [ T("2026 NFL Coaching Changes & Playcaller Guide", { bold: true, size: 40, color: ACCENT }) ] }));
children.push(new Paragraph({ spacing: { after: 200 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } },
  children: [ T("Built for fantasy / Best-Ball prep — who actually calls the plays, their scheme, and what it moves. ", { italics: true, size: 20 }),
              T("Coordinator list CBS-sourced & web-verified (June 2026); BAL DC confirmed (Minter). Not re-verified live this session.", { italics: true, size: 20, color: "888888" }) ] }));

// ---- Thesis ----
children.push(H("The one thing that matters: who calls the plays", HeadingLevel.HEADING_1));
children.push(P([ T("A new offensive coordinator only changes the offense if he actually calls the plays. League-wide, "),
  T("18 of 32 head coaches call their own offense", { bold: true }),
  T("; only 8 teams are “HC-as-CEO” where a coordinator runs it. So of the 21 OC-title changes in 2026, only ~14 actually move the offense — 4 of those are really head-coach hires, and ~6 are noise (continuity). Attribute the offense to the play-caller, not the title.") ]));
children.push(P([ T("The dominant pattern: most of the real new offenses are "),
  T("Shanahan / McVay tree", { bold: true }),
  T(" (LAC, MIA, ATL, ARI, LV, TB, SEA). Their shared signature — quick game + heavy play-action, pre-snap motion, under-center, zone run, RBs in the pass game — raises efficiency and pass-catching-back value, "),
  T("spreads target distribution", { bold: true }),
  T(" (tempers WR1 target concentration), and compresses raw pass rate. Clay’s pass% prices volume, not these distribution effects.") ]));

// ---- Summary buckets table ----
children.push(H("Who calls the plays — at a glance", HeadingLevel.HEADING_1));
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
function row(c1, c2, shade) {
  return new TableRow({ children: [
    new TableCell({ borders, width: { size: 2600, type: WidthType.DXA }, shading: shade?{fill:shade,type:ShadingType.CLEAR}:undefined,
      margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [ new Paragraph({ children: [ T(c1, { bold: !!shade }) ] }) ] }),
    new TableCell({ borders, width: { size: 6760, type: WidthType.DXA }, shading: shade?{fill:shade,type:ShadingType.CLEAR}:undefined,
      margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [ new Paragraph({ children: [ T(c2, { bold: !!shade }) ] }) ] }),
  ]});
}
children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2600, 6760], rows: [
  row("Bucket", "Teams", "D5E8F0"),
  row("New HC runs offense", "ARI (LaFleur), CLE (Monken), LV (Kubiak), PIT (McCarthy)"),
  row("New OC genuinely calls it", "ATL (Rees/Stefanski), CAR (Idzik), DEN (Webb), DET (Petzing), LAC (McDaniel), MIA (Slowik), NYG (Nagy), NYJ (Reich), TB (Z. Robinson), TEN (Daboll)"),
  row("First-time callers — widen error bars", "BAL (Doyle), PHI (Mannion), SEA (Fleury), WAS (Blough)"),
  row("Continuity — ignore the OC headline", "BUF (Brady), KC (Reid), LAR (McVay), CHI (Ben Johnson), DAL (Schottenheimer), GB (M. LaFleur)"),
]}));

// ---- Offensive profiles ----
children.push(H("Offensive playcaller profiles", HeadingLevel.HEADING_1));
children.push(H("New head coach calls the offense", HeadingLevel.HEADING_2));
profile("ARI", "Mike LaFleur (HC, new; Gannon fired) — OC Hackett does NOT call plays", [
  ["Tree", "Shanahan/Kyle (ex-SF/NYJ OC)"],
  ["Scheme", "wide-zone + heavy play-action, pre-snap motion, under-center looks"],
  ["Fantasy", "Murray gone → pocket-QB fit; efficiency should rise but target distribution spreads — temper any Cardinal WR1’s target concentration. Do not model as “Hackett’s offense.”"],
]).forEach(p=>children.push(p));
profile("CLE", "Todd Monken (HC, new)", [
  ["Tree", "Air Coryell (vertical)"],
  ["Scheme", "vertical play-action, ~68% motion (high), RBs featured — the one genuinely vertical new offense here"],
  ["Fantasy", "downfield + motion = WR aDOT/ceiling friendly; RBs stay involved. Was elite for Lamar in BAL — which is why BAL replacing him is a downgrade (below)."],
]).forEach(p=>children.push(p));
profile("LV", "Klint Kubiak (HC, new; Janocko is titular OC)", [
  ["Tree", "Shanahan/Kubiak"],
  ["Scheme", "wide-zone, heavy motion + 12-personnel, deep PA bootlegs, ~27.9% play-action, RBs as receivers (made rookie Kamara elite)"],
  ["Fantasy", "Ashton Jeanty is the clean winner. Brock Bowers gets a PA/TE bump but soften it — rookie QB likely means a conservative “tight-to-the-vest” Year 1."],
]).forEach(p=>children.push(p));
profile("PIT", "Mike McCarthy (HC, new)", [
  ["Tree", "West Coast"],
  ["Scheme", "timing West Coast, Rodgers quick game + checkdowns, suppresses scramble"],
  ["Fantasy", "short-area/possession passing; lifts pass-catching backs & underneath WR/TE over vertical X receivers"],
]).forEach(p=>children.push(p));

children.push(H("New OC who genuinely calls the plays", HeadingLevel.HEADING_2));
profile("LAC", "Mike McDaniel (OC, new)", [
  ["Tree", "Shanahan"],
  ["Scheme", "Miami-style ~70% motion, PA + screens, zone run, downfield off PA; Herbert ~2.4s release"],
  ["Fantasy", "Omarion Hampton up (zone run + RB pass game), Herbert efficiency up. Risk: timing offense needs a clean pocket — OL/sacks would undercut it. Targets spread."],
]).forEach(p=>children.push(p));
profile("MIA", "Bobby Slowik (OC, new)", [
  ["Tree", "Shanahan (ex-HOU OC)"],
  ["Scheme", "motion/PA/screens, horizontal spacing — not a vertical bomber"],
  ["Fantasy", "scheme is friendly but the WR room was gutted — the open question is De’Von Achane’s role/ceiling, not a clean WR boost"],
]).forEach(p=>children.push(p));
profile("TEN", "Brian Daboll (OC, new)", [
  ["Tree", "Erhardt-Perkins (Josh Allen’s developer)"],
  ["Scheme", "motion + condensed splits + deep PA, WR/RB featured"],
  ["Fantasy", "with rookie Cam Ward, pass volume should climb as he develops — buy the trajectory"],
]).forEach(p=>children.push(p));
profile("ATL", "Tommy Rees (OC) under HC Kevin Stefanski’s system", [
  ["Tree", "Stefanski/Shanahan wide-zone"],
  ["Scheme", "under-center #1 (2024), wide-zone + heavy PA, possession passing, strict pocket"],
  ["Fantasy", "TE-friendly (12-personnel) → Kyle Pitts upside is the headline"],
]).forEach(p=>children.push(p));
profile("DET", "Drew Petzing (OC, new)", [
  ["Tree", "under-center / play-action family"],
  ["Scheme", "heavy under-center + play-action (charts strongly), motion + RPO; his Arizona scheme skewed run-heavy/short, Goff is a pocket QB"],
  ["Fantasy", "under-center PA boosts Goff + PA receivers; watch whether Ben-Johnson-era juice carries or regresses toward Petzing’s conservative AZ baseline"],
]).forEach(p=>children.push(p));
profile("TB", "Zac Robinson (OC, new)", [
  ["Tree", "McVay"],
  ["Scheme", "motion/PA/wide-zone for Mayfield; Bowles DC unchanged"],
  ["Fantasy", "Bucky Irving more receptions, Mayfield bounce-back — but target distribution gets watered down, so temper a WR1’s concentration"],
]).forEach(p=>children.push(p));
profile("NYG", "Matt Nagy (OC, calls plays)", [
  ["Tree", "Reid / West Coast"], ["Scheme", "West Coast/spread, misdirection, RPO, motion for Dart"],
  ["Fantasy", "motion + pass-catching-friendly; Reid-tree QB development angle"],
]).forEach(p=>children.push(p));
profile("NYJ", "Frank Reich (OC, new)", [
  ["Tree", "veteran (Frazier/Coryell lineage)"], ["Scheme", "RB/TE motion to ID coverage, quick game for Geno, strict pocket"],
  ["Fantasy", "quick-game/possession-leaning; underneath targets + RB receiving over deep shots"],
]).forEach(p=>children.push(p));
profile("DEN", "Davis Webb (OC, new caller; Payton handed it off)", [
  ["Tree", "Payton / spread-Air-Raid roots"], ["Scheme", "spread + vertical (Waddle field-stretcher), deep RB room"],
  ["Fantasy", "vertical tilt; note this flipped from continuity — Payton delegating makes it a real (if Payton-influenced) change"],
]).forEach(p=>children.push(p));
profile("CAR", "Brad Idzik (OC, new caller)", [
  ["Tree", "Canales / Shanahan-ish"], ["Scheme", "wide-zone committing to more motion, short aDOT, RB screens"],
  ["Fantasy", "short-area, RB-screen friendly; lower-aDOT WR usage"],
]).forEach(p=>children.push(p));

children.push(H("First-time play-callers — real change, widen the error bars", HeadingLevel.HEADING_2));
profile("BAL", "Declan Doyle (OC, first-time)", [
  ["Scheme", "Payton/Johnson-tree motion + explosive PA + Lamar bootlegs"],
  ["Caution", "DOWNGRADE RISK — replaces Todd Monken, who was elite for Lamar. Not the reflexive “new OC = improvement.”"],
]).forEach(p=>children.push(p));
profile("SEA", "Brian Fleury (OC, first-time; Kubiak left for the LV HC job)", [
  ["Scheme", "~80% the same wide-zone/under-center/PA family + more motion/tempo (Fleury from SF); Darnold a pocket QB"],
  ["Caution", "DOWNGRADE FLAG — Kubiak was Seattle’s 2025 caller and the reason JSN broke out. Handing it to unproven Fleury makes the SEA pass game / JSN a downgrade risk, not neutral."],
]).forEach(p=>children.push(p));
profile("PHI", "Sean Mannion (OC, first-time)", [
  ["Tree", "McVay/LaFleur (motion wide-zone, not run-heavy quick game); HC Sirianni is CEO, Hurts has designed runs"],
  ["Fantasy", "scheme historically targets RBs → Saquon’s receiving role could expand, DeVonta Smith a larger uncontested share. But modeled pass attempts are down post-A.J. Brown — neutral-to-cautious."],
]).forEach(p=>children.push(p));
profile("WAS", "David Blough (OC, first-time)", [
  ["Scheme", "more under-center/balanced, less shotgun for Jayden Daniels"],
  ["Fantasy", "the dials suggest a more grounded, less-scramble Daniels — a meaningful style change for a QB whose 2025 value leaned on mobility. Widest error bars of the group."],
]).forEach(p=>children.push(p));

children.push(H("Continuity — OC title churned, 2025 play-caller stayed (no scheme change)", HeadingLevel.HEADING_2));
children.push(bullet([ T("BUF — Joe Brady", {bold:true}), T(" (now HC, still calls). Evolving toward more PA + motion than assumed — not pure “nothing changed.”") ]));
children.push(bullet([ T("KC — Andy Reid", {bold:true}), T(" calls it; Bieniemy is a support/reunion hire.") ]));
children.push(bullet([ T("LAR — Sean McVay", {bold:true}), T(" calls it (#1 in play-action league-wide); Scheelhaase internal promo.") ]));
children.push(bullet([ T("CHI — Ben Johnson", {bold:true}), T(" (hired 2025, not new): most explosive offense in the NFL, #2 motion two years running, #2 PA, 13-personnel multi-TE (Loveland + Kmet) → Caleb Williams leap + a live TE room. Press Taylor is support.") ]));
children.push(bullet([ T("DAL — Brian Schottenheimer", {bold:true}), T(" (year 2); GB — Matt LaFleur calls it.") ]));
children.push(P([ T("Don’t move players on these OC headlines — Clay already models them as no-change.", { italics: true }) ]));

// ---- Defense ----
children.push(H("Defensive coordinator changes & scheme", HeadingLevel.HEADING_1));
children.push(P([ T("14 teams hired a new DC. Six have a quantified scheme tendency that shifts the matchup read; the rest are regressed toward mean (low confidence) until confirmed. A new DC changes a team’s man/zone + blitz identity — so the personnel-based funnel is least reliable for these teams.") ]));
profile("BAL", "Jesse Minter (DC, confirmed)", [
  ["Scheme", "~81% zone, two-high split-field, low man, low blitz, front-four pressure (ex-LAC DC)"],
  ["Read", "BAL becomes zone-heavy / two-high → suppresses deep shots; target underneath, slot, TE, YAC and pass-catching RBs over vertical man-beaters"],
]).forEach(p=>children.push(p));
profile("TEN", "Gus Bradley", [
  ["Scheme", "heavy Cover-3 ZONE (~55% Cover-3, led NFL 2023), low man"],
  ["Read", "makes TEN a ZONE pass-funnel → target zone-beaters: slot, TE, YAC WRs, pass-catching RBs; fade pure man-beating vertical X receivers"],
]).forEach(p=>children.push(p));
profile("SF", "Raheem Morris", [
  ["Scheme", "MORE man + aggressive (5+ rushers ~⅓), multiple change-ups vs Saleh’s zone"],
  ["Read", "SF stays near-fortress but shifts man-heavy → the way in is man-beating separators, not zone-settlers"],
]).forEach(p=>children.push(p));
profile("PIT", "Patrick Graham", [
  ["Scheme", "two-high, split-field, press corners, low blitz (~25th)"],
  ["Read", "two-high suppresses deep shots → PIT’s soft 2025 coverage likely firms vs explosives; production tilts underneath/RB, not deep WR booms"],
]).forEach(p=>children.push(p));
profile("NYG", "Dennard Wilson", [
  ["Scheme", "attacking, smart-blitz, DB-coach pass-defense emphasis"],
  ["Read", "NYG’s extreme pass-funnel should firm — coverage is his specialty. Downgrade the “torch the Giants secondary” assumption."],
]).forEach(p=>children.push(p));
profile("GB", "Jonathan Gannon", [
  ["Scheme", "LOW blitz (~17–18%), front-four pressure, 3-safety looks"],
  ["Read", "run-funnel intact but cleaner QB pockets (fewer free rushers) → steadier opposing-QB matchup; opposing RB/underneath still the exploit"],
]).forEach(p=>children.push(p));
children.push(P([ T("Low-confidence new DCs (regressed to mean until confirmed): ", { bold: true }),
  T("BUF Leonhard, CLE Rutenberg, DAL Parker, LAC O’Leary, LV Leonard, MIA Duggan, NYJ Duker, WAS D. Jones.") ]));

// ---- Tendency leaderboards ----
children.push(H("Charted tendency leaderboards (the scheme tags Clay’s pass% misses)", HeadingLevel.HEADING_1));
children.push(bullet([ T("Motion at snap: ", { bold: true }), T("Ben Johnson (#2, 2 yrs), M. LaFleur, Coen, O’Connell, Joe Brady; Kubiak mid-pack.") ]));
children.push(bullet([ T("Play-action: ", { bold: true }), T("McVay #1, Ben Johnson #2, Joe Brady #3 (up from 25th), Kubiak, O’Connell, M. LaFleur, Petzing.") ]));
children.push(bullet([ T("Under-center dropbacks: ", { bold: true }), T("Stefanski #1 (2024); Ben Johnson, O’Connell, McVay, Kubiak, Petzing, McDaniel, LaFleur all heavy. Under-center PA boosts QB efficiency + play-action WRs.") ]));

// ---- Verify ----
children.push(H("Verify before you cite", HeadingLevel.HEADING_1));
children.push(bullet([ T("NE — Josh McDaniels with Drake Maye: ", { bold: true }), T("charted analysts repeatedly praised this as a top play-caller / elite-fantasy-QB setup, but the sourced registry didn’t capture NE’s 2026 caller. Verify NE’s OC/play-caller before acting on a Maye bump.") ]));
children.push(bullet([ T("Provenance: ", { bold: true }), T("the offensive play-caller list was web-verified June 2026 but not re-checked this session; BAL’s DC is confirmed as Jesse Minter. Live-verify any specific team on request.") ]));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: ACCENT, font: "Arial" }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ]
  },
  numbering: { config: [ { reference: "b", levels: [ { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 460, hanging: 240 } } } } ] } ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children
  }]
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync("2026_Coaching_Changes_Playcaller_Guide.docx", buf); console.log("wrote docx", buf.length, "bytes"); });
