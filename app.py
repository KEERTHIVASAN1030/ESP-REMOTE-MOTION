# app.py — ESP Remote Motion Dashboard (Flask)
# - POST /pir_event  (ESP sends JSON here; protected by X-API-Key)
# - GET  /live.json  (returns latest state for a selected node)
# - GET  /nodes.json (lists all nodes that reported)
# - GET  /           (simple live dashboard web page)

from flask import Flask, request, jsonify, render_template_string
from time import time
import os

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "change-me")  # set this when running/deploying

# Store last state per node: { node: { "last_update": int, "data": {...} } }
nodes = {}

HTML = """
<!doctype html>
<html>
<head>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>ESP Remote Motion Dashboard</title>
  <style>
    body{font-family:sans-serif;margin:18px;max-width:700px}
    .card{border:1px solid #ddd;border-radius:8px;padding:12px;margin:10px 0}
    select,button{font-size:16px;padding:6px}
  </style>
</head>
<body>
  <h2>ESP Remote Motion Dashboard</h2>

  <div class="card">
    <label for="nodeSel"><b>Node:</b></label>
    <select id="nodeSel"></select>
    <button onclick="reloadNodes()">Reload nodes</button>
  </div>

  <div id="root" class="card">Loading...</div>

<script>
async function getJSON(p){ const r = await fetch(p); return await r.json(); }

async function loadNodes(){
  const j = await getJSON('/nodes.json');
  const sel = document.getElementById('nodeSel');
  const prev = sel.value;
  sel.innerHTML = '';
  (j.nodes||[]).forEach(n=>{
    const o=document.createElement('option'); o.value=n; o.textContent=n; sel.appendChild(o);
  });
  if (j.nodes && j.nodes.length>0){
    sel.value = (prev && j.nodes.includes(prev)) ? prev : j.nodes[0];
  }
}
async function reloadNodes(){ await loadNodes(); }

async function refresh(){
  const node = document.getElementById('nodeSel').value;
  if(!node){ document.getElementById('root').textContent='No nodes yet. Waiting for device data...'; return; }
  const j = await getJSON('/live.json?node='+encodeURIComponent(node));
  const d = j.data || {};
  const age = Math.max(0, Math.round(Date.now()/1000 - (j.last_update||0)));
  document.getElementById('root').innerHTML =
    `<div><b>Node:</b> ${node}</div>
     <div><b>State:</b> ${d.state||'-'}</div>
     <div><b>Time:</b> ${d.time||'-'}</div>
     <div><b>Total motions:</b> ${d.motions||0} (confirmed ${d.confirmed||0})</div>
     <div><b>Counts:</b> PIR ${d.pirHits||0}, VIB ${d.vibHits||0}</div>
     <div><b>Occupied today:</b> ${d.occupiedSec||0}s</div>
     <div><b>Raw:</b> PIR ${d.pirRaw||0} VIB ${d.vibRaw||0}</div>
     <div><b>Last update:</b> ${age}s ago</div>`;
}

(async()=>{
  await loadNodes();
  setInterval(refresh, 1000);
  setInterval(loadNodes, 10000);
  refresh();
})();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/nodes.json")
def nodes_list():
    return jsonify({"nodes": sorted(list(nodes.keys()))})

@app.route("/live.json")
def live():
    node = request.args.get("node")
    if not node:
        if len(nodes) == 0:
            return jsonify({"last_update": 0, "data": {}})
        node = sorted(list(nodes.keys()))[0]
    return jsonify(nodes.get(node, {"last_update": 0, "data": {}}))

@app.route("/pir_event", methods=["POST"])
def pir_event():
    if request.headers.get("X-API-Key") != API_KEY:
        return "Forbidden", 403
    try:
        payload = request.get_json(force=True)
    except Exception:
        return "Bad JSON", 400
    node = payload.get("node", "Node-1")
    if node not in nodes:
        nodes[node] = {"last_update": 0, "data": {}}
    nodes[node]["data"].update(payload)
    nodes[node]["last_update"] = int(time())
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))