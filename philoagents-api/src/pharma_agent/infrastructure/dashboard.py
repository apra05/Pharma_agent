"""Custom Pharma Agent Monitoring Dashboard.

Serves a rich HTML page that reads from the local Evidently workspace and
renders live metrics with hover-based definitions in plain English.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse


# ── Workspace Paths ────────────────────────────────────────────────────────────
WORKSPACE_DIR = Path("/app/workspace")

# Metric display names → internal evidently key fragments
METRIC_FRAGMENTS = {
    "Response Character Length": "Response Character Length",
    "Response Sentiment": "Response Sentiment",
    "Query Character Length": "Query Character Length",
    "Query Sentiment": "Query Sentiment",
    "Response Toxicity": "Response Toxicity",
    "Query Toxicity": "Query Toxicity",
    "Response Faithfulness": "Response Faithfulness",
    "Correctness": "Correctness",
    "Faithfulness": "Faithfulness",
    "Context Quality": "Context Quality",
    "Semantic Similarity to Expected": "Semantic Similarity to Expected",
}


def _load_snapshots(project_id: str) -> list[dict[str, Any]]:
    snap_dir = WORKSPACE_DIR / project_id / "snapshots"
    if not snap_dir.exists():
        return []
    snaps = []
    for f in sorted(snap_dir.iterdir()):
        if f.suffix == ".json":
            try:
                with open(f) as fh:
                    snaps.append(json.load(fh))
            except Exception:
                pass
    return snaps


def _extract_mean(snapshot: dict, label: str) -> float | None:
    for result in snapshot.get("metric_results", {}).values():
        name = result.get("display_name", "")
        if f"Mean value of '{label}'" in name:
            v = result.get("value")
            if v is not None and str(v) not in ("nan", "None"):
                try:
                    return round(float(v), 4)
                except Exception:
                    pass
    return None


def _extract_row_count(snapshot: dict) -> int:
    for result in snapshot.get("metric_results", {}).values():
        if result.get("display_name") == "Row count in dataset":
            try:
                return int(result.get("value", 0))
            except Exception:
                pass
    return 0


def _get_projects() -> dict[str, dict]:
    """Returns {project_id: {name, description}} for all workspace projects."""
    projects = {}
    if not WORKSPACE_DIR.exists():
        return projects
    for d in WORKSPACE_DIR.iterdir():
        meta_file = d / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                projects[d.name] = meta
            except Exception:
                pass
    return projects


def _build_timeseries(snapshots: list[dict], label: str) -> list[dict]:
    series = []
    for snap in snapshots:
        ts = snap.get("timestamp", "")
        v = _extract_mean(snap, label)
        if v is not None:
            series.append({"ts": ts[:19].replace("T", " "), "v": v})
    return series


def build_dashboard_html() -> str:  # noqa: C901 — intentionally verbose for clarity
    projects = _get_projects()

    live_id = next(
        (pid for pid, m in projects.items() if "Live" in m.get("name", "")), None
    )
    eval_id = next(
        (pid for pid, m in projects.items() if "Evaluation" in m.get("name", "") and "Live" not in m.get("name", "")), None
    )

    live_snaps = _load_snapshots(live_id) if live_id else []
    eval_snaps = _load_snapshots(eval_id) if eval_id else []

    # ── Latest values ──────────────────────────────────────────────────────────
    def latest(snaps, label):
        for snap in reversed(snaps):
            v = _extract_mean(snap, label)
            if v is not None:
                return v
        return None

    live_total = sum(_extract_row_count(s) for s in live_snaps)
    eval_total = sum(_extract_row_count(s) for s in eval_snaps)

    metrics_live = {
        "Response Character Length": latest(live_snaps, "Response Character Length"),
        "Response Sentiment": latest(live_snaps, "Response Sentiment"),
        "Query Character Length": latest(live_snaps, "Query Character Length"),
        "Query Sentiment": latest(live_snaps, "Query Sentiment"),
        "Response Toxicity": latest(live_snaps, "Response Toxicity"),
        "Query Toxicity": latest(live_snaps, "Query Toxicity"),
        "Response Faithfulness": latest(live_snaps, "Response Faithfulness"),
        "Context Quality": latest(live_snaps, "Context Quality"),
    }

    metrics_eval = {
        "Correctness": latest(eval_snaps, "Correctness"),
        "Faithfulness": latest(eval_snaps, "Faithfulness"),
        "Context Quality": latest(eval_snaps, "Context Quality"),
        "Semantic Similarity to Expected": latest(eval_snaps, "Semantic Similarity to Expected"),
        "Response Sentiment": latest(eval_snaps, "Response Sentiment"),
        "Response Character Length": latest(eval_snaps, "Response Character Length"),
    }

    def fmt(v, pct=False):
        if v is None:
            return "N/A"
        if pct:
            return f"{v * 100:.1f}%"
        return str(v)

    def score_color(v, invert=False):
        if v is None:
            return "#6b7280"
        if invert:
            v = 1 - v
        if v >= 0.75:
            return "#22c55e"
        if v >= 0.4:
            return "#f59e0b"
        return "#ef4444"

    # ── Timeseries JSON ────────────────────────────────────────────────────────
    ts_resp_len = json.dumps(_build_timeseries(live_snaps, "Response Character Length"))
    ts_resp_sent = json.dumps(_build_timeseries(live_snaps, "Response Sentiment"))
    ts_query_len = json.dumps(_build_timeseries(live_snaps, "Query Character Length"))
    ts_faith = json.dumps(_build_timeseries(live_snaps, "Response Faithfulness"))
    ts_toxicity = json.dumps(_build_timeseries(live_snaps, "Response Toxicity"))
    ts_ctx_live = json.dumps(_build_timeseries(live_snaps, "Context Quality"))
    ts_correct = json.dumps(_build_timeseries(eval_snaps, "Correctness"))
    ts_ctx = json.dumps(_build_timeseries(eval_snaps, "Context Quality"))
    ts_sim = json.dumps(_build_timeseries(eval_snaps, "Semantic Similarity to Expected"))

    snap_timestamps = [s.get("timestamp", "")[:19].replace("T", " ") for s in live_snaps]
    snap_count = len(live_snaps)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Pharma Agent — Monitoring Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #0a0a14;
  --surface: #12121f;
  --surface2: #1a1a2e;
  --border: #2a2a45;
  --text: #e2e2ff;
  --text-muted: #7c7ca8;
  --purple: #a78bfa;
  --blue: #60a5fa;
  --green: #34d399;
  --yellow: #fbbf24;
  --red: #f87171;
  --pink: #f472b6;
  --cyan: #22d3ee;
  --grad1: linear-gradient(135deg, #a78bfa22, #60a5fa22);
  --grad2: linear-gradient(135deg, #34d39922, #22d3ee22);
  --grad3: linear-gradient(135deg, #fbbf2422, #f472b622);
  --grad4: linear-gradient(135deg, #f8717122, #fbbf2422);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}}

/* ── Header ── */
.header {{
  background: linear-gradient(135deg, #1a0a2e 0%, #0a0a14 60%, #0a1428 100%);
  border-bottom: 1px solid var(--border);
  padding: 20px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(12px);
}}
.header-left {{ display: flex; align-items: center; gap: 14px; }}
.header h1 {{ font-size: 1.4rem; font-weight: 700; background: linear-gradient(90deg, var(--purple), var(--blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.header p {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}
.live-badge {{
  display: flex; align-items: center; gap: 6px;
  background: #22c55e18; border: 1px solid #22c55e44;
  border-radius: 20px; padding: 4px 12px; font-size: 0.75rem; color: #22c55e;
}}
.live-dot {{ width: 7px; height: 7px; border-radius: 50%; background: #22c55e; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }} }}

/* ── Nav tabs ── */
.nav {{ padding: 0 32px; border-bottom: 1px solid var(--border); display: flex; gap: 4px; }}
.nav-btn {{
  padding: 12px 20px; font-size: 0.85rem; font-weight: 500;
  color: var(--text-muted); background: transparent; border: none;
  cursor: pointer; border-bottom: 2px solid transparent; transition: all .2s;
  position: relative;
}}
.nav-btn:hover {{ color: var(--text); }}
.nav-btn.active {{ color: var(--purple); border-bottom-color: var(--purple); }}

/* ── Content ── */
.page {{ display: none; padding: 28px 32px; }}
.page.active {{ display: block; }}

/* ── Tooltip system ── */
.metric-tooltip {
  position: relative;
  cursor: help;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px dotted var(--purple);
}
.metric-tooltip .tip-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(167, 139, 250, 0.15);
  color: var(--purple);
  border: 1px solid var(--purple);
  font-size: 10px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}
.metric-tooltip:hover .tip-icon {
  background: var(--purple);
  color: #0a0a14;
}
.tooltip-box {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%) translateY(10px);
  background: rgba(20, 20, 35, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid var(--purple);
  border-radius: 10px;
  padding: 16px;
  width: 320px;
  z-index: 999;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
  pointer-events: none;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s;
  font-weight: normal;
}
.tooltip-box::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 7px solid transparent;
  border-top-color: var(--purple);
}
.tooltip-box .tt-title { font-size: 0.85rem; font-weight: 700; color: var(--purple); margin-bottom: 8px; }
.tooltip-box .tt-what { font-size: 0.78rem; color: var(--text); margin-bottom: 8px; line-height: 1.6; }
.tooltip-box .tt-why { font-size: 0.75rem; color: var(--text-muted); line-height: 1.6; }
.tooltip-box .tt-scale { margin-top: 10px; font-size: 0.72rem; border-top: 1px solid var(--border); padding-top: 8px; color: var(--text-muted); }
.metric-tooltip:hover .tooltip-box {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}

/* ── KPI Grid ── */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }}
.kpi-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 20px;
  transition: transform .2s, border-color .2s;
  position: relative; overflow: hidden;
}}
.kpi-card::before {{
  content: ''; position: absolute; inset: 0;
  background: var(--grad); opacity: 0.5; pointer-events: none;
}}
.kpi-card:hover {{ transform: translateY(-2px); border-color: var(--purple); }}
.kpi-card .kpi-label {{ font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px; font-weight: 500; }}
.kpi-card .kpi-value {{ font-size: 2rem; font-weight: 700; line-height: 1; }}
.kpi-card .kpi-sub {{ font-size: 0.72rem; color: var(--text-muted); margin-top: 4px; }}
.kpi-card .kpi-bar {{ height: 4px; border-radius: 2px; background: var(--border); margin-top: 12px; overflow: hidden; }}
.kpi-card .kpi-bar-fill {{ height: 100%; border-radius: 2px; transition: width 1s ease; }}

/* ── Section heading ── */
.section-title {{ font-size: 1rem; font-weight: 600; color: var(--text); margin: 28px 0 16px; display: flex; align-items: center; gap: 10px; }}
.section-title::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}

/* ── Chart Cards ── */
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px; margin-bottom: 28px; }}
.chart-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 20px;
}}
.chart-card .card-header {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 16px; }}
.chart-card .card-title {{ font-size: 0.88rem; font-weight: 600; }}
.chart-card canvas {{ max-height: 180px; }}

/* ── Metric Explainer Boxes ── */
.explain-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 28px; }}
.explain-card {{
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 14px; padding: 18px 20px;
  transition: border-color .2s, transform .2s;
}}
.explain-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
.explain-card .ec-icon {{ font-size: 1.8rem; margin-bottom: 10px; }}
.explain-card .ec-name {{ font-size: 0.9rem; font-weight: 700; margin-bottom: 6px; }}
.explain-card .ec-desc {{ font-size: 0.78rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 10px; }}
.explain-card .ec-example {{ font-size: 0.72rem; background: var(--surface); border-radius: 6px; padding: 8px 10px; color: var(--cyan); border-left: 2px solid var(--cyan); }}
.explain-card .ec-scale {{
  margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;
}}
.scale-chip {{
  font-size: 0.67rem; padding: 2px 8px; border-radius: 20px; font-weight: 600;
}}
.scale-bad {{ background: #ef444422; color: #ef4444; border: 1px solid #ef444444; }}
.scale-ok {{ background: #fbbf2422; color: #fbbf24; border: 1px solid #fbbf2444; }}
.scale-good {{ background: #22c55e22; color: #22c55e; border: 1px solid #22c55e44; }}

/* ── Footer ── */
.footer {{ text-align: center; padding: 20px; color: var(--text-muted); font-size: 0.75rem; border-top: 1px solid var(--border); margin-top: 16px; }}

/* ── Responsive ── */
@media(max-width:600px) {{
  .header {{ padding: 16px; flex-direction: column; gap: 10px; }}
  .page {{ padding: 16px; }}
  .nav {{ padding: 0 16px; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="header-left">
    <div>
      <h1>🏛️ Pharma Agent Monitoring Dashboard</h1>
      <p>Real-time AI quality metrics for your philosopher chat agents</p>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="live-badge"><span class="live-dot"></span> Live</div>
    <div style="font-size:0.75rem;color:var(--text-muted);text-align:right;">
      <div id="clock"></div>
      <div>{snap_count} snapshots collected</div>
    </div>
  </div>
</div>

<!-- NAV -->
<div class="nav">
  <button class="nav-btn active" onclick="switchTab('live')">📡 Live Monitoring</button>
  <button class="nav-btn" onclick="switchTab('eval')">🧪 Offline Evaluation</button>
  <button class="nav-btn" onclick="switchTab('guide')">📖 Metric Guide</button>
</div>

<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- PAGE: LIVE MONITORING                                                     -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="page active" id="page-live">

  <div class="kpi-grid">
    <!-- Total Interactions -->
    <div class="kpi-card" style="--grad:var(--grad2);">
      <div class="kpi-label">
        <span class="metric-tooltip">💬 Total Chat Interactions
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Total Chat Interactions</div>
            <div class="tt-what"><b>What it is:</b> The total number of messages your users have sent to any philosopher since the system started collecting data.</div>
            <div class="tt-why"><b>Why it matters:</b> Shows how actively the system is being used. More interactions = more data for analysis.</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:var(--green);">{live_total}</div>
      <div class="kpi-sub">interactions logged</div>
    </div>

    <!-- Response Sentiment -->
    <div class="kpi-card" style="--grad:var(--grad1);">
      <div class="kpi-label">
        <span class="metric-tooltip">😊 Response Sentiment
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Response Sentiment</div>
            <div class="tt-what"><b>What it is:</b> A score from -1 to +1 that measures how positive or negative the philosopher's reply sounds. 0 = neutral, +1 = very positive, -1 = very negative.</div>
            <div class="tt-why"><b>Why it matters:</b> Philosophers should be thoughtful and respectful, not harsh or cold. We want scores near 0 to +0.6.</div>
            <div class="tt-scale">🟢 Good: 0.0 – 0.7 &nbsp;|&nbsp; 🟡 OK: -0.2 – 0.0 &nbsp;|&nbsp; 🔴 Investigate: below -0.3</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_live.get('Response Sentiment'))}">{fmt(metrics_live.get('Response Sentiment'))}</div>
      <div class="kpi-sub">latest mean (-1 to +1)</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{max(0,min(100,(metrics_live.get('Response Sentiment') or 0)*100 + 50))}%;background:{score_color(metrics_live.get('Response Sentiment'))};"></div></div>
    </div>

    <!-- Avg Response Length -->
    <div class="kpi-card" style="--grad:var(--grad1);">
      <div class="kpi-label">
        <span class="metric-tooltip">📏 Avg Response Length
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Average Response Length</div>
            <div class="tt-what"><b>What it is:</b> The average number of characters in the philosopher's replies. More characters = longer, more detailed answers.</div>
            <div class="tt-why"><b>Why it matters:</b> Responses that are too short (< 80 chars) may be incomplete. Too long (> 800 chars) may be unfocused. Sweet spot: 150–500 chars.</div>
            <div class="tt-scale">🟢 Good: 150–500 chars &nbsp;|&nbsp; 🟡 OK: 80–800 chars &nbsp;|&nbsp; 🔴 Check: outside that range</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:var(--blue);">{fmt(metrics_live.get('Response Character Length'))}</div>
      <div class="kpi-sub">characters (avg)</div>
    </div>

    <!-- Faithfulness -->
    <div class="kpi-card" style="--grad:var(--grad2);">
      <div class="kpi-label">
        <span class="metric-tooltip">🔗 Response Faithfulness
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Hallucination / Faithfulness (FaithfulnessLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the philosopher's response is solely supported by the retrieved context (documents retrieved from RAG), or if it contains hallucinated facts not present in the source materials.</div>
            <div class="tt-why"><b>Why use it:</b> Crucial for detecting if the agent is making up quotes or philosophical claims that aren't in the database.</div>
            <div class="tt-scale">🟢 Grounded: > 0.75 &nbsp;|&nbsp; 🟡 Review: 0.4–0.75 &nbsp;|&nbsp; 🔴 Hallucinating: < 0.4</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_live.get('Response Faithfulness'))}">{fmt(metrics_live.get('Response Faithfulness'))}</div>
      <div class="kpi-sub">0 = hallucinating, 1 = grounded</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_live.get('Response Faithfulness') or 0)*100)}%;background:{score_color(metrics_live.get('Response Faithfulness'))};"></div></div>
    </div>

    <!-- Context Quality -->
    <div class="kpi-card" style="--grad:var(--grad3);">
      <div class="kpi-label">
        <span class="metric-tooltip">🔍 Context Quality
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Context Quality / Relevance (ContextQualityLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the retrieved context/documents actually contain relevant information to answer the user's query.</div>
            <div class="tt-why"><b>Why use it:</b> Helps debug retrieval performance. If context quality is low, the agent's answer is likely to be weak or inaccurate.</div>
            <div class="tt-scale">🟢 Relevant: > 0.7 &nbsp;|&nbsp; 🟡 Partly: 0.4–0.7 &nbsp;|&nbsp; 🔴 Poor: < 0.4</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_live.get('Context Quality'))}">{fmt(metrics_live.get('Context Quality'))}</div>
      <div class="kpi-sub">retrieval relevance score</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_live.get('Context Quality') or 0)*100)}%;background:{score_color(metrics_live.get('Context Quality'))};"></div></div>
    </div>

    <!-- Response Toxicity -->
    <div class="kpi-card" style="--grad:var(--grad4);">
      <div class="kpi-label">
        <span class="metric-tooltip">🚨 Response Toxicity
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Toxicity Judge (ToxicityLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the user's query or the agent's response is toxic, offensive, or inappropriate.</div>
            <div class="tt-why"><b>Why use it:</b> Safely monitors production dialogues to flag abusive users or inappropriate agent responses.</div>
            <div class="tt-scale">🟢 Safe: < 0.1 &nbsp;|&nbsp; 🟡 Review: 0.1–0.3 &nbsp;|&nbsp; 🔴 Toxic: > 0.3</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_live.get('Response Toxicity'), invert=True)}">{fmt(metrics_live.get('Response Toxicity'))}</div>
      <div class="kpi-sub">0 = safe, 1 = toxic</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_live.get('Response Toxicity') or 0)*100)}%;background:{score_color(metrics_live.get('Response Toxicity'), invert=True)};"></div></div>
    </div>

    <!-- Query Sentiment -->
    <div class="kpi-card" style="--grad:var(--grad3);">
      <div class="kpi-label">
        <span class="metric-tooltip">🧑 User Query Sentiment
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">User Query Sentiment</div>
            <div class="tt-what"><b>What it is:</b> How positive or negative user messages are on average (-1 to +1). Detects frustration (-) or enthusiasm (+).</div>
            <div class="tt-why"><b>Why it matters:</b> A sudden drop (e.g. users getting very negative) could signal a bad user experience worth investigating.</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:var(--yellow);">{fmt(metrics_live.get('Query Sentiment'))}</div>
      <div class="kpi-sub">user tone (-1 to +1)</div>
    </div>
  </div>

  <div class="section-title">📈 Trends Over Time</div>
  <div class="chart-grid">
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Response Length Trend
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Response Length Over Time</div>
            <div class="tt-what"><b>What it shows:</b> How the average length of philosopher replies changes with each conversation. A sudden drop might mean the model is being cut off. A huge spike could mean it's rambling.</div>
          </div>
        </div>
      </div>
      <canvas id="chartRespLen"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Sentiment Trend (Response vs Query)
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Sentiment Trends</div>
            <div class="tt-what"><b>What it shows:</b> How upbeat or negative both the user and the philosopher are, over time. If agent sentiment drops while user is positive, the agent may be acting oddly.</div>
          </div>
        </div>
      </div>
      <canvas id="chartSentiment"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Faithfulness (Anti-Hallucination)
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Faithfulness Trend</div>
            <div class="tt-what"><b>What it shows:</b> Whether the philosopher stays grounded in real knowledge over time. Declining faithfulness = more hallucinations appearing.</div>
          </div>
        </div>
      </div>
      <canvas id="chartFaith"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Context Quality Trend
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Context Quality Trend</div>
            <div class="tt-what"><b>What it shows:</b> Monitors whether retrieved references are relevant to user questions in production. A downward trend indicates index mismatch.</div>
          </div>
        </div>
      </div>
      <canvas id="chartCtxLive"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Toxicity Safety Monitor
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Toxicity Safety Monitor</div>
            <div class="tt-what"><b>What it shows:</b> Tracks if any toxic language appears in responses over time. Should always be near 0. Any spike needs immediate review.</div>
          </div>
        </div>
      </div>
      <canvas id="chartTox"></canvas>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- PAGE: OFFLINE EVALUATION                                                  -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="page" id="page-eval">
  <div class="kpi-grid">
    <div class="kpi-card" style="--grad:var(--grad2);">
      <div class="kpi-label">
        <span class="metric-tooltip">🧪 Evaluation Runs
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Offline Evaluation Runs</div>
            <div class="tt-what"><b>What it is:</b> Total number of philosopher responses evaluated against a predefined test dataset where we know the correct expected answers.</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:var(--purple);">{eval_total}</div>
      <div class="kpi-sub">samples evaluated</div>
    </div>

    <div class="kpi-card" style="--grad:var(--grad1);">
      <div class="kpi-label">
        <span class="metric-tooltip">✅ Correctness
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Correctness (CorrectnessLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the philosopher's answer matches the factuality and details of the reference (expected) answer.</div>
            <div class="tt-why"><b>Why use it:</b> Best for offline dataset evaluation (where you have a predefined ground-truth target answer).</div>
            <div class="tt-scale">🟢 Good: > 0.75 &nbsp;|&nbsp; 🟡 Review: 0.5–0.75 &nbsp;|&nbsp; 🔴 Poor: < 0.5</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_eval.get('Correctness'))}">{fmt(metrics_eval.get('Correctness'))}</div>
      <div class="kpi-sub">0 = wrong, 1 = correct</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_eval.get('Correctness') or 0)*100)}%;background:{score_color(metrics_eval.get('Correctness'))};"></div></div>
    </div>

    <div class="kpi-card" style="--grad:var(--grad2);">
      <div class="kpi-label">
        <span class="metric-tooltip">🔗 Faithfulness
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Hallucination / Faithfulness (FaithfulnessLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the philosopher's response is solely supported by the retrieved context (documents retrieved from RAG), or if it contains hallucinated facts not present in the source materials.</div>
            <div class="tt-why"><b>Why use it:</b> Crucial for detecting if the agent is making up quotes or philosophical claims that aren't in the database.</div>
            <div class="tt-scale">🟢 Grounded: > 0.75 &nbsp;|&nbsp; 🟡 Review: 0.4–0.75 &nbsp;|&nbsp; 🔴 Hallucinating: < 0.4</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_eval.get('Faithfulness'))}">{fmt(metrics_eval.get('Faithfulness'))}</div>
      <div class="kpi-sub">0 = hallucinating, 1 = grounded</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_eval.get('Faithfulness') or 0)*100)}%;background:{score_color(metrics_eval.get('Faithfulness'))};"></div></div>
    </div>

    <div class="kpi-card" style="--grad:var(--grad3);">
      <div class="kpi-label">
        <span class="metric-tooltip">🔍 Context Quality
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Context Quality / Relevance (ContextQualityLLMEval)</div>
            <div class="tt-what"><b>What it measures:</b> Evaluates whether the retrieved context/documents actually contain relevant information to answer the user's query.</div>
            <div class="tt-why"><b>Why use it:</b> Helps debug retrieval performance. If context quality is low, the agent's answer is likely to be weak or inaccurate.</div>
            <div class="tt-scale">🟢 Relevant: > 0.7 &nbsp;|&nbsp; 🟡 Partly: 0.4–0.7 &nbsp;|&nbsp; 🔴 Poor: < 0.4</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_eval.get('Context Quality'))}">{fmt(metrics_eval.get('Context Quality'))}</div>
      <div class="kpi-sub">retrieval relevance score</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_eval.get('Context Quality') or 0)*100)}%;background:{score_color(metrics_eval.get('Context Quality'))};"></div></div>
    </div>

    <div class="kpi-card" style="--grad:var(--grad1);">
      <div class="kpi-label">
        <span class="metric-tooltip">🎯 Semantic Similarity
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Semantic Similarity to Expected Answer</div>
            <div class="tt-what"><b>What it is:</b> Uses AI embeddings to measure how closely the generated answer "means" the same thing as the reference answer, even if different words are used.</div>
            <div class="tt-why"><b>Why it matters:</b> Catches cases where the answer is factually wrong but uses similar philosophical jargon. 1.0 = identical meaning, 0.0 = completely different.</div>
            <div class="tt-scale">🟢 Very similar: > 0.8 &nbsp;|&nbsp; 🟡 Somewhat: 0.5–0.8 &nbsp;|&nbsp; 🔴 Different: < 0.5</div>
          </div>
        </span>
      </div>
      <div class="kpi-value" style="color:{score_color(metrics_eval.get('Semantic Similarity to Expected'))}">{fmt(metrics_eval.get('Semantic Similarity to Expected'))}</div>
      <div class="kpi-sub">0 = different, 1 = same meaning</div>
      <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{int((metrics_eval.get('Semantic Similarity to Expected') or 0)*100)}%;background:{score_color(metrics_eval.get('Semantic Similarity to Expected'))};"></div></div>
    </div>
  </div>

  <div class="section-title">📈 Evaluation Metric Trends</div>
  <div class="chart-grid">
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Correctness Over Evaluations
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Correctness Trend</div>
            <div class="tt-what">Shows how the factual accuracy of philosopher answers changes across evaluation runs. A downward trend means something in the pipeline is degrading.</div>
          </div>
        </div>
      </div>
      <canvas id="chartCorrect"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Context Quality (Retrieval Health)
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Context Quality Trend</div>
            <div class="tt-what">Monitors retrieval performance over time. Declining context quality usually means the vector index needs updating or the query isn't matching well.</div>
          </div>
        </div>
      </div>
      <canvas id="chartCtx"></canvas>
    </div>
    <div class="chart-card">
      <div class="card-header">
        <div class="metric-tooltip card-title">Semantic Similarity Trend
          <span class="tip-icon">i</span>
          <div class="tooltip-box">
            <div class="tt-title">Semantic Similarity Trend</div>
            <div class="tt-what">Tracks how closely generated answers match the expected answers in meaning. Lower scores may indicate prompt drift or LLM behaviour changes.</div>
          </div>
        </div>
      </div>
      <canvas id="chartSim"></canvas>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════════ -->
<!-- PAGE: METRIC GUIDE                                                         -->
<!-- ══════════════════════════════════════════════════════════════════════════ -->
<div class="page" id="page-guide">
  <div class="section-title">🧭 What Do These Metrics Actually Mean?</div>
  <p style="color:var(--text-muted);font-size:0.83rem;margin-bottom:20px;">
    Hover over any metric title on the Live or Evaluation tabs for instant definitions. Here's a deeper guide to each one:
  </p>

  <div class="explain-grid">
    <div class="explain-card" style="--accent:var(--green); border-color:var(--border);">
      <div class="ec-icon">✅</div>
      <div class="ec-name" style="color:var(--green);">Correctness (CorrectnessLLMEval)</div>
      <div class="ec-desc"><b>What it measures:</b> Evaluates whether the philosopher's answer matches the factuality and details of the reference (expected) answer.<br><br><b>Why use it:</b> Best for offline dataset evaluation (where you have a predefined ground-truth target answer).</div>
      <div class="ec-example">💡 Example: If we expect "Socrates believed in questioning everything" and the agent says "Socrates believed knowledge was innate", that's low correctness.</div>
      <div class="ec-scale">
        <span class="scale-bad">< 0.5 Poor</span>
        <span class="scale-ok">0.5–0.75 Average</span>
        <span class="scale-good">> 0.75 Good</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--blue); border-color:var(--border);">
      <div class="ec-icon">🔗</div>
      <div class="ec-name" style="color:var(--blue);">Hallucination / Faithfulness (FaithfulnessLLMEval)</div>
      <div class="ec-desc"><b>What it measures:</b> Evaluates whether the philosopher's response is solely supported by the retrieved context (documents retrieved from RAG), or if it contains hallucinated facts not present in the source materials.<br><br><b>Why use it:</b> Crucial for detecting if the agent is making up quotes or philosophical claims that aren't in the database.</div>
      <div class="ec-example">💡 Example: If the retrieved docs say "Aristotle wrote Nicomachean Ethics" but the agent says "Aristotle wrote the Critique of Pure Reason" — that's a faithfulness violation.</div>
      <div class="ec-scale">
        <span class="scale-bad">< 0.4 Hallucinating</span>
        <span class="scale-ok">0.4–0.75 Some Risk</span>
        <span class="scale-good">> 0.75 Grounded</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--yellow); border-color:var(--border);">
      <div class="ec-icon">🔍</div>
      <div class="ec-name" style="color:var(--yellow);">Context Quality / Relevance (ContextQualityLLMEval)</div>
      <div class="ec-desc"><b>What it measures:</b> Evaluates whether the retrieved context/documents actually contain relevant information to answer the user's query.<br><br><b>Why use it:</b> Helps debug retrieval performance. If context quality is low, the agent's answer is likely to be weak or inaccurate.</div>
      <div class="ec-example">💡 Example: User asks "What is Plato's theory of Forms?" but the system retrieves documents about Descartes' mind-body problem.</div>
      <div class="ec-scale">
        <span class="scale-bad">< 0.4 Irrelevant</span>
        <span class="scale-ok">0.4–0.7 Partly Relevant</span>
        <span class="scale-good">> 0.7 On-Target</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--red); border-color:var(--border);">
      <div class="ec-icon">🚨</div>
      <div class="ec-name" style="color:var(--red);">Toxicity Judge (ToxicityLLMEval)</div>
      <div class="ec-desc"><b>What it measures:</b> Evaluates whether the user's query or the agent's response is toxic, offensive, or inappropriate.<br><br><b>Why use it:</b> Safely monitors production dialogues to flag abusive users or inappropriate agent responses.</div>
      <div class="ec-example">💡 Example: If a user sends hateful messages, or if the agent's response becomes aggressive or offensive.</div>
      <div class="ec-scale">
        <span class="scale-good">< 0.1 Safe</span>
        <span class="scale-ok">0.1–0.3 Review</span>
        <span class="scale-bad">> 0.3 Block/Alert</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--purple); border-color:var(--border);">
      <div class="ec-icon">😊</div>
      <div class="ec-name" style="color:var(--purple);">Sentiment Score</div>
      <div class="ec-desc">Uses natural language processing to detect the emotional tone of text. Ranges from -1 (very negative/angry) to +1 (very positive/happy). 0 is perfectly neutral.<br><br>We track this separately for user queries and agent responses.</div>
      <div class="ec-example">💡 Example: "Tell me more, this is fascinating!" = +0.8 (positive). "You are completely wrong!" = -0.7 (negative). "What is consciousness?" = 0.0 (neutral).</div>
      <div class="ec-scale">
        <span class="scale-bad">-1 Very Negative</span>
        <span class="scale-ok">0 Neutral</span>
        <span class="scale-good">+1 Very Positive</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--cyan); border-color:var(--border);">
      <div class="ec-icon">🎯</div>
      <div class="ec-name" style="color:var(--cyan);">Semantic Similarity</div>
      <div class="ec-desc">Uses AI vector embeddings to compare the meaning of two texts. Unlike exact word matching, it understands that "the mind is separate from the body" and "Descartes' dualism separates mental from physical" mean the same thing.<br><br>Score: 0 = completely different meaning, 1 = identical meaning.</div>
      <div class="ec-example">💡 Example: Generated answer says "Plato believed ideas exist beyond the physical world." Expected says "Plato's Forms are eternal, non-physical entities." → High similarity ≈ 0.9.</div>
      <div class="ec-scale">
        <span class="scale-bad">< 0.5 Different</span>
        <span class="scale-ok">0.5–0.8 Similar</span>
        <span class="scale-good">> 0.8 Very Close</span>
      </div>
    </div>

    <div class="explain-card" style="--accent:var(--blue); border-color:var(--border);">
      <div class="ec-icon">📏</div>
      <div class="ec-name" style="color:var(--blue);">Response Length</div>
      <div class="ec-desc">Simply the number of characters in the philosopher's reply. While not a quality metric by itself, sudden changes are a useful signal.<br><br>A sudden drop may mean the model is being cut off by token limits. A sudden spike could mean runaway generation.</div>
      <div class="ec-example">💡 Example: Normal: ~200–400 chars. If it drops to 10–20 chars, the model may be returning error messages. If it jumps to 2000+ chars, check for prompt injection.</div>
      <div class="ec-scale">
        <span class="scale-bad">< 80 Too Short</span>
        <span class="scale-good">150–500 Ideal</span>
        <span class="scale-ok">> 800 Too Long</span>
      </div>
    </div>
  </div>
</div>

<div class="footer">
  🏛️ Pharma Agent Monitoring Dashboard &nbsp;·&nbsp; Powered by Evidently AI &nbsp;·&nbsp;
  <a href="/docs" style="color:var(--purple)">API Docs</a> &nbsp;·&nbsp;
  <a href="http://localhost:8085" target="_blank" style="color:var(--blue)">Evidently Raw UI</a>
</div>

<script>
// ── Tab switching ──────────────────────────────────────────────────────────────
function switchTab(tab) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + tab).classList.add('active');
  event.target.classList.add('active');
}}

// ── Clock ──────────────────────────────────────────────────────────────────────
function updateClock() {{
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString();
}}
setInterval(updateClock, 1000); updateClock();

// ── Chart helper ───────────────────────────────────────────────────────────────
function makeChart(id, data, label, color, min, max) {{
  const canvas = document.getElementById(id);
  if (!canvas || !data || data.length === 0) return;
  const labels = data.map(d => d.ts.split(' ')[1] || d.ts);
  const values = data.map(d => d.v);
  new Chart(canvas, {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{
        label,
        data: values,
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.3
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ mode: 'index', intersect: false }} }},
      scales: {{
        x: {{ ticks: {{ color: '#7c7ca8', font: {{ size: 10 }} }}, grid: {{ color: '#2a2a4533' }} }},
        y: {{
          min: min ?? undefined, max: max ?? undefined,
          ticks: {{ color: '#7c7ca8', font: {{ size: 10 }} }},
          grid: {{ color: '#2a2a4533' }}
        }}
      }}
    }}
  }});
}}

// ── Inject chart data ──────────────────────────────────────────────────────────
const tsRespLen  = {ts_resp_len};
const tsRespSent = {ts_resp_sent};
const tsQueryLen = {ts_query_len};
const tsFaith    = {ts_faith};
const tsTox      = {ts_toxicity};
const tsCtxLive  = {ts_ctx_live};
const tsCorrect  = {ts_correct};
const tsCtx      = {ts_ctx};
const tsSim      = {ts_sim};

makeChart('chartRespLen',  tsRespLen,  'Response Length (chars)', '#60a5fa');
makeChart('chartSentiment', tsRespSent, 'Response Sentiment', '#a78bfa', -1, 1);
makeChart('chartFaith',    tsFaith,    'Faithfulness', '#34d399', 0, 1);
makeChart('chartTox',      tsTox,      'Toxicity', '#f87171', 0, 1);
makeChart('chartCtxLive',  tsCtxLive,  'Context Quality', '#fbbf24', 0, 1);
makeChart('chartCorrect',  tsCorrect,  'Correctness', '#22c55e', 0, 1);
makeChart('chartCtx',      tsCtx,      'Context Quality', '#fbbf24', 0, 1);
makeChart('chartSim',      tsSim,      'Semantic Similarity', '#22d3ee', 0, 1);

// ── Auto-refresh every 60 seconds ──────────────────────────────────────────────
setTimeout(() => location.reload(), 60000);
</script>
</body>
</html>"""
    return html
