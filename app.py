from flask import Flask, request, jsonify, render_template_string
import os, time

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "QAwsEDrfTGyhUJikOLp")  # set in Render

# Node store:
# nodes = {
#   "Room-1": {
#       "last_update": 0,
#       "data": {"state":"-", "time":"-", "pirHits":0, "vibHits":0}
#   }
# }
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
  --bg1:#0a0f2b; --bg2:#0f1e5f; --card:#0e1b4d;
  --border:#1b2a6b; --text:#e8eefc; --muted:#a6b4df;
  --accent:#4ea8ff; --accent2:#6ee7b7; --warn:#fbbf24; --danger:#f87171;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; padding:22px;
  color:var(--text);
  font:16px/1.45 ui-sans-serif,system-ui,Segoe UI,Roboto,Arial;
  background: radial-gradient(1000px 600px at -10% -20%, rgba(78,168,255,.12), transparent 45%),
              radial-gradient(1100px 700px at 110% -10%, rgba(110,231,183,.10), transparent 40%),
              linear-gradient(180deg, var(--bg1) 0%, var(--bg2) 100%);
}
.container{max-width:1024px;margin:0 auto}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.title{font-size:22px;font-weight:800;letter-spacing:.2px}
.controls{display:flex;gap:10px;flex-wrap:wrap}
select,button{
  background:rgba(13,28,84,.6); color:var(--text);
  border:1px solid var(--border); border-radius:10px;
  padding:8px 12px; font-weight:600; backdrop-filter: blur(6px);
}
button:hover{border-color:#2d3c86; cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media (max-width:900px){ .grid{grid-template-columns:repeat(2,1fr)} }
@media (max-width:600px){ .grid{grid-template-columns:1fr} }

.card{
  min-height:110px;
  background:
    radial-gradient(800px 480px at -10% -20%, rgba(78,168,255,.18), transparent 35%),
    radial-gradient(620px 420px at 120% -10%, rgba(110,231,183,.14), transparent 35%),
    linear-gradient(180deg, rgba(19,34,102,.6), rgba(9,18,66,.6));
  border:1px solid var(--border);
  border-radius:16px; padding:16px;
  box-shadow: inset 0 18px 28px rgba(0,0,0,.35), 0 10px 28px rgba(0,0,0,.25);
}
.card h3{margin:0 0 8px 0;font-size:13px;color:var(--muted);font-weight:700;letter-spacing:.6px;text-transform:uppercase}
.value{font-size:30px;font-weight:900;letter-spacing:.4px}
.rows{display:flex;justify-content:space-between;align-items:center;margin-top:8px;color:var(--muted)}
.badge{
  display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;
  font-size:12px;font-weight:700;border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.06)
}
.ok{color:#93e6b8;border-color:rgba(110,231,183,.4);background:rgba(110,231,183,.08)}
.warn{color:#fde68a;border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.08)}
.danger{color:#fecaca;border-color:rgba(248,113,113,.4);background:rgba(248,113,113,.08)}
.small{font-size:12px;color:var(--muted)}
.footer{margin-top:14px;color:var(--muted);font-size:13px}
.divider{height:1px;background:linear-gradient(90deg, transparent, #1b2a6b, transparent);margin:10px 0}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title">ESP Remote Motion Dashboard</div>
    <div class="controls">
      <select id="nodeSel" aria-label="Node selector"></select>
      <button id="reloadBtn">Reload nodes</button>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Current State</h3>
      <div class="value" id="state">-</div>
      <div class="rows"><div>Device time</div><div class="badge ok" id="time">-</div></div>
    </div>

    <div class="card">
      <h3>PIR Motion</h3>
      <div class="value"><span id="pirHits">0</span></div>
      <div class="rows"><div>Last update</div><div class="badge" id="agoPIR">-</div></div>
    </div>

    <div class="card">
      <h3>Vibration</h3>
      <div class="value"><span id="vibHits">0</span></div>
      <div class="rows"><div>Footsteps detected</div><div class="badge warn" id="footBadge">live</div></div>
    </div>

    <div class="card">
      <h3>Node</h3>
      <div class="value" id="nodeName">-</div>
      <div class="rows"><div>Status</div><div class="badge ok" id="statusBadge">Connected</div></div>
      <div class="divider"></div>
      <div class="rows"><div>Last update</div><div class="badge" id="ago">-</div></div>
    </div>
  </div>

  <div class="footer">Auto-refresh every 1s · Nodes list every 10s · Theme: Blue</div>
</div>

<script>
async function j(p){ const r=await fetch(p,{cache:'no-store'}); return await r.json(); }

function setText(id,val){ document.getElementById(id).textContent = (val ?? "-"); }
function setBadge(id,cls){ const el=document.getElementById(id); el.className="badge "+cls; }

async function loadNodes(){
  const js = await j('/nodes.json');
  const sel = document.getElementById('nodeSel');
  const prev = sel.value; sel.innerHTML='';
  (js.nodes||[]).forEach(n => { const o=document.createElement('option'); o.value=n; o.textContent=n; sel.appendChild(o); });
  if(js.nodes && js.nodes.length>0) sel.value = (prev && js.nodes.includes(prev)) ? prev : js.nodes[0];
  setText('nodeName', sel.value || "-");
}

async function refresh(){
  const node = document.getElementById('nodeSel').value;
  if(!node){ setText('state','-'); setText('time','-'); return; }
  const js = await j('/live.json?node='+encodeURIComponent(node));
  const d  = js.data || {};
  const age = Math.max(0, Math.round(Date.now()/1000 - (js.last_update||0)));

  setText('nodeName', node);
  setText('state', d.state || '-');
  setText('time',  d.time || '-');
  setText('pirHits', d.pirHits || 0);
  setText('vibHits', d.vibHits || 0);

  setText('ago', age+'s ago');
  setText('agoPIR', age+'s ago');
  document.getElementById('footBadge').textContent = (d.vibHits||0) > 0 ? "detected" : "idle";

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
    if not nodes:
      return jsonify({"last_update":0, "data":{}})
    node = sorted(nodes.keys())[0]
  return jsonify(nodes.get(node, {"last_update":0, "data":{}}))

@app.route("/pir_event", methods=["POST"])
def pir_event():
  if request.headers.get("X-API-Key") != API_KEY:
    return "Forbidden", 403

  data = request.get_json(silent=True) or {}
  node  = data.get("node","Room-1")
  state = data.get("state","-")      # "Motion" or "Vibration"
  t     = data.get("time","-")
  pirH  = int(data.get("pirHits", 0))
  vibH  = int(data.get("vibHits", 0))

  if node not in nodes:
    nodes[node] = {"last_update":0, "data":{"state":"-","time":"-","pirHits":0,"vibHits":0}}

  d = nodes[node]["data"]

  # Prefer device-supplied totals if nonzero; else increment
  if pirH>0 or vibH>0:
    if pirH>0: d["pirHits"] = pirH
    if vibH>0: d["vibHits"] = vibH
  else:
    if state.lower().startswith("motion"):   d["pirHits"] += 1
    if state.lower().startswith("vibration"):d["vibHits"] += 1

  d["state"] = state
  d["time"]  = t
  nodes[node]["last_update"] = int(time.time())
  return "OK", 200

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
