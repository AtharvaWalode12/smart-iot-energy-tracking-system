#!/usr/bin/env python3
"""Local Smart IoT Energy Audit demo. Uses simulated readings; no dependencies."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json, math, os, random, time

PORT = int(os.environ.get("PORT", "8765"))
PROFILES = {
    "Residential": [
        ("HVAC", 1.65, "Cooling"), ("Water heater", 1.20, "Heating"),
        ("Refrigerator", .18, "Always on"), ("Lighting", .32, "Lighting"),
        ("Kitchen", .85, "Appliances"), ("Washer", .55, "Appliances"),
        ("Standby loads", .11, "Standby"),
    ],
    "Commercial": [
        ("HVAC plant", 8.5, "Cooling"), ("Lighting", 3.2, "Lighting"),
        ("IT equipment", 2.4, "Always on"), ("Ventilation", 1.4, "Cooling"),
        ("Kitchen", 1.8, "Appliances"), ("Standby loads", .42, "Standby"),
    ],
    "Industrial": [
        ("Production motors", 18.0, "Motors"), ("Compressor", 7.2, "Motors"),
        ("Process heating", 9.5, "Heating"), ("HVAC", 4.3, "Cooling"),
        ("Lighting", 1.8, "Lighting"), ("Standby loads", .75, "Standby"),
    ],
}

def get_data(q):
    site = q.get("site", ["Commercial"])[0]
    if site not in PROFILES: site = "Commercial"
    selected = set(q.get("loads", [] if q.get("monitoring") else [x[0] for x in PROFILES[site]]))
    loads = [x for x in PROFILES[site] if x[0] in selected]
    voltage = max(180, min(260, float(q.get("voltage", [230])[0])))
    pf = max(.5, min(1, float(q.get("pf", [.92])[0])))
    tariff = max(0, min(100, float(q.get("tariff", [8])[0])))
    limit = max(.1, float(q.get("limit", [18])[0]))
    seed = int(time.time() // 3)
    rng = random.Random(seed + len(site) + len(selected))
    hour = time.localtime().tm_hour
    readings = []
    for name, base, category in loads:
        factor = .62 + .24 * math.sin((hour - 7) * math.pi / 12) + rng.uniform(-.06, .06)
        if category == "Always on": factor = .8 + rng.uniform(-.04, .04)
        if category == "Standby": factor = 1
        if category == "Lighting": factor = .75 if hour < 7 or hour > 17 else .38
        if category == "Motors": factor = .88 + rng.uniform(-.08, .08)
        if category == "Appliances": factor = .45 + rng.random() * .45
        kw = max(.01, base * factor)
        readings.append({"name": name, "kw": round(kw, 2), "category": category, "base": base})
    active = sum(x["kw"] for x in readings)
    current = active * 1000 / (voltage * pf) if voltage and pf else 0
    apparent = active / pf
    reactive = math.sqrt(max(0, apparent**2 - active**2))
    energy_day = active * 24 * .66
    cost_day = energy_day * tariff
    alerts = []
    if active > limit: alerts.append({"type":"critical", "text":f"Peak load {active:.1f} kW exceeds your {limit:.1f} kW threshold."})
    if voltage < 207 or voltage > 253: alerts.append({"type":"warning", "text":f"Voltage {voltage:.0f} V is outside the nominal ±10% band."})
    if pf < .85: alerts.append({"type":"warning", "text":f"Power factor {pf:.2f} is low; review reactive loads and correction."})
    standby = sum(x["kw"] for x in readings if x["category"] == "Standby")
    if standby > 0: alerts.append({"type":"info", "text":f"Estimated standby draw: {standby:.2f} kW ({standby*24:.1f} kWh/day if continuous)."})
    if not alerts: alerts.append({"type":"good", "text":"No threshold or power-quality alerts for this operating point."})
    profile = []
    for h in range(24):
        mult = .55 + .30 * math.sin((h - 7) * math.pi / 12)
        if 0 <= h <= 5: mult = .48
        if 8 <= h <= 17: mult = .86
        if site == "Industrial": mult = .82 if 6 <= h <= 21 else .48
        profile.append(round(active * mult, 2))
    return {"site":site,"loads":readings,"voltage":voltage,"pf":pf,"tariff":tariff,"limit":limit,
            "active":round(active,2),"current":round(current,1),"apparent":round(apparent,2),"reactive":round(reactive,2),
            "energy_day":round(energy_day,1),"cost_day":round(cost_day,2),"cost_month":round(cost_day*30,2),
            "carbon_day":round(energy_day*.42,1),"alerts":alerts,"profile":profile,"updated":time.strftime("%H:%M:%S")}

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wattwise · Energy audit</title>
<style>
:root{--bg:#f4f6f4;--ink:#17251f;--muted:#77847d;--line:#e7ebe7;--green:#157d58;--lime:#d9f36b;--panel:#fff;--red:#c34f3d}*{box-sizing:border-box}body{margin:0;background:var(--bg);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif;color:var(--ink)}.shell{max-width:1440px;margin:auto;display:grid;grid-template-columns:230px 1fr;min-height:100vh}.side{background:#14251f;color:#eef6ef;padding:28px 19px;display:flex;flex-direction:column}.brand{font-size:20px;font-weight:750;letter-spacing:-.7px}.brand i{color:var(--lime);font-style:normal}.tag{color:#91a29a;font-size:11px;margin:3px 0 39px}.navlabel{color:#81948a;text-transform:uppercase;letter-spacing:1.3px;font-size:10px;margin:0 10px 10px}.nav{display:flex;gap:11px;padding:11px 12px;border-radius:9px;color:#b5c4bc;margin-bottom:4px}.nav.active{background:#263b32;color:#fff}.nav b{font-size:16px;font-weight:500}.sidefoot{margin-top:auto;border-top:1px solid #31443b;padding:17px 8px 0;color:#a1b1a8;font-size:11px}.dot{width:7px;height:7px;background:#74d28b;display:inline-block;border-radius:100%;margin-right:6px}.main{padding:29px 38px 44px;max-width:1250px;width:100%;margin:auto;display:flex;flex-direction:column}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:27px;order:0}.eyebrow{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.3px}.h1{font-size:28px;letter-spacing:-1.1px;margin:4px 0;font-weight:650}.sub{color:var(--muted);font-size:13px}.topright{display:flex;align-items:center;gap:10px}.pill{padding:7px 11px;border:1px solid var(--line);background:#fff;border-radius:20px;font-size:11px;color:#536159}.live{color:var(--green);font-weight:650}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;order:2}.card{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:17px 18px}.metriclabel{color:var(--muted);font-size:12px}.metric{font-size:27px;font-weight:650;letter-spacing:-1px;margin:7px 0 1px}.unit{font-size:13px;color:#65746c;font-weight:450}.delta{font-size:11px;color:var(--green)}.sectiongrid{display:grid;grid-template-columns:1.7fr 1fr;gap:14px;margin-top:14px}.telemetry{order:3}.monitoring{order:4}.cardhead{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px}.title{font-size:14px;font-weight:650}.desc{font-size:11px;color:var(--muted);margin-top:2px}.chart{width:100%;height:200px}.chart svg{height:100%;width:100%;overflow:visible}.gridline{stroke:#eef1ee;stroke-width:1}.chartline{fill:none;stroke:#17845e;stroke-width:2.5}.chartfill{fill:url(#fade)}.axis{font-size:10px;fill:#87928c}.legend{font-size:10px;color:#78857e}.loadrow{display:grid;grid-template-columns:1fr 75px 36px;align-items:center;gap:10px;margin:13px 0}.loadname{font-size:12px}.barbg{height:6px;background:#eff2ef;border-radius:8px;overflow:hidden}.bar{height:100%;background:#17845e;border-radius:8px}.kw{font-size:11px;color:#69776f;text-align:right}.alerts{margin-top:14px}.alert{border-radius:9px;padding:10px 12px;margin:8px 0;font-size:12px;display:flex;gap:9px;align-items:flex-start}.critical{background:#fff1ee;color:#9e3f31}.warning{background:#fff8e8;color:#8b6418}.info{background:#eef6f2;color:#2a6d50}.good{background:#eff7e6;color:#4d6c27}.controls{margin-top:0;order:1}.controlsgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:19px}.control label{display:flex;justify-content:space-between;font-size:12px;margin-bottom:9px}.control strong{color:var(--green)}input[type=range]{width:100%;accent-color:#157d58}.select{width:100%;border:1px solid var(--line);padding:9px;border-radius:8px;background:#fff;color:var(--ink)}.checkloads{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.checkloads label{border:1px solid var(--line);border-radius:20px;padding:5px 10px;font-size:11px;color:#526158;cursor:pointer}.checkloads input{accent-color:#157d58}.actions{display:flex;gap:9px}.button{border:1px solid var(--line);background:#fff;color:#27362e;padding:9px 12px;border-radius:8px;cursor:pointer;font:inherit;font-size:11px}.button.primary{background:#157d58;color:white;border-color:#157d58}.footnote{margin-top:18px;color:#8b9690;font-size:10px}.main>.footnote{order:5}.hidden{display:none}@media(max-width:900px){.shell{grid-template-columns:1fr}.side{display:none}.main{padding:22px 16px}.grid{grid-template-columns:repeat(2,1fr)}.sectiongrid{grid-template-columns:1fr}.controlsgrid{grid-template-columns:repeat(2,1fr)}}
</style><style>
.nav{cursor:pointer}.nav:hover{background:#20362d;color:white}.pageview{order:1;margin-bottom:14px}.pageview h2{font-size:21px;letter-spacing:-.5px;margin:0 0 4px}.pagelead{color:var(--muted);margin:0 0 18px;font-size:13px}.tablewrap{overflow:auto}.audit-table{width:100%;border-collapse:collapse;font-size:12px}.audit-table th{text-align:left;color:#75827b;font-size:10px;text-transform:uppercase;letter-spacing:.6px;padding:10px 11px;border-bottom:1px solid var(--line);white-space:nowrap}.audit-table td{padding:11px;border-bottom:1px solid #eff1ef}.audit-table tr:last-child td{border:0}.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.tagpill{display:inline-block;border-radius:20px;background:#f0f5f1;color:#496458;padding:4px 8px;font-size:10px}.audit-summary{background:#eff7f2;border-radius:10px;padding:14px 16px;margin-bottom:14px;color:#315a45}.audit-summary strong{color:#174f36}.audit-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.audit-kpi{padding:13px;background:#f7f9f7;border-radius:9px}.audit-kpi span{display:block;color:var(--muted);font-size:10px}.audit-kpi strong{display:block;font-size:18px;margin-top:3px}.print-button{background:#157d58;border-color:#157d58;color:#fff}.print-meta{display:flex;gap:20px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:12px 0}.good-action{color:#27724e}.audit-actions{margin-top:14px}.section-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.print-only{display:none}
@media print{body{background:#fff}.shell{display:block;max-width:none}.side,.top,.grid,.sectiongrid,.controls,.main>.footnote,#loadpage,#settingspage{display:none!important}.main{display:block;padding:0;max-width:none}.pageview{display:none!important}#auditpage{display:block!important;border:0;box-shadow:none;padding:0}.print-only{display:block}.audit-table th,.audit-table td{padding:8px;border-bottom:1px solid #ddd}.audit-summary{background:#f3f5f3!important;color:#17251f!important;print-color-adjust:exact}.audit-kpi{background:#f7f7f7!important;print-color-adjust:exact}.print-button{display:none}}
@media(max-width:900px){.audit-kpis{grid-template-columns:repeat(2,1fr)}.side{display:flex;flex-direction:row;align-items:center;gap:4px;position:sticky;top:0;z-index:3;overflow-x:auto;padding:9px 10px}.brand{font-size:16px;white-space:nowrap}.tag,.navlabel,.sidefoot{display:none}.nav{flex:0 0 auto;white-space:nowrap;font-size:11px;padding:8px 9px;margin:0}.nav b{font-size:14px}.main{max-width:none}}.credit{order:6;margin-top:auto;padding:18px 0 2px;text-align:center;color:#157d58;font-size:11px;font-weight:600;letter-spacing:.25px}.credit span{opacity:.86}
</style></head><body><div class="shell"><aside class="side"><div class="brand">wattwise<i>.</i></div><div class="tag">SMART ENERGY INTELLIGENCE</div><div class="navlabel">WORKSPACE</div><div class="nav active" data-page="overview"><b>⌂</b> Energy overview</div><div class="nav" data-page="loads"><b>▥</b> Load breakdown</div><div class="nav" data-page="audit"><b>⌁</b> Audit insights</div><div class="nav" data-page="settings"><b>⚙</b> System settings</div><div class="sidefoot"><span class="dot"></span>Local simulator online<br><span style="margin-left:13px">Sensor gateway · demo mode</span></div></aside>
<main class="main"><div class="top"><div><div class="eyebrow" id="eyebrow">ENERGY MANAGEMENT / OVERVIEW</div><div class="h1" id="pagetitle">Energy audit dashboard</div><div class="sub" id="pagesub">Monitor demand, explore load patterns, and find savings opportunities.</div></div><div class="topright"><span class="pill"><span class="dot"></span><span class="live">LIVE SIMULATION</span></span><span class="pill" id="clock">--:--:--</span></div></div>
<section id="loadpage" class="card pageview hidden"><div class="section-heading"><div><h2>Load breakdown</h2><p class="pagelead">See how each selected load contributes to demand, energy use, and estimated cost.</p></div></div><div class="audit-kpis" id="loadkpis"></div><div class="tablewrap"><table class="audit-table"><thead><tr><th>Load</th><th>Type</th><th class="num">Demand</th><th class="num">Est. energy / day</th><th class="num">Est. cost / day</th><th class="num">Share</th></tr></thead><tbody id="loadtable"></tbody><tfoot id="loadtotal"></tfoot></table></div><p class="footnote">Estimates use the selected profile's typical utilization factor. Simulated readings are not utility meter data.</p></section>
<section id="auditpage" class="card pageview hidden"><div class="section-heading"><div><h2>Energy audit insights</h2><p class="pagelead">A simple snapshot of current operating conditions and practical next steps.</p></div><button class="button print-button" onclick="window.print()">Print audit</button></div><div class="print-meta"><span><b>Facility:</b> <span id="audit-site"></span></span><span><b>Prepared:</b> <span id="audit-date"></span></span><span><b>Data source:</b> Local simulation</span></div><div class="audit-summary" id="audit-summary"></div><div class="audit-kpis" id="audit-kpis"></div><div class="cardhead"><div><div class="title">Recommended actions</div><div class="desc">Start with the items that can lower waste or reduce operating risk.</div></div></div><div class="tablewrap"><table class="audit-table"><thead><tr><th>Priority</th><th>Finding</th><th>Suggested action</th><th>Expected benefit</th></tr></thead><tbody id="recommendations"></tbody></table></div><div class="cardhead" style="margin-top:22px"><div><div class="title">Audit conditions</div><div class="desc">Inputs used for these estimates</div></div></div><div class="tablewrap"><table class="audit-table"><tbody id="audit-conditions"></tbody></table></div><p class="footnote">This demonstration report is based on synthetic profile data. Confirm findings with calibrated meters and a qualified energy auditor before making operational or investment decisions.</p><div class="print-only" style="margin-top:20px;font-size:10px;color:#68756e">Wattwise · Smart energy audit demonstration</div></section>
<section id="settingspage" class="card pageview hidden"><h2>System settings</h2><p class="pagelead">Set the facility profile, monitoring parameters, and alert threshold below.</p><p class="desc">Changes apply to the dashboard and audit insights immediately.</p></section>
<div id="metrics" class="grid"><div class="card"><div class="metriclabel">Active demand</div><div class="metric"><span id="active">—</span> <span class="unit">kW</span></div><div class="delta">● Current selected load mix</div></div><div class="card"><div class="metriclabel">Energy estimate</div><div class="metric"><span id="energy">—</span> <span class="unit">kWh / day</span></div><div class="delta">Based on typical operating profile</div></div><div class="card"><div class="metriclabel">Estimated daily cost</div><div class="metric">₹<span id="cost">—</span></div><div class="delta">₹<span id="month">—</span> / 30-day month</div></div><div class="card"><div class="metriclabel">Carbon estimate</div><div class="metric"><span id="carbon">—</span> <span class="unit">kg CO₂ / day</span></div><div class="delta">Grid factor · 0.42 kg / kWh</div></div></div>
<div class="sectiongrid telemetry"><div class="card"><div class="cardhead"><div><div class="title">Daily demand profile</div><div class="desc">Illustrative 24-hour load curve · kW</div></div><span class="pill" id="sitepill">Commercial</span></div><div class="chart" id="chart"></div></div><div class="card"><div class="cardhead"><div><div class="title">Electrical parameters</div><div class="desc">Derived from selected profile and inputs</div></div></div><div class="loadrow"><span class="loadname">Voltage</span><div class="barbg"><div class="bar" id="vbar"></div></div><span class="kw"><span id="vread">—</span> V</span></div><div class="loadrow"><span class="loadname">Current</span><div class="barbg"><div class="bar" id="ibar"></div></div><span class="kw"><span id="iread">—</span> A</span></div><div class="loadrow"><span class="loadname">Power factor</span><div class="barbg"><div class="bar" id="pfbar"></div></div><span class="kw" id="pfread">—</span></div><div class="loadrow"><span class="loadname">Reactive power</span><div class="barbg"><div class="bar" id="qbar"></div></div><span class="kw"><span id="qread">—</span> kVAr</span></div><div class="loadrow"><span class="loadname">Apparent power</span><div class="barbg"><div class="bar" id="sbar"></div></div><span class="kw"><span id="sread">—</span> kVA</span></div><div class="desc" style="margin-top:18px">Illustrative estimates; actual power quality requires calibrated meters.</div></div></div>
<div class="sectiongrid monitoring"><div class="card"><div class="cardhead"><div><div class="title">Load monitoring</div><div class="desc">Estimated contribution by monitored load</div></div><div class="actions"><button class="button" onclick="selectAll(true)">Select all</button><button class="button" onclick="selectAll(false)">Clear</button></div></div><div id="loadlist"></div></div><div class="card"><div class="cardhead"><div><div class="title">Audit alerts</div><div class="desc">Threshold and efficiency observations</div></div></div><div class="alerts" id="alerts"></div></div></div>
<div id="controls" class="card controls"><div class="cardhead"><div><div class="title">Scenario & audit parameters</div><div class="desc">Change operating conditions to compare load monitoring scenarios</div></div><button class="button primary" onclick="downloadReport()">↓ &nbsp;Export audit JSON</button></div><div class="controlsgrid"><div class="control"><label>Facility profile <strong id="siteval">Commercial</strong></label><select class="select" id="site"><option>Residential</option><option selected>Commercial</option><option>Industrial</option></select></div><div class="control"><label>Supply voltage <strong><span id="voltageval">230</span> V</strong></label><input id="voltage" type="range" min="190" max="255" value="230"></div><div class="control"><label>Power factor <strong id="pfval">0.92</strong></label><input id="pf" type="range" min="0.60" max="1.00" step="0.01" value="0.92"></div><div class="control"><label>Energy tariff <strong>₹<span id="tariffval">8</span> / kWh</strong></label><input id="tariff" type="range" min="3" max="25" step="0.5" value="8"></div></div><div class="control" style="margin-top:16px;max-width:320px"><label>Demand alert threshold <strong><span id="limitval">18</span> kW</strong></label><input id="limit" type="range" min="2" max="35" step="0.5" value="18"></div><div class="checkloads" id="checks"></div><div class="footnote">Simulation only: values are synthetic estimates for learning and demonstration, not billing, safety, or ISO 50001 compliance measurements.</div></div>
<div class="footnote">Wattwise local demo · NILM-style load estimates are profile-based and do not use trained machine learning. Connect CT / voltage sensors and a gateway for field measurements.</div><div class="credit"><span>Developed by Atharva N. Walode</span></div></main></div>
<script>
let data=null,timer=null;const $=x=>document.getElementById(x);const enc=x=>encodeURIComponent(x);
function params(){let p=new URLSearchParams();for(let k of ['site','voltage','pf','tariff','limit'])p.set(k,$(k).value);p.set('monitoring','1');document.querySelectorAll('#checks input:checked').forEach(x=>p.append('loads',x.value));return p}
function renderChart(vals){let w=640,h=200,L=33,R=8,T=10,B=24,max=Math.max(1,...vals)*1.18,points=vals.map((v,i)=>[L+i*(w-L-R)/23,T+(h-T-B)*(1-v/max)]),path=points.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' '),area=path+` L${points[23][0]},${h-B} L${L},${h-B} Z`,ys=[0,.5,1].map(f=>T+(h-T-B)*f);$('chart').innerHTML=`<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><defs><linearGradient id="fade" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#6bb791" stop-opacity=".26"/><stop offset="1" stop-color="#6bb791" stop-opacity="0"/></linearGradient></defs>${ys.map(y=>`<line class="gridline" x1="${L}" y1="${y}" x2="${w-R}" y2="${y}"/>`).join('')}<path class="chartfill" d="${area}"/><path class="chartline" d="${path}"/>${[0,6,12,18,23].map((v)=>`<text class="axis" x="${points[v][0]}" y="${h-5}" text-anchor="middle">${String(v).padStart(2,'0')}:00</text>`).join('')}<text class="axis" x="0" y="${T+5}">${max.toFixed(0)}</text></svg>`}
function update(){let p=params();fetch('/api?'+p).then(r=>r.json()).then(d=>{data=d;$('active').textContent=d.active.toFixed(1);$('energy').textContent=d.energy_day.toFixed(1);$('cost').textContent=d.cost_day.toFixed(0);$('month').textContent=d.cost_month.toLocaleString('en-IN',{maximumFractionDigits:0});$('carbon').textContent=d.carbon_day.toFixed(1);$('vread').textContent=d.voltage.toFixed(0);$('iread').textContent=d.current.toFixed(1);$('pfread').textContent=d.pf.toFixed(2);$('qread').textContent=d.reactive.toFixed(2);$('sread').textContent=d.apparent.toFixed(2);$('vbar').style.width=Math.min(100,d.voltage/2.55)+'%';$('ibar').style.width=Math.min(100,d.current/2)+'%';$('pfbar').style.width=(d.pf*100)+'%';$('qbar').style.width=Math.min(100,d.reactive*5)+'%';$('sbar').style.width=Math.min(100,d.apparent*3)+'%';$('sitepill').textContent=d.site;renderChart(d.profile);$('clock').textContent='Updated '+d.updated;$('loadlist').innerHTML=d.loads.length?d.loads.map(x=>`<div class="loadrow"><span class="loadname">${x.name}</span><div class="barbg"><div class="bar" style="width:${Math.min(100,x.kw/Math.max(d.active,.1)*100)}%"></div></div><span class="kw">${x.kw.toFixed(2)} kW</span></div>`).join(''):'<div class="desc">Select one or more loads to monitor.</div>';$('alerts').innerHTML=d.alerts.map(a=>`<div class="alert ${a.type}"><span>${a.type==='critical'?'●':a.type==='warning'?'▲':a.type==='good'?'✓':'◆'}</span><span>${a.text}</span></div>`).join('');renderDetailTables(d)})}
function syncChecks(){let site=$('site').value, options={Residential:['HVAC','Water heater','Refrigerator','Lighting','Kitchen','Washer','Standby loads'],Commercial:['HVAC plant','Lighting','IT equipment','Ventilation','Kitchen','Standby loads'],Industrial:['Production motors','Compressor','Process heating','HVAC','Lighting','Standby loads']}[site];let previous=new Set([...document.querySelectorAll('#checks input:checked')].map(x=>x.value));$('checks').innerHTML=options.map((n,i)=>`<label><input type="checkbox" value="${n}" ${previous.size?(previous.has(n)?'checked':''):(i<options.length?'checked':'')}> ${n}</label>`).join('');$('siteval').textContent=site;update()}
function selectAll(v){document.querySelectorAll('#checks input').forEach(x=>x.checked=v);update()}
function downloadReport(){if(!data)return;let report={title:'Smart IoT Energy Audit - Demonstration',generated_at:new Date().toISOString(),notice:'Synthetic estimates; not field measurements or certified audit results.',parameters:{facility:data.site,voltage_v:data.voltage,power_factor:data.pf,tariff_per_kwh:data.tariff,demand_threshold_kw:data.limit},summary:{active_demand_kw:data.active,estimated_energy_kwh_day:data.energy_day,estimated_cost_day:data.cost_day,estimated_cost_30_days:data.cost_month,estimated_carbon_kg_day:data.carbon_day,reactive_power_kvar:data.reactive,apparent_power_kva:data.apparent},monitored_loads:data.loads,alerts:data.alerts,daily_profile_kw:data.profile};let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));a.download='smart-energy-audit.json';a.click();URL.revokeObjectURL(a.href)}
function renderDetailTables(d) {
  let energyTotal = 0, costTotal = 0;
  $('loadtable').innerHTML = d.loads.map(x => {
    const energy = x.kw * 24 * .66, cost = energy * d.tariff;
    energyTotal += energy; costTotal += cost;
    return `<tr><td><strong>${x.name}</strong></td><td><span class="tagpill">${x.category}</span></td><td class="num">${x.kw.toFixed(2)} kW</td><td class="num">${energy.toFixed(1)} kWh</td><td class="num">₹${cost.toFixed(0)}</td><td class="num">${d.active ? (x.kw / d.active * 100).toFixed(1) : '0.0'}%</td></tr>`;
  }).join('') || '<tr><td colspan="6">No loads selected. Go to System settings to choose loads.</td></tr>';
  $('loadtotal').innerHTML = `<tr><th colspan="2">Selected load total</th><th class="num">${d.active.toFixed(2)} kW</th><th class="num">${energyTotal.toFixed(1)} kWh</th><th class="num">₹${costTotal.toFixed(0)}</th><th class="num">100%</th></tr>`;
  $('loadkpis').innerHTML = `<div class="audit-kpi"><span>Facility</span><strong>${d.site}</strong></div><div class="audit-kpi"><span>Selected demand</span><strong>${d.active.toFixed(1)} kW</strong></div><div class="audit-kpi"><span>Estimated energy</span><strong>${d.energy_day.toFixed(1)} kWh/day</strong></div><div class="audit-kpi"><span>Estimated cost</span><strong>₹${d.cost_day.toFixed(0)}/day</strong></div>`;

  $('audit-site').textContent = d.site;
  $('audit-date').textContent = new Date().toLocaleString();
  const demandText = d.active > d.limit ? `Demand is above your ${d.limit.toFixed(1)} kW alert threshold.` : 'Demand is within your selected threshold.';
  const pfText = d.pf < .85 ? 'Power factor is low; review reactive loads.' : 'Power factor is in a reasonable range for this demonstration.';
  $('audit-summary').innerHTML = `<strong>In plain language:</strong> The selected ${d.site.toLowerCase()} loads use an estimated <strong>${d.energy_day.toFixed(1)} kWh per day</strong>, costing about <strong>₹${d.cost_day.toFixed(0)} per day</strong> at the chosen tariff. ${demandText} ${pfText}`;
  $('audit-kpis').innerHTML = `<div class="audit-kpi"><span>Current demand</span><strong>${d.active.toFixed(1)} kW</strong></div><div class="audit-kpi"><span>Estimated monthly cost</span><strong>₹${Math.round(d.cost_month).toLocaleString('en-IN')}</strong></div><div class="audit-kpi"><span>Estimated carbon</span><strong>${d.carbon_day.toFixed(1)} kg/day</strong></div><div class="audit-kpi"><span>Power quality</span><strong>PF ${d.pf.toFixed(2)}</strong></div>`;

  const recommendations = [];
  const standbyLoads = d.loads.filter(x => x.category === 'Standby');
  const standbyKw = standbyLoads.reduce((sum, x) => sum + x.kw, 0);
  if (d.active > d.limit) recommendations.push(['High', 'Demand exceeds alert threshold', 'Stagger large loads or review equipment start times.', 'May reduce peak demand; compare meter readings.']);
  if (d.pf < .85) recommendations.push(['Medium', 'Power factor is below 0.85', 'Ask an electrician to review reactive loads and correction options.', 'Can reduce reactive demand where applicable.']);
  if (standbyKw > 0) recommendations.push(['Medium', 'Continuous standby load detected', `Check whether ${standbyLoads.map(x => x.name).join(', ')} can be switched off outside operating hours.`, `This simulated standby load uses about ${(standbyKw * 24).toFixed(1)} kWh/day.`]);
  const largest = [...d.loads].sort((a, b) => b.kw - a.kw)[0];
  if (largest) recommendations.push(['Review', `${largest.name} is the largest selected load`, 'Check its operating schedule, setpoints, and maintenance condition.', 'Track before and after demand to confirm any change.']);
  if (!recommendations.length) recommendations.push(['Good', 'No immediate threshold issue detected', 'Keep monitoring demand and compare similar operating days.', 'Helps identify changes and unusual use.']);
  $('recommendations').innerHTML = recommendations.map(r => `<tr><td><span class="tagpill">${r[0]}</span></td><td><strong>${r[1]}</strong></td><td>${r[2]}</td><td>${r[3]}</td></tr>`).join('');
  $('audit-conditions').innerHTML = `<tr><th>Facility profile</th><td>${d.site}</td><th>Supply voltage</th><td>${d.voltage.toFixed(0)} V</td></tr><tr><th>Power factor input</th><td>${d.pf.toFixed(2)}</td><th>Tariff</th><td>₹${d.tariff.toFixed(2)} / kWh</td></tr><tr><th>Demand threshold</th><td>${d.limit.toFixed(1)} kW</td><th>Loads monitored</th><td>${d.loads.length}</td></tr>`;
}
function navigate(page) {
  document.querySelectorAll('.nav[data-page]').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  const overview = page === 'overview';
  $('metrics').classList.toggle('hidden', !overview);
  document.querySelector('.telemetry').classList.toggle('hidden', !overview);
  document.querySelector('.monitoring').classList.toggle('hidden', !overview);
  $('controls').classList.toggle('hidden', page !== 'settings' && !overview);
  document.querySelector('.main>.footnote').classList.toggle('hidden', !overview);
  $('loadpage').classList.toggle('hidden', page !== 'loads');
  $('auditpage').classList.toggle('hidden', page !== 'audit');
  $('settingspage').classList.toggle('hidden', page !== 'settings');
  const titles = {overview:['ENERGY MANAGEMENT / OVERVIEW','Energy audit dashboard','Monitor demand, explore load patterns, and find savings opportunities.'],loads:['ENERGY MANAGEMENT / LOADS','Load breakdown','Review estimated demand, daily energy use, cost, and share by selected load.'],audit:['ENERGY MANAGEMENT / AUDIT','Energy audit insights','A clear summary of current conditions and practical next steps.'],settings:['ENERGY MANAGEMENT / SETTINGS','System settings','Choose the facility and operating conditions used in this simulation.']};
  $('eyebrow').textContent = titles[page][0]; $('pagetitle').textContent = titles[page][1]; $('pagesub').textContent = titles[page][2];
}
document.querySelectorAll('.nav[data-page]').forEach(n => n.addEventListener('click', () => navigate(n.dataset.page)));
['voltage','pf','tariff','limit'].forEach(id=>$(id).addEventListener('input',()=>{$(id+'val').textContent=$(id).value;update()}));$('site').addEventListener('change',syncChecks);$('checks').addEventListener('change',update);syncChecks();setInterval(update,3000);
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api":
            try: body = json.dumps(get_data(parse_qs(parsed.query))).encode()
            except (ValueError, TypeError): body = b'{"error":"invalid parameter"}'
            self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(body)
        else:
            body = HTML.encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *_): pass

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    print(f"Smart Energy Audit running on {host}:{PORT}")
    ThreadingHTTPServer((host, PORT), Handler).serve_forever()
