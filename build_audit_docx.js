const fs=require('fs');
const {Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,AlignmentType,
 HeadingLevel,BorderStyle,WidthType,ShadingType,LevelFormat,PageNumber,Header,Footer}=require('docx');
const CW=9360;
const B={style:BorderStyle.SINGLE,size:1,color:"CCCCCC"}, BORD={top:B,bottom:B,left:B,right:B};
const H1=t=>new Paragraph({heading:HeadingLevel.HEADING_1,children:[new TextRun(t)]});
const H2=t=>new Paragraph({heading:HeadingLevel.HEADING_2,children:[new TextRun(t)]});
const P=(t,o={})=>new Paragraph({spacing:{after:120},children:[new TextRun({text:t,...o})]});
const LEAD=(b,t)=>new Paragraph({spacing:{after:120},children:[new TextRun({text:b,bold:true}),new TextRun(t)]});
const BULL=t=>new Paragraph({numbering:{reference:"b",level:0},spacing:{after:60},children:[new TextRun(t)]});
const MONO=t=>new Paragraph({spacing:{after:20},children:[new TextRun({text:t,font:"Courier New",size:16})]});
const cell=(t,{w,fill,bold,head}={})=>new TableCell({borders:BORD,width:{size:w,type:WidthType.DXA},
 ...(fill?{shading:{fill,type:ShadingType.CLEAR}}:{}),margins:{top:60,bottom:60,left:100,right:100},
 children:[new Paragraph({children:[new TextRun({text:t,bold:!!(bold||head),size:head?18:18})]})]});
const SEVC={"High":"F4B6A8","Med":"FFE39E","Low-Med":"FFF2CC"};

// Problem table
const probCols=[520,3400,1040,4400];
const probRows=[["#","Problem","Severity","Evidence"],
["P1","No orchestrator — 18-stage build run by hand","High","no .sh/Makefile/runner exists"],
["P2","Append-only chain + silent skips — skip/reorder an ingest and columns vanish, no error","High","each ingest_advanced* reads→rewrites features.csv; engines just abstain"],
["P3","ingest_defense ↔ reweight_2026 ordering footgun — re-running ingest_defense reverts the 2026 reweight","High","both write defense.json + opp_*_pctl"],
["P4","Non-atomic CSV write — crash mid-write desyncs features.csv from features.json","Med","JSON atomic via safe_json_dump; CSV raw open()+DictWriter"],
["P5","Duplicated parsers — num() in 11 files, pct() in 6, team maps in 3","High","grep counts; ingest_defense/reweight/team_* redefine vs import core"],
["P6","Duplicated stats math — (rank-0.5)/n*100 copied across 3 functions in 2 files","Med","dfs vs fusion within_pos_pctl; diverge only on NaN policy"],
["P7","CSV read→merge→rewrite boilerplate repeated verbatim","Med","12 ingest scripts"],
["P8","~20 magic constants scattered in function bodies, no config","Med","LG_MAN=17, HOT/COLD=70/35, ENV 0.80/1.25, source weights"],
["P9","Zero tests (1 stub)","High","no coverage of fn, norm_team, percentile, ingest"],
["P10","No column provenance — 139 cols, no producer/coverage record","Med","features.json.meta.cols is names only"],
["P11","Inconsistent NaN/abstention — preserve vs neutral-fill chosen ad hoc","Low-Med","dfs preserves; fusion has both variants"],
["P12","Perf: full re-read/write ×12 + recompute every run + double-parse defense CSVs","Low-Med","acceptable at 371 rows but compounds P2"]];
const probTable=new Table({width:{size:CW,type:WidthType.DXA},columnWidths:probCols,
 rows:probRows.map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{w:probCols[j],
   fill:i===0?"2E5496":(j===2?SEVC[c]:undefined),bold:i===0,head:i===0,
   }))}))});
// header row text white

// Delivered code table
const dCols=[1700,3700,3960];
const dRows=[["Module","What it is","Validation"],
["statlib.py","one within-position percentile + consensus/divergence/composite; NaN policy is a named arg","exact parity vs live within_pos_pctl on 371 real rows"],
["parse.py","canonical num/pct/pnum/ab + one team_code resolver","unit-tested incl. '97%Elite', '1PIT', 'Las Vegas Raiders'"],
["featurestore.py","FeatureStore (load/apply/save, atomic CSV+JSON) + declarative SourceSpec","reproduced ingest_advanced6 exactly (145 WR/TE), live store untouched"],
["registry.py + columns.json","column → producer/dtype/coverage/abstains; validate() fails on drift","139/139 registered, 0 unregistered"],
["pipeline.py","single orchestrator; per-stage column/sync/order integrity checks","--check green: csv/json in sync, all 18 stages' columns present"],
["tests/test_refactor.py","the missing test layer","6/6 PASS"]];
const dTable=new Table({width:{size:CW,type:WidthType.DXA},columnWidths:dCols,
 rows:dRows.map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{w:dCols[j],fill:i===0?"2E5496":undefined,bold:i===0,head:i===0}))}))});

const kids=[
 new Paragraph({heading:HeadingLevel.TITLE,children:[new TextRun("Best-Ball / DFS Toolkit — Architecture Audit & Refactor Plan")]}),
 P("Senior-engineer review, June 2026. Scope: the bestball/ analytics pipeline — 26 Python files, ~5,381 LOC, a 139-column feature store, an 18-stage build, and a browser command center.",{italics:true}),

 H1("1. Architecture Overview"),
 P("The system turns raw football data into a single interactive draft/DFS dashboard, organized in four layers."),
 LEAD("Layer 1 — Shared core (core.py, 61 LOC). ","One canonical name normalizer (fn), team-code map (norm_team/TMAP), a NaN-safe atomic JSON writer (safe_json_dump), and the position-strict fuzzy join (match_usage) that resolves collisions like A.J. Brown vs Amon-Ra. Imported by nearly every script."),
 LEAD("Layer 2 — Feature store (append-only chain). ","build_features.py creates features.csv/json (one row per ~371 players); then twelve scripts each read it, add columns, and rewrite it (ingest_advanced→…10→ingest_defense→reweight_defense_2026). End state: a flat 139-column store, the single source every engine reads."),
 LEAD("Layer 3 — Source-fusion engines. ","dfs_scenarios.py (870 LOC) and fusion.py (1,152 LOC) read the store and emit model-fusion outputs: each source is its own within-position percentile, shown with consensus (mean) and divergence (std). gameplan.py and personnel.py add draft/scheme layers. Nothing is refit or collapsed."),
 LEAD("Layer 4 — Render. ","command_center.py merges five JSON outputs into command_center.html via a __DATA__ placeholder."),
 H2("Data flow"),
 MONO("raw (sis_value/*, NFL-master/*, ffdataroma/*, parquet, schedule, ADP)"),
 MONO("  └─ build_features.py            → features.{csv,json}  (~40 cols)"),
 MONO("  └─ ingest_advanced .. 10  ×11   → features (+~85 cols, append-in-place)"),
 MONO("  └─ ingest_defense.py            → defense.json (2025) + opp_*_pctl"),
 MONO("  └─ reweight_defense_2026.py     → defense.json (2026) + adj opp_*_pctl  [MUST be last]"),
 MONO("       ├─ dfs_scenarios.py  → dfs_scenarios.json"),
 MONO("       ├─ fusion.py         → fusion.json"),
 MONO("       ├─ gameplan.py / personnel.py → *.json"),
 MONO("       └─ command_center.py → command_center.html"),
 H2("What's genuinely good"),
 BULL("The model-fusion contract is sound and consistent: independent within-position percentiles, missing signals abstain (never a fake 50 inside a source), consensus/divergence computed not collapsed."),
 BULL("core.py is the right abstraction — one join, one team map, one atomic JSON writer."),
 BULL("Atomic JSON writes already prevent truncated JSON on crash."),

 H1("2. Problem Areas"),
 probTable,
 new Paragraph({spacing:{before:160,after:120},children:[new TextRun("The throughline: P1–P4 are one failure mode — an implicit, in-place, hand-run chain with no guardrails, so a skipped/out-of-order step corrupts state silently. P5–P7 are duplication that multiplies the cost of every change. P9–P10 mean none of it is verified or documented.")]}),

 H1("3. Refactor Strategy (incremental, non-breaking)"),
 P("Sequenced lowest-risk-first; each phase is independently shippable and parity-tested before the next."),
 LEAD("Phase 0 — Safety net. ","Land tests + pipeline.py --check. Regressions now caught. (Delivered.)"),
 LEAD("Phase 1 — Dedupe leaf helpers. ","Replace 11 num()/6 pct()/3 team-maps with parse.py; the 3 percentile copies with statlib.py. Pure, parity-tested, swap one import at a time. (Delivered + verified.)"),
 LEAD("Phase 2 — Collapse the ingest chain. ","Re-express the 12 ingest scripts as declarative SourceSpecs over featurestore.py (load once, merge, write once, atomic). Kills P2/P4/P7, records provenance for P10. (Framework delivered; one stage reproduced at parity.)"),
 LEAD("Phase 3 — Orchestrate. ","Adopt pipeline.py as the single entry point with per-stage integrity checks. Kills P1/P3. (Delivered; --check green.)"),
 LEAD("Phase 4 — Config + provenance. ","Lift the ~20 constants into one config; run registry.py in CI to fail on schema drift. (Registry delivered.)"),

 H1("4. Improved Architecture"),
 MONO("core.py ── parse.py (num/pct/team_code) ── statlib.py (pctl abstain|neutral,"),
 MONO("(join,IO)                                    consensus/divergence)"),
 MONO("     │                                              │ engines import statlib"),
 MONO("     ▼                                              ▼ instead of re-deriving pctl"),
 MONO("featurestore.py (load once, apply SourceSpec[],  → dfs_scenarios.py / fusion.py"),
 MONO("  write once, atomic, provenance)"),
 MONO("     │            columns.json ◄── registry.py (provenance + CI drift guard)"),
 MONO("     ▼"),
 MONO("pipeline.py — ordered DAG + integrity checks → command_center.html"),
 P("The engines keep their model-fusion logic but drop their private percentile copies (import statlib); the 12 ingest scripts become ~12 SourceSpec literals fed to one FeatureStore; the hand-run chain becomes one command. Net: fewer lines, one place per concern, and every ordering hazard becomes a loud failure."),

 H1("5. Delivered Reference Code (refactor/)"),
 dTable,
 new Paragraph({spacing:{before:160},children:[new TextRun({text:"Adoption is incremental and reversible: the modules sit beside the working code and are swapped in one import / one stage at a time, gated by the test suite and pipeline --check.",italics:true})]}),
];

const doc=new Document({
 styles:{default:{document:{run:{font:"Arial",size:22}}},
  paragraphStyles:[
   {id:"Title",name:"Title",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:40,bold:true,font:"Arial",color:"1F3864"},paragraph:{spacing:{after:240}}},
   {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:30,bold:true,font:"Arial",color:"1F3864"},paragraph:{spacing:{before:280,after:160},outlineLevel:0}},
   {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,font:"Arial",color:"2E5496"},paragraph:{spacing:{before:180,after:120},outlineLevel:1}},
  ]},
 numbering:{config:[{reference:"b",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]}]},
 sections:[{properties:{page:{size:{width:12240,height:15840},margin:{top:1440,right:1440,bottom:1440,left:1440}}},
  footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun("Architecture Audit — bestball/ — page "),new TextRun({children:[PageNumber.CURRENT]})]})]})},
  children:kids}]
});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync("ARCHITECTURE_AUDIT_2026.docx",b);console.log("wrote ARCHITECTURE_AUDIT_2026.docx",b.length,"bytes");});
