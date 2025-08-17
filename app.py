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
async function j(p){ const r=await fetch(p); return await r.json(); }
async function loadNodes(){
  const js = await j('/nodes.json');
  const sel = document.getElementById('nodeSel');
  const prev = sel.value; sel.innerHTML='';
  (js.nodes||[]).forEach(n=>{ const o=document.createElement('option'); o.value=n;o.textContent=n; sel.appendChild(o); });
  if (js.nodes && js.nodes.length>0) sel.value = (prev && js.nodes.includes(prev))?prev:js.nodes;
}
async function reloadNodes(){ await loadNodes(); }
async function refresh(){
  const node = document.getElementById('nodeSel').value;
  if(!node){ document.getElementById('root').textContent='No nodes yet...'; return; }
  const js = await j('/live.json?node='+encodeURIComponent(node));
  const d = js.data||{};
  const age = Math.max(0, Math.round(Date.now()/1000 - (js.last_update||0)));
  document.getElementById('root').innerHTML =
   `<div><b>Node:</b> ${node}</div>
    <div><b>State:</b> ${d.state||'-'}</div>
    <div><b>Time:</b> ${d.time||'-'}</div>
    <div><b>Last update:</b> ${age}s ago</div>`;
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
