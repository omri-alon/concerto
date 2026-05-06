"""Optional web dashboard and API (requires fastapi + uvicorn)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import MultiOrchestrator

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
except ImportError:
    raise ImportError("Install web extras: pip install concerto[web]")

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Concerto — Program of Works</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,700;0,9..144,900;1,9..144,300;1,9..144,500&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --paper:     #f4ede0;
    --paper-2:   #ece4d2;
    --rule:      #1715111a;
    --rule-hi:   #17151140;
    --ink:       #171511;
    --ink-soft:  #3a342b;
    --muted:     #6f6657;
    --dim:       #a59d8a;
    --vermilion: #c8412b;
    --vermilion-soft: #c8412b22;
    --ledger:    #3d6b4a;
    --ledger-soft: #3d6b4a22;
    --slate:     #355a8a;
    --slate-soft: #355a8a22;
    --gold:      #a37a1f;
    --gold-soft: #a37a1f22;

    --serif:  'Fraunces', 'Times New Roman', serif;
    --mono:   'JetBrains Mono', ui-monospace, monospace;
    --ease:   cubic-bezier(.6,.05,.2,1);
  }

  html, body {
    background: var(--paper);
    color: var(--ink);
    font-family: var(--mono);
    font-size: 12.5px;
    line-height: 1.55;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }

  /* Paper grain — subtle SVG noise */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 2;
    opacity: 0.35;
    mix-blend-mode: multiply;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.09  0 0 0 0 0.08  0 0 0 0 0.06  0 0 0 0.18 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
    background-size: 220px 220px;
  }

  ::selection { background: var(--ink); color: var(--paper); }

  .shell {
    position: relative;
    z-index: 1;
    max-width: 1240px;
    margin: 0 auto;
    padding: 0 36px 80px;
  }

  /* ── Header ── */
  header {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: end;
    padding: 56px 0 28px;
    border-bottom: 0.5px solid var(--rule-hi);
    margin-bottom: 36px;
    position: relative;
  }
  header::before {
    content: '';
    position: absolute;
    left: 0; right: 0; bottom: -3px;
    height: 0.5px;
    background: var(--rule-hi);
  }

  .logo { display: flex; flex-direction: column; gap: 2px; }

  .logo-name {
    font-family: var(--serif);
    font-variation-settings: "opsz" 144, "wght" 700;
    font-size: clamp(64px, 9vw, 112px);
    line-height: 0.86;
    letter-spacing: -0.045em;
    color: var(--ink);
  }
  .logo-name em {
    font-style: italic;
    font-variation-settings: "opsz" 144, "wght" 500;
    color: var(--vermilion);
  }

  .logo-tag {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 14px;
    color: var(--muted);
    letter-spacing: 0.01em;
    margin-top: 10px;
  }

  .header-right {
    text-align: right;
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: flex-end;
    padding-bottom: 6px;
  }

  .opus-mark {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.04em;
  }
  .opus-mark b {
    font-style: normal;
    font-variation-settings: "opsz" 14, "wght" 700;
    color: var(--ink);
  }

  .conductor-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }

  .status-dot {
    width: 8px; height: 8px;
    background: var(--vermilion);
    transform: rotate(45deg);
    transition: opacity .4s var(--ease), background .3s var(--ease);
  }
  .status-dot.idle { background: var(--dim); opacity: .5; }

  .timestamp {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-soft);
    letter-spacing: 0.06em;
  }

  /* ── Metrics row (typographic, no cards) ── */
  .metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    border-top: 0.5px solid var(--rule-hi);
    border-bottom: 0.5px solid var(--rule-hi);
    margin-bottom: 44px;
    background:
      linear-gradient(var(--rule-hi), var(--rule-hi)) left  / 0.5px 100% no-repeat,
      linear-gradient(var(--rule-hi), var(--rule-hi)) 25%  0 / 0.5px 100% no-repeat,
      linear-gradient(var(--rule-hi), var(--rule-hi)) 50%  0 / 0.5px 100% no-repeat,
      linear-gradient(var(--rule-hi), var(--rule-hi)) 75%  0 / 0.5px 100% no-repeat,
      linear-gradient(var(--rule-hi), var(--rule-hi)) right 0 / 0.5px 100% no-repeat;
  }

  .metric {
    padding: 26px 28px 24px;
    position: relative;
    transition: background .4s var(--ease);
  }
  .metric.active { background: linear-gradient(180deg, var(--vermilion-soft), transparent 70%); }

  .metric-label {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 12px;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin-bottom: 14px;
    display: flex;
    align-items: baseline;
    gap: 8px;
  }
  .metric-label::before {
    content: '';
    width: 14px;
    height: 0.5px;
    background: var(--ink);
    transform: translateY(-3px);
  }

  .metric-value {
    font-family: var(--serif);
    font-variation-settings: "opsz" 144, "wght" 500;
    font-size: 64px;
    line-height: 0.92;
    letter-spacing: -0.04em;
    color: var(--ink);
    transition: color .4s var(--ease), font-variation-settings .8s var(--ease);
    font-feature-settings: "lnum", "tnum";
  }
  .metric.active .metric-value {
    color: var(--vermilion);
    font-variation-settings: "opsz" 144, "wght" 700;
  }

  .metric-sub {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 12px;
  }

  /* ── Section headers ── */
  .section-header {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 14px;
    padding-top: 4px;
  }

  .section-numeral {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 144, "wght" 500;
    font-size: 28px;
    color: var(--vermilion);
    letter-spacing: -0.02em;
    line-height: 1;
  }

  .section-title {
    font-family: var(--serif);
    font-variation-settings: "opsz" 14, "wght" 500;
    font-size: 13px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink);
  }

  .section-line {
    flex: 1;
    height: 0.5px;
    background: var(--rule-hi);
    transform: translateY(-4px);
  }

  .section-count {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.12em;
  }

  /* ── Agent ledger rows ── */
  .agents {
    display: flex;
    flex-direction: column;
    border-top: 0.5px solid var(--rule-hi);
    border-bottom: 0.5px solid var(--rule-hi);
    margin-bottom: 44px;
  }

  .agent-card {
    padding: 20px 4px;
    display: grid;
    grid-template-columns: 130px 1fr auto;
    gap: 24px;
    align-items: center;
    border-bottom: 0.5px solid var(--rule);
    transition: background .25s var(--ease);
    position: relative;
    overflow: hidden;
  }
  .agent-card:last-child { border-bottom: none; }
  .agent-card:hover { background: var(--paper-2); }

  /* Streaming baton sweep */
  .agent-card:has(.status-pill.streaming)::after {
    content: '';
    position: absolute;
    left: -10%;
    bottom: 0;
    width: 22%;
    height: 1.5px;
    background: var(--vermilion);
    animation: baton 4.2s var(--ease) infinite;
  }
  @keyframes baton {
    0%   { left: -22%; opacity: 0; }
    15%  { opacity: 1; }
    85%  { opacity: 1; }
    100% { left: 102%; opacity: 0; }
  }

  .agent-id {
    font-family: var(--serif);
    font-variation-settings: "opsz" 14, "wght" 500;
    font-size: 16px;
    color: var(--ink);
    letter-spacing: 0.01em;
    font-feature-settings: "lnum", "tnum";
  }

  .agent-status-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 6px;
  }

  .status-pill {
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 2px 0 2px 10px;
    border-left: 2px solid var(--dim);
    color: var(--muted);
    background: transparent;
  }
  .status-pill.streaming  { color: var(--vermilion); border-left-color: var(--vermilion); }
  .status-pill.streaming::before {
    content: '◆ ';
    animation: pulse-dia 1.4s var(--ease) infinite;
  }
  @keyframes pulse-dia {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.25; }
  }
  .status-pill.succeeded  { color: var(--ledger);    border-left-color: var(--ledger); }
  .status-pill.failed     { color: var(--vermilion); border-left-color: var(--vermilion); }
  .status-pill.retrying   { color: var(--slate);     border-left-color: var(--slate); }
  .status-pill.pending    { color: var(--muted);     border-left-color: var(--dim); }
  .status-pill.gate       { color: var(--gold);      border-left-color: var(--gold); }

  .agent-msg {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 13.5px;
    color: var(--ink-soft);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 640px;
  }

  .agent-meta {
    text-align: right;
    white-space: nowrap;
    font-family: var(--mono);
  }
  .agent-tokens {
    font-size: 13px;
    color: var(--ink);
    font-weight: 600;
    letter-spacing: 0.02em;
    margin-bottom: 3px;
    font-feature-settings: "tnum";
  }
  .agent-turns {
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .agent-project {
    font-family: var(--mono);
    font-size: 9.5px;
    color: var(--muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-top: 4px;
  }

  /* ── Projects (program list) ── */
  .projects-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 0;
    border-top: 0.5px solid var(--rule-hi);
    border-left: 0.5px solid var(--rule-hi);
    margin-bottom: 44px;
  }

  .project-tile {
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    border-right: 0.5px solid var(--rule-hi);
    border-bottom: 0.5px solid var(--rule-hi);
    transition: background .25s var(--ease);
    position: relative;
  }
  .project-tile:hover { background: var(--paper-2); }
  .project-tile.paused { opacity: 0.5; }

  .project-tile-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
  }

  .project-tile-name {
    font-family: var(--serif);
    font-variation-settings: "opsz" 14, "wght" 600;
    font-size: 16px;
    color: var(--ink);
    letter-spacing: -0.005em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 160px;
  }

  .pause-btn {
    background: transparent;
    border: 0.5px solid var(--ink);
    color: var(--ink);
    font-family: var(--mono);
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 4px 10px;
    cursor: pointer;
    transition: all .2s var(--ease);
  }
  .pause-btn:hover {
    background: var(--ink);
    color: var(--paper);
  }
  .pause-btn.paused {
    border-color: var(--vermilion);
    color: var(--vermilion);
  }
  .pause-btn.paused:hover {
    background: var(--vermilion);
    color: var(--paper);
  }

  .project-tile-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }

  .project-stat {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .project-stat-label {
    font-family: var(--mono);
    font-size: 8.5px;
    color: var(--muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .project-stat-value {
    font-family: var(--serif);
    font-variation-settings: "opsz" 14, "wght" 600;
    font-size: 18px;
    color: var(--ink);
    line-height: 1;
    font-feature-settings: "lnum", "tnum";
  }

  /* ── Filter dropdown ── */
  .filter-select {
    background: transparent;
    border: none;
    border-bottom: 0.5px solid var(--ink);
    color: var(--ink);
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.1em;
    padding: 3px 18px 3px 4px;
    cursor: pointer;
    appearance: none;
    background-image: linear-gradient(45deg, transparent 50%, var(--ink) 50%),
                      linear-gradient(135deg, var(--ink) 50%, transparent 50%);
    background-position: calc(100% - 10px) center, calc(100% - 6px) center;
    background-size: 4px 4px, 4px 4px;
    background-repeat: no-repeat;
  }
  .filter-select:focus {
    outline: none;
    border-bottom-color: var(--vermilion);
    color: var(--vermilion);
  }

  /* ── Queue ── */
  .queue-card {
    padding: 14px 4px;
    display: grid;
    grid-template-columns: 130px 1fr auto;
    gap: 24px;
    align-items: center;
    border-bottom: 0.5px solid var(--rule);
  }
  .queue-card:last-child { border-bottom: none; }

  .queue-id {
    font-family: var(--serif);
    font-variation-settings: "opsz" 14, "wght" 500;
    font-size: 14px;
    color: var(--ink);
  }

  .queue-title {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 13px;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 620px;
  }

  .queue-reason {
    font-family: var(--mono);
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    padding: 3px 10px;
    border: 0.5px solid var(--rule-hi);
  }
  .queue-reason.paused {
    color: var(--vermilion);
    border-color: var(--vermilion);
  }

  /* ── Empty state ── */
  .empty {
    border-top: 0.5px solid var(--rule-hi);
    border-bottom: 0.5px solid var(--rule-hi);
    padding: 80px 24px;
    text-align: center;
    margin-bottom: 44px;
  }

  .empty-title {
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 144, "wght" 400;
    font-size: 28px;
    color: var(--ink);
    margin-bottom: 10px;
    letter-spacing: -0.01em;
  }

  .empty-sub {
    font-family: var(--mono);
    font-size: 10.5px;
    color: var(--muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  /* ── Stats bar / coda ── */
  .stats-bar {
    display: flex;
    align-items: center;
    gap: 32px;
    padding: 18px 0;
    border-top: 0.5px solid var(--rule-hi);
    margin-top: 12px;
  }

  .stat-item {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .stat-label {
    font-family: var(--serif);
    font-style: italic;
    font-size: 13px;
    color: var(--muted);
  }

  .stat-value {
    font-family: var(--mono);
    font-size: 12.5px;
    color: var(--ink);
    font-weight: 600;
    letter-spacing: 0.04em;
    font-feature-settings: "tnum";
  }

  .stat-divider {
    width: 0.5px;
    height: 16px;
    background: var(--rule-hi);
  }

  /* ── Progress bar (baton scan) ── */
  .progress-wrap {
    flex: 1;
    height: 1px;
    background: var(--rule-hi);
    overflow: hidden;
    position: relative;
  }

  .progress-bar {
    position: absolute;
    top: 0; left: 0;
    width: 22%;
    height: 100%;
    background: var(--vermilion);
    animation: scan 4.2s var(--ease) infinite;
  }

  @keyframes scan {
    0%   { transform: translateX(-110%); }
    100% { transform: translateX(560%); }
  }

  /* ── Footer ── */
  footer {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 22px 0 0;
    border-top: 0.5px solid var(--rule-hi);
    margin-top: 36px;
    font-family: var(--serif);
    font-style: italic;
    font-variation-settings: "opsz" 14, "wght" 400;
    font-size: 12px;
    color: var(--muted);
  }
  footer .footer-right { font-family: var(--mono); font-style: normal; font-size: 10.5px; letter-spacing: 0.12em; }

  @media (max-width: 820px) {
    .shell { padding: 0 22px 60px; }
    header { grid-template-columns: 1fr; gap: 18px; }
    .header-right { align-items: flex-start; text-align: left; }
    .metrics { grid-template-columns: repeat(2, 1fr); }
    .agent-card, .queue-card { grid-template-columns: 90px 1fr; }
    .agent-meta { grid-column: 1 / -1; text-align: left; }
  }
</style>
</head>
<body>
<div class="shell">

  <header>
    <div class="logo">
      <div class="logo-name">Concerto<em>.</em></div>
      <div class="logo-tag">a program of works for Claude Code — after Symphony, op. 0</div>
    </div>
    <div class="header-right">
      <div class="opus-mark"><b>Op.</b> live · <b>tempo</b> 3s</div>
      <div class="conductor-row">
        <span id="status-dot" class="status-dot idle"></span>
        <span id="ts" class="timestamp">—</span>
      </div>
    </div>
  </header>

  <div class="metrics">
    <div class="metric" id="m-running">
      <div class="metric-label">running</div>
      <div class="metric-value" id="v-running">—</div>
      <div class="metric-sub">active agents</div>
    </div>
    <div class="metric" id="m-retrying">
      <div class="metric-label">queued</div>
      <div class="metric-value" id="v-retrying">—</div>
      <div class="metric-sub">retry · gate</div>
    </div>
    <div class="metric" id="m-tokens">
      <div class="metric-label">tokens</div>
      <div class="metric-value" id="v-tokens">—</div>
      <div class="metric-sub" id="v-tokens-sub">total consumed</div>
    </div>
    <div class="metric" id="m-runtime">
      <div class="metric-label">runtime</div>
      <div class="metric-value" id="v-runtime">—</div>
      <div class="metric-sub">cumulative</div>
    </div>
  </div>

  <div id="projects-section" style="display:none">
    <div class="section-header">
      <span class="section-numeral">i.</span>
      <span class="section-title">Projects</span>
      <div class="section-line"></div>
      <span class="section-count" id="project-count">0</span>
    </div>
    <div id="projects-grid" class="projects-grid"></div>
  </div>

  <div class="section-header">
    <span class="section-numeral">ii.</span>
    <span class="section-title">Active Agents</span>
    <div class="section-line"></div>
    <select id="project-filter" class="filter-select" onchange="window.__concertoSetFilter(this.value)">
      <option value="">All projects</option>
    </select>
    <span class="section-count" id="agent-count">0</span>
  </div>

  <div id="agents-container"></div>

  <div id="queue-section" style="display:none">
    <div class="section-header">
      <span class="section-numeral">iii.</span>
      <span class="section-title">Awaiting Cue</span>
      <div class="section-line"></div>
      <span class="section-count" id="queue-count">0</span>
    </div>
    <div id="queue-container"></div>
  </div>

  <div class="stats-bar">
    <div class="stat-item">
      <span class="stat-label">in</span>
      <span class="stat-value" id="s-in">—</span>
    </div>
    <div class="stat-divider"></div>
    <div class="stat-item">
      <span class="stat-label">out</span>
      <span class="stat-value" id="s-out">—</span>
    </div>
    <div class="stat-divider"></div>
    <div id="progress-container" style="display:none; flex:1; align-items:center; gap:14px;">
      <span class="stat-label">tempo</span>
      <div class="progress-wrap"><div class="progress-bar"></div></div>
    </div>
  </div>

  <footer>
    <span class="footer-left">— polled every three seconds, in good faith.</span>
    <span class="footer-right" id="footer-gen">—</span>
  </footer>

</div>

<script>
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function fmt(n) {
    if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
    if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
    return n.toString();
  }

  function fmtSecs(s) {
    if (s < 60)   return Math.round(s) + 's';
    if (s < 3600) return Math.floor(s/60) + 'm ' + Math.round(s%60) + 's';
    return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
  }

  function statusPill(status) {
    const cls = ['streaming','succeeded','failed','retrying','pending','gate'].includes(status) ? status : 'pending';
    const label = status === 'streaming' ? 'live' : status === 'gate' ? 'awaiting gate' : status;
    return `<span class="status-pill ${cls}">${label}</span>`;
  }

  // Filter state — null means "all projects". Persisted across refreshes.
  let activeFilter = '';
  window.__concertoSetFilter = (val) => { activeFilter = val || ''; refresh(); };

  function projectMatches(item) {
    if (!activeFilter) return true;
    return (item.project_name || '') === activeFilter;
  }

  async function togglePause(name) {
    try {
      await fetch('/api/v1/projects/' + encodeURIComponent(name) + '/toggle', { method: 'POST' });
      refresh();
    } catch (e) { /* ignore */ }
  }
  window.__concertoTogglePause = togglePause;

  function renderProjects(data) {
    const projects = data.projects || [];
    const section = document.getElementById('projects-section');
    if (projects.length <= 1) {
      // Hide the projects section for single-project setups — keeps the
      // dashboard clean when there's no multi-project context to surface.
      section.style.display = 'none';
    } else {
      section.style.display = '';
    }
    document.getElementById('project-count').textContent = projects.length;

    // Update filter dropdown options (preserve current selection)
    const sel = document.getElementById('project-filter');
    const current = sel.value;
    const wantedNames = projects.map(p => p.name);
    const existingOpts = Array.from(sel.options).map(o => o.value);
    const same = wantedNames.length === existingOpts.length - 1 &&
      wantedNames.every((n, i) => existingOpts[i + 1] === n);
    if (!same) {
      sel.innerHTML = '<option value="">All projects</option>' +
        wantedNames.map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join('');
      sel.value = wantedNames.includes(current) ? current : '';
      activeFilter = sel.value;
    }

    document.getElementById('projects-grid').innerHTML = projects.map(p => {
      const tokens = p.totals?.total_tokens || 0;
      const pauseLabel = p.paused ? 'Resume' : 'Pause';
      const pauseClass = p.paused ? 'pause-btn paused' : 'pause-btn';
      return `
        <div class="project-tile ${p.paused ? 'paused' : ''}">
          <div class="project-tile-head">
            <span class="project-tile-name" title="${esc(p.name)}">${esc(p.name)}</span>
            <button class="${pauseClass}" onclick="window.__concertoTogglePause('${esc(p.name)}')">${pauseLabel}</button>
          </div>
          <div class="project-tile-stats">
            <div class="project-stat">
              <span class="project-stat-label">Run</span>
              <span class="project-stat-value">${p.counts?.running || 0}</span>
            </div>
            <div class="project-stat">
              <span class="project-stat-label">Gates</span>
              <span class="project-stat-value">${p.counts?.gates || 0}</span>
            </div>
            <div class="project-stat">
              <span class="project-stat-label">Queue</span>
              <span class="project-stat-value">${p.counts?.queued || 0}</span>
            </div>
            <div class="project-stat">
              <span class="project-stat-label">Tokens</span>
              <span class="project-stat-value">${fmt(tokens)}</span>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function renderQueue(data) {
    const queue = (data.queued || []).filter(projectMatches);
    const section = document.getElementById('queue-section');
    if (queue.length === 0) {
      section.style.display = 'none';
      return;
    }
    section.style.display = '';
    document.getElementById('queue-count').textContent = queue.length;
    document.getElementById('queue-container').innerHTML =
      `<div class="agents">` + queue.map(q => {
        const pausedReason = (q.reason || '').toLowerCase().includes('paused');
        return `
          <div class="queue-card">
            <div>
              <div class="queue-id">${esc(q.issue_identifier)}</div>
              ${q.project_name ? `<div class="agent-project">${esc(q.project_name)}</div>` : ''}
            </div>
            <div class="queue-title">${esc(q.title || '—')}</div>
            <div class="queue-reason ${pausedReason ? 'paused' : ''}">${esc(q.reason || '')}</div>
          </div>`;
      }).join('') + `</div>`;
  }

  function renderAgents(data) {
    const all = [
      ...(data.running || []),
      ...(data.retrying || []).map(r => ({
        issue_identifier: r.issue_identifier,
        project_name: r.project_name,
        status: 'retrying',
        turn_count: r.attempt,
        tokens: { total_tokens: 0 },
        last_message: r.error || 'waiting to retry...',
        session_id: null,
      })),
      ...(data.gates || []).map(g => ({
        issue_identifier: g.issue_identifier,
        project_name: g.project_name,
        status: 'gate',
        state_name: g.gate_state,
        turn_count: g.run,
        tokens: { total_tokens: 0 },
        last_message: 'Awaiting human review',
        session_id: null,
      })),
    ].filter(projectMatches);

    document.getElementById('agent-count').textContent = all.length;

    if (all.length === 0) {
      document.getElementById('agents-container').innerHTML = `
        <div class="empty">
          <div class="empty-title">No active agents</div>
          <div class="empty-sub">Move a GUS work item to the entry status to start</div>
        </div>`;
      return;
    }

    const rows = all.map(r => {
      const stateInfo = r.state_name ? `<span style="color:var(--muted);font-size:11px;margin-left:8px">${esc(r.state_name)}</span>` : '';
      const projTag = r.project_name ? `<div class="agent-project">${esc(r.project_name)}</div>` : '';
      return `
      <div class="agent-card">
        <div>
          <div class="agent-id">${esc(r.issue_identifier)}</div>
          ${projTag}
        </div>
        <div>
          <div class="agent-status-row">
            ${statusPill(r.status)}${stateInfo}
          </div>
          <div class="agent-msg">${esc(r.last_message || '—')}</div>
        </div>
        <div class="agent-meta">
          <div class="agent-tokens">${fmt(r.tokens?.total_tokens || 0)} tok</div>
          <div class="agent-turns">turn ${r.turn_count || 0}</div>
        </div>
      </div>`;
    }).join('');

    document.getElementById('agents-container').innerHTML =
      `<div class="agents">${rows}</div>`;
  }

  async function refresh() {
    try {
      const res = await fetch('/api/v1/state');
      const data = await res.json();

      const running  = data.counts?.running  || 0;
      const retrying = data.counts?.retrying || 0;
      const active   = running > 0;

      // Metrics
      document.getElementById('v-running').textContent  = running;
      const gates = data.counts?.gates || 0;
      document.getElementById('v-retrying').textContent = retrying + gates;
      document.getElementById('v-tokens').textContent   = fmt(data.totals?.total_tokens || 0);
      document.getElementById('v-runtime').textContent  = fmtSecs(data.totals?.seconds_running || 0);

      document.getElementById('m-running').className  = 'metric' + (active ? ' active' : '');
      document.getElementById('m-tokens').className   = 'metric' + (data.totals?.total_tokens > 0 ? ' active' : '');

      // Stats bar
      document.getElementById('s-in').textContent  = fmt(data.totals?.input_tokens  || 0);
      document.getElementById('s-out').textContent = fmt(data.totals?.output_tokens || 0);

      // Progress bar
      const pc = document.getElementById('progress-container');
      pc.style.display = active ? 'flex' : 'none';

      // Status dot
      const dot = document.getElementById('status-dot');
      dot.className = 'status-dot' + (active ? '' : ' idle');

      // Timestamp
      const now = new Date();
      document.getElementById('ts').textContent =
        now.toLocaleTimeString('en-US', { hour12: false }) + ' local';
      document.getElementById('footer-gen').textContent =
        'last sync ' + now.toLocaleTimeString('en-US', { hour12: false });

      renderProjects(data);
      renderAgents(data);
      renderQueue(data);
    } catch(e) {
      document.getElementById('status-dot').className = 'status-dot idle';
    }
  }

  refresh();
  setInterval(refresh, 3000);
</script>
</body>
</html>
"""


def create_app(orchestrator: "MultiOrchestrator") -> FastAPI:
    app = FastAPI(title="Concerto", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(DASHBOARD_HTML)

    @app.get("/api/v1/state")
    async def api_state():
        return JSONResponse(orchestrator.get_state_snapshot())

    @app.get("/api/v1/{issue_identifier}")
    async def api_issue(issue_identifier: str):
        snap = orchestrator.get_state_snapshot()
        for r in snap["running"]:
            if r["issue_identifier"] == issue_identifier:
                return JSONResponse(r)
        for r in snap["retrying"]:
            if r["issue_identifier"] == issue_identifier:
                return JSONResponse(r)
        for g in snap["gates"]:
            if g["issue_identifier"] == issue_identifier:
                return JSONResponse(g)
        return JSONResponse(
            {"error": {"code": "issue_not_found", "message": f"Unknown: {issue_identifier}"}},
            status_code=404,
        )

    @app.post("/api/v1/refresh")
    async def api_refresh():
        asyncio.create_task(orchestrator.force_tick())
        return JSONResponse({"ok": True})

    @app.post("/api/v1/projects/{project_name}/pause")
    async def api_project_pause(project_name: str):
        if not orchestrator.pause(project_name):
            return JSONResponse(
                {"error": {"code": "project_not_found", "message": project_name}},
                status_code=404,
            )
        return JSONResponse({"ok": True, "project": project_name, "paused": True})

    @app.post("/api/v1/projects/{project_name}/resume")
    async def api_project_resume(project_name: str):
        if not orchestrator.resume(project_name):
            return JSONResponse(
                {"error": {"code": "project_not_found", "message": project_name}},
                status_code=404,
            )
        return JSONResponse({"ok": True, "project": project_name, "paused": False})

    @app.post("/api/v1/projects/{project_name}/toggle")
    async def api_project_toggle(project_name: str):
        if project_name not in orchestrator.project_names:
            return JSONResponse(
                {"error": {"code": "project_not_found", "message": project_name}},
                status_code=404,
            )
        now_paused = orchestrator.toggle(project_name)
        return JSONResponse({"ok": True, "project": project_name, "paused": now_paused})

    return app
