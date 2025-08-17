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
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP Remote Motion Dashboard</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:18px;max-width:900px}
 .row{display:flex;gap:12px;flex-wrap:wrap}
 .card{flex:1 1 260px;border:1px solid #ddd;border-radius:10px;padding:12px}
 .title{font-weight:700;font-size:18px;margin-bottom:8px}
 select,button{padding:6px 10px;font-size:15px}
 .dim{color:#666}
 .big{font-size:26px;font-weight:800}
</style>
</head>
<body>
<h2>ESP Remote Motion Dashboard</h2>
<div class="card">
  <label for="nodeSel"><b>Node:</b></label>
  <select id="nodeSel"></select>
  <button onclick="reloadNodes()">Reload nodes</button>
</div>
<div class="row">
  <div class="card">
    <div class="title">Current</div>
    <div class="big" id="state">-</div>
    <div class="dim">Time: <span id="time">-</span></div>
  </div>
  <div class="card">
    <div class="title">Counts</div>
    <div>PIR hits: <b id="pirHits">0</b></div>
    <div>Vibration hits: <b id="vibHits">0</b></div>
    <div class="dim">Last update: <span id="ago">-</span></div>
  </div>
</div>
<script>
async function getJ(p){ const r=await fetch(p,{cache:'no-store'}); return await r.json(); }
async function loadNodes(){
  const js = await getJ('/nodes.json');
  const sel = document.getElementById('nodeSel');
  const prev = sel.value; sel.innerHTML = '';
  (js.nodes||[]).forEach(n=>{
    const o=document.createElement('option'); o.value=n; o.textContent=n; sel.appendChild(o);
  });
  if(js.nodes && js.nodes.length>0) sel.value=(prev&&js.nodes.includes(prev))?prev:js.nodes[0];
}
async function reloadNodes(){ await loadNodes(); }
async function refresh(){
  const node = document.getElementById('nodeSel').value;
  if(!node){ document.getElementById('state').textContent='No nodes'; return; }
  const js = await getJ('/live.json?node='+encodeURIComponent(node));
  const d  = js.data||{};
  const age = Math.max(0, Math.round(Date.now()/1000 - (js.last_update||0)));
  document.getElementById('state').textContent = d.state || '-';
  document.getElementById('time').textContent  = d.time  || '-';
  document.getElementById('pirHits').textContent = d.pirHits || 0;
  document.getElementById('vibHits').textContent = d.vibHits || 0;
  document.getElementById('ago').textContent = age + 's ago';
}
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
