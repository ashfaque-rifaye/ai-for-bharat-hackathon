#!/usr/bin/env python3
"""
VaaniSetu — Dev Control Panel (Local Web UI)
==============================================
A tiny local web server with a control panel to:
  - Stop/Start all backend Lambdas
  - View real-time resource status
  - View latest cost data from aws-costs.log

Run: python vaanisetu-panel.py
Opens at: http://localhost:4100
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import boto3

REGION = "us-east-1"
PORT = 4100
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aws-costs.log")

session = boto3.Session(region_name=REGION)
lam_client = session.client("lambda")


def get_vaanisetu_lambdas():
    fns = []
    for page in lam_client.get_paginator("list_functions").paginate():
        for fn in page.get("Functions", []):
            name = fn["FunctionName"]
            if "vaanisetu" in name.lower() or "VaaniSetu" in name:
                fns.append(name)
    return sorted(fns)


def get_lambda_status(fn_name):
    try:
        resp = lam_client.get_function_concurrency(FunctionName=fn_name)
        conc = resp.get("ReservedConcurrentExecutions")
        return "stopped" if conc == 0 else "running"
    except Exception:
        return "running"


def stop_all():
    lambdas = get_vaanisetu_lambdas()
    results = []
    for fn in lambdas:
        try:
            lam_client.put_function_concurrency(FunctionName=fn, ReservedConcurrentExecutions=0)
            results.append({"name": fn, "status": "stopped", "ok": True})
        except Exception as e:
            results.append({"name": fn, "status": str(e), "ok": False})
    return results


def start_all():
    lambdas = get_vaanisetu_lambdas()
    results = []
    for fn in lambdas:
        try:
            lam_client.delete_function_concurrency(FunctionName=fn)
            results.append({"name": fn, "status": "running", "ok": True})
        except Exception as e:
            results.append({"name": fn, "status": str(e), "ok": False})
    return results


def get_all_status():
    lambdas = get_vaanisetu_lambdas()
    return [{"name": fn, "status": get_lambda_status(fn)} for fn in lambdas]


def read_cost_log():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Cost monitor not running. Start it with: python aws-cost-monitor.py"


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VaaniSetu — Dev Control Panel</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  .container { max-width: 900px; margin: 0 auto; padding: 24px; }
  h1 { font-size: 1.5rem; color: #f97316; margin-bottom: 4px; }
  .subtitle { color: #64748b; font-size: 0.85rem; margin-bottom: 24px; }
  .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #334155; }
  .card h2 { font-size: 1rem; color: #94a3b8; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  .status-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #334155; }
  .status-row:last-child { border-bottom: none; }
  .fn-name { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.8rem; color: #cbd5e1; }
  .badge { padding: 3px 10px; border-radius: 9px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
  .badge.running { background: #065f46; color: #6ee7b7; }
  .badge.stopped { background: #7f1d1d; color: #fca5a5; }
  .controls { display: flex; gap: 12px; margin-top: 16px; }
  button { padding: 10px 24px; border: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  button:hover { transform: translateY(-1px); }
  button:active { transform: translateY(0); }
  button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .btn-stop { background: #dc2626; color: white; }
  .btn-stop:hover:not(:disabled) { background: #ef4444; }
  .btn-start { background: #16a34a; color: white; }
  .btn-start:hover:not(:disabled) { background: #22c55e; }
  .btn-refresh { background: #334155; color: #e2e8f0; }
  .btn-refresh:hover:not(:disabled) { background: #475569; }
  .overall { font-size: 1.2rem; font-weight: 700; margin: 8px 0; }
  .overall.running { color: #6ee7b7; }
  .overall.stopped { color: #fca5a5; }
  .log-box { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.75rem; line-height: 1.5; white-space: pre-wrap; color: #94a3b8; max-height: 500px; overflow-y: auto; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #475569; border-top-color: #f97316; border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .action-log { margin-top: 12px; font-size: 0.8rem; color: #64748b; }
  .flash { animation: flash-bg 0.5s; }
  @keyframes flash-bg { 0% { background: #f97316; } 100% { background: transparent; } }
</style>
</head>
<body>
<div class="container">
  <h1>🏛️ VaaniSetu — Dev Control Panel</h1>
  <p class="subtitle">Stop/Start AWS backend resources to save costs during development</p>

  <!-- Backend Control -->
  <div class="card">
    <h2>Backend Status</h2>
    <div class="overall" id="overall">Loading...</div>
    <div id="lambda-list"></div>
    <div class="controls">
      <button class="btn-stop" id="btn-stop" onclick="doStop()">⏹ Stop All</button>
      <button class="btn-start" id="btn-start" onclick="doStart()">▶ Start All</button>
      <button class="btn-refresh" id="btn-refresh" onclick="refresh()">🔄 Refresh</button>
    </div>
    <div class="action-log" id="action-log"></div>
  </div>

  <!-- Cost Log -->
  <div class="card">
    <h2>AWS Cost Monitor</h2>
    <div id="cost-log" class="log-box">Loading cost data...</div>
    <div style="margin-top: 8px;">
      <button class="btn-refresh" onclick="refreshCosts()">🔄 Refresh Costs</button>
    </div>
  </div>
</div>

<script>
const API = '';

async function refresh() {
  setButtons(true);
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    renderStatus(data);
  } catch(e) {
    document.getElementById('overall').textContent = 'Error: ' + e.message;
    document.getElementById('overall').className = 'overall stopped';
  }
  setButtons(false);
}

async function doStop() {
  if (!confirm('Stop all VaaniSetu backend Lambdas? The API will become unavailable.')) return;
  setButtons(true);
  log('Stopping all Lambdas...');
  try {
    const resp = await fetch('/api/stop', { method: 'POST' });
    const data = await resp.json();
    log('Stopped ' + data.length + ' functions.');
    await refresh();
  } catch(e) {
    log('Error: ' + e.message);
  }
  setButtons(false);
}

async function doStart() {
  setButtons(true);
  log('Starting all Lambdas...');
  try {
    const resp = await fetch('/api/start', { method: 'POST' });
    const data = await resp.json();
    log('Started ' + data.length + ' functions.');
    await refresh();
  } catch(e) {
    log('Error: ' + e.message);
  }
  setButtons(false);
}

async function refreshCosts() {
  try {
    const resp = await fetch('/api/costs');
    const text = await resp.text();
    document.getElementById('cost-log').textContent = text;
  } catch(e) {
    document.getElementById('cost-log').textContent = 'Error loading costs: ' + e.message;
  }
}

function renderStatus(lambdas) {
  const list = document.getElementById('lambda-list');
  const overall = document.getElementById('overall');
  const allRunning = lambdas.every(l => l.status === 'running');
  const allStopped = lambdas.every(l => l.status === 'stopped');

  if (allRunning) {
    overall.textContent = '● RUNNING';
    overall.className = 'overall running';
  } else if (allStopped) {
    overall.textContent = '● STOPPED';
    overall.className = 'overall stopped';
  } else {
    overall.textContent = '● PARTIAL';
    overall.className = 'overall stopped';
  }

  list.innerHTML = lambdas.map(l => `
    <div class="status-row">
      <span class="fn-name">${l.name}</span>
      <span class="badge ${l.status}">${l.status}</span>
    </div>
  `).join('');
}

function setButtons(disabled) {
  document.querySelectorAll('button').forEach(b => b.disabled = disabled);
}

function log(msg) {
  const el = document.getElementById('action-log');
  const time = new Date().toLocaleTimeString();
  el.textContent = `[${time}] ${msg}`;
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

// Initial load
refresh();
refreshCosts();
// Auto-refresh every 30s
setInterval(refreshCosts, 30000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif path == "/api/status":
            data = get_all_status()
            self._json(data)
        elif path == "/api/costs":
            text = read_cost_log()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(text.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/stop":
            data = stop_all()
            self._json(data)
        elif path == "/api/start":
            data = start_all()
            self._json(data)
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):
        # Quieter logging
        pass


def main():
    print(f"\033[1m\033[96mVaaniSetu Dev Control Panel\033[0m")
    print(f"  http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop\n")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nControl panel stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
