# app.py — ESP Remote Motion Dashboard (Flask)
# - POST /pir_event  (ESP sends JSON here; protected by X-API-Key)
# - GET  /live.json  (returns latest state for a selected node)
# - GET  /nodes.json (lists all nodes that reported)
# - GET  /           (simple live dashboard web page)

from flask import Flask, request, jsonify, render_template_string
import os, time

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "QAwsEDrfTGyhUJikOLp")

# node store: { "Room-1": { "last_update": int, "data": {"state": "...", "time": "..."} } }
nodes = {}

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP Remote Motion Dashboard</title>
<style>
:root{
  --bg:#0f172a; --card:#111827; --muted:#94a3b8; --accent:#22c55e; --warn:#f59e0b; --danger:#ef4444; --text:#e5e7eb;
}
*{box-sizing:border-box}
body{
  margin:0; padding:24px;
  background:linear-gradient(180deg,#0b1020 0%, #0f172a 100%);
  color:var(--text); font:16px/1.45 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}
.container{max-width:960px;margin:0 auto}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.title{font-size:22px;font-weight:700;letter-spacing:.2px}
.controls{display:flex;gap:10px;flex-wrap:wrap}
select,button{
  background:#0b1222;border:1px solid #1f2937;color:var(--text);
  padding:8px 10px;border-radius:8px;font-weight:600
}
button:hover{border-color:#334155;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media (max-width:820px){ .grid{grid-template-columns:repeat(2,1fr)} }
@media (max-width:560px){ .grid{grid-template-columns:1fr} }

.card{
  background:radial-gradient(1200px 600px at -10% -20%, rgba(124,58,237,.15), transparent 35%),
             radial-gradient(1000px 700px at 120% -20%, rgba(34,197,94,.15), transparent 40%),
             #0b1222;
  border:1px solid #1f2937; border-radius:14px; padding:16px; min-height:86px;
  box-shadow: 0 12px 28px rgba(2,6,23,.55) inset, 0 8px 24px rgba(0,0,0,.35);
}
.card h3{margin:0 0 8px 0;font-size:14px;color:var(--muted);font-weight:600}
.value{font-size:28px;font-weight:800;letter-spacing:.3px}
.kv{display:flex;align-items:center;justify-content:space-between;margin-top:10px;color:var(--muted)}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;font-size:12px}
.ok{background:rgba(34,197,94,.15);color:#86efac;border:1px solid rgba(34,197,94,.35)}
.warn{background:rgba(245,158,11,.12);color:#fcd34d;border:1px solid rgba(245,158,11,.35)}
.danger{background:rgba(239,68,68,.12);color:#fecaca;border:1px solid rgba(239,68,68,.35)}
.footer{margin-top:14px;color:var(--muted);font-size:13px}
.small{font-size:12px;color:var(--muted)}
.divider{height:1px;background:#1f2937;margin:10px 0}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title">ESP Remote Motion Dashboard</div>
    <div class="controls">
      <select id="nodeSel"></select>
      <button id="reloadBtn">Reload nodes</button>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Current state</h3>
      <div class="value" id="state">-</div>
      <div class="kv"><div>Time</div><div id="time" class="badge ok">-</div></div>
    </div>

    <div class="card">
      <h3>Motion counts</h3>
      <div class="value"><span id="motions">0</span> <span class="small">(confirmed <span id="confirmed">0</span>)</span></div>
      <div class="kv"><div>PIR hits</div><div id="pirHits" class="badge warn">0</div></div>
    </div>

    <div class="card">
      <h3>Vibration</h3>
      <div class="value" id="vibHits">0</div>
      <div class="kv"><div>Footsteps (est.)</div><div id="occupiedSec" class="badge">0s</div></div>
    </div>

    <div class="card">
      <h3>Raw signals</h3>
      <div class="kv"><div>PIR raw</div><div id="pirRaw" class="badge">0</div></div>
      <div class="kv"><div>VIB raw</div><div id="vibRaw" class="badge">0</div></div>
      <div class="divider"></div>
      <div class="kv"><div>Last update</div><div id="ago" class="badge">-</div></div>
    </div>

    <div class="card">
      <h3>Node</h3>
      <div class="value" id="nodeName">-</div>
      <div class="kv"><div>Status</div><div id="statusBadge" class="badge ok">Live</div></div>
    </div>
  </div>

  <div class="footer">Auto-refreshing every second. Reload nodes every 10s.</div>
</div>

<script>
async function j(p){ const r=await fetch(p,{cache:'no-store'}); return await r.json(); }

async function loadNodes(){
  const js = await j('/nodes.json');
  const sel = document.getElementById('nodeSel');
  const prev = sel.value; sel.innerHTML='';
  (js.nodes||[]).forEach(n => {
    const o = document.createElement('option');
    o.value=n; o.textContent=n; sel.appendChild(o);
  });
  if (js.nodes && js.nodes.length>0) sel.value = (prev && js.nodes.includes(prev))?prev:js.nodes[0];
}

function setText(id, val){ document.getElementById(id).textContent = val; }
function setBadge(id, cls){ const el=document.getElementById(id); el.className='badge '+cls; }

async function refresh(){
  const sel = document.getElementById('nodeSel');
  const node = sel.value;
  if (!node) { setText('state','-'); setText('time','-'); return; }
  const js = await j('/live.json?node='+encodeURIComponent(node));
  const d = js.data || {};
  const age = Math.max(0, Math.round(Date.now()/1000 - (js.last_update||0)));

  setText('nodeName', node);
  setText('state', d.state || '-');
  setText('time', d.time || '-');
  setText('motions', d.motions || 0);
  setText('confirmed', d.confirmed || 0);
  setText('pirHits', d.pirHits || 0);
  setText('vibHits', d.vibHits || 0);
  setText('occupiedSec', (d.occupiedSec||0)+'s');
  setText('pirRaw', d.pirRaw || 0);
  setText('vibRaw', d.vibRaw || 0);
  setText('ago', age+'s ago');

  // Color badges by state
  const st = (d.state||'').toLowerCase();
  if (st.includes('motion')) setBadge('statusBadge','warn');
  else if (st.includes('vibration')) setBadge('statusBadge','danger');
  else setBadge('statusBadge','ok');
}

document.getElementById('reloadBtn').addEventListener('click', loadNodes);
(async()=>{ await loadNodes(); setInterval(refresh,1000); setInterval(loadNodes,10000); refresh(); })();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/nodes.json")
def nodes_list():
    return jsonify({"nodes": sorted(nodes.keys())})

@app.route("/live.json")
def live():
    node = request.args.get("node")
    if not node:
        if not nodes: return jsonify({"last_update":0,"data":{}})
        node = sorted(nodes.keys())[0]
    return jsonify(nodes.get(node, {"last_update":0,"data":{}}))

@app.route("/pir_event", methods=["POST"])
def pir_event():
    if request.headers.get("X-API-Key") != API_KEY:
        return "Forbidden", 403
    data = request.get_json(silent=True) or {}
    node  = data.get("node","Room-1")
    state = data.get("state","-")       # "Motion" or "Vibration"
    t     = data.get("time","-")        # "HH:MM:SS" from device
    nodes[node] = { "last_update": int(time.time()), "data": {"state": state, "time": t} }
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
