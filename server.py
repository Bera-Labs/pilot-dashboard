#!/usr/bin/env python3
"""Pilot Dashboard Backend — Bidirectional API server with JSON file state storage.
Hermes reads/writes the same state files directly. Dashboard calls REST endpoints.
"""
import json, os, time, http.server, urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
ASSETS_DIR = Path(__file__).parent / "assets"
STATE_FILE = DATA_DIR / "state.json"
PORT = 8080

def default_state():
    return {
        "mission_start": "2026-05-18T04:00:00",
        "metrics": {"wip": 0, "completed": 0, "ooda_last": None, "avg_latency": None},
        "decisions": [],
        "activity_log": [
            {"time": time.strftime("%H:%M:%S"), "type": "BOOT", "message": "Dashboard initialized"},
            {"time": time.strftime("%H:%M:%S"), "type": "LOAD", "message": "STEM Stack v1.0 active"},
            {"time": time.strftime("%H:%M:%S"), "type": "STATUS", "message": "Bidirectional mode online"}
        ],
        "properties": {"tracked": 0, "viewings": 0, "offers": 0}
    }

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = default_state()
        save_state(state)
        return state

def save_state(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ASSETS_DIR), **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == '/api/state':
            self._send_json(load_state())
        elif path.startswith('/api/'):
            self._send_json({"error": "unknown endpoint"}, 404)
        else:
            # Serve static files from assets/
            super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        state = load_state()
        now = time.strftime("%H:%M:%S")

        if path == '/api/log-decision':
            state['decisions'].append({
                "title": body.get('title', ''),
                "confidence": body.get('confidence', 50),
                "rationale": body.get('rationale', ''),
                "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "resolved": False,
                "outcome": None
            })
            state['activity_log'].insert(0, {"time": now, "type": "DECISION", "message": f"\"{body.get('title','')}\" — {body.get('confidence',50)}% confidence"})

        elif path == '/api/resolve-decision':
            pending = [d for d in state['decisions'] if not d['resolved']]
            if pending:
                pending[-1]['resolved'] = True
                pending[-1]['outcome'] = body.get('outcome', False)
                pending[-1]['resolvedDate'] = time.strftime("%Y-%m-%dT%H:%M:%S")
                # Calibration
                resolved = [d for d in state['decisions'] if d['resolved']]
                correct = sum(1 for d in resolved if d['outcome'] is True)
                total = len(resolved)
                avg_conf = sum(d['confidence'] for d in resolved) / total if total > 0 else 0
                state['activity_log'].insert(0, {"time": now, "type": "CALIBRATE", "message": f"{correct}/{total} correct ({round(correct/total*100)}%) vs avg {round(avg_conf)}% confidence"})

        elif path == '/api/log-completion':
            state['metrics']['completed'] = state['metrics'].get('completed', 0) + 1
            state['metrics']['wip'] = max(0, state['metrics'].get('wip', 0) - 1)
            state['activity_log'].insert(0, {"time": now, "type": "COMPLETE", "message": f"Task finished. WIP: {state['metrics']['wip']} | Total: {state['metrics']['completed']}"})

        elif path == '/api/set-wip':
            state['metrics']['wip'] = body.get('count', 0)

        elif path == '/api/set-ooda':
            sec = body.get('seconds', 0)
            state['metrics']['ooda_last'] = sec
            state['activity_log'].insert(0, {"time": now, "type": "OODA", "message": f"Cycle complete: {sec}s"})

        elif path == '/api/add-log':
            state['activity_log'].insert(0, {"time": now, "type": body.get('type', 'INFO'), "message": body.get('message', '')})

        elif path == '/api/update-properties':
            for key in ['tracked', 'viewings', 'offers']:
                if key in body:
                    state['properties'][key] = body[key]

        else:
            self._send_json({"error": "unknown endpoint"}, 404)
            return

        # Trim log
        if len(state['activity_log']) > 100:
            state['activity_log'] = state['activity_log'][:100]

        save_state(state)
        self._send_json({"status": "ok"})

if __name__ == '__main__':
    print(f"◆ Pilot Dashboard Backend")
    print(f"  API:    http://localhost:{PORT}/api/state")
    print(f"  UI:     http://localhost:{PORT}/dashboard.html")
    print(f"  Data:   {STATE_FILE}")
    print(f"  GitHub: https://bera-labs.github.io/pilot-dashboard/")

    server = http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown.")
