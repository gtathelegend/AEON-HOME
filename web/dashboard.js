/* ÆON Home — PC dashboard.
   Renders whatever HubState.snapshot() sends. It never computes state itself,
   so the phone and this screen cannot drift apart.

   Deliberately shows less than the hub knows. In a five-minute demo a number
   nobody reads is a number in the way -- the three appliances, the fan-out
   proof and the model version are what earn the points. */

const $ = (id) => document.getElementById(id);

let socket = null;
let retries = 0;

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws`);

  socket.onopen = () => { retries = 0; };

  socket.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.typ === "state") render(msg);
  };

  socket.onclose = () => {
    $("node-text").textContent = "offline";
    $("node-dot").className = "dot offline";
    retries += 1;
    setTimeout(connect, Math.min(500 * retries, 4000));
  };
}

function send(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

document.querySelectorAll("[data-send]").forEach((btn) => {
  btn.addEventListener("click", () => send(JSON.parse(btn.dataset.send)));
});

/* ── render ──────────────────────────────────────────────────── */

function render(s) {
  $("clock").textContent = s.clock;
  $("clock-day").textContent = s.clock_day;

  $("node-dot").className = "dot " + (s.node.online ? "on live" : "offline");
  $("node-text").textContent = s.node.online ? "online" : "offline";
  $("hdr-temp").textContent = s.ambient.temp_c.toFixed(1) + "°C";
  $("hdr-occ").textContent = s.ambient.occupied ? "present" : "empty";

  renderDevices(s.devices);
  renderModel(s);
  renderLearned(s.learned_week);
  renderLog(s.log);
}

function renderDevices(devices) {
  const host = $("devices");
  devices.forEach((d) => {
    let el = host.querySelector(`[data-id="${d.id}"]`);
    if (!el) {
      el = document.createElement("div");
      el.className = "device";
      el.dataset.id = d.id;
      el.innerHTML = `
        <div class="name"><span class="dot"></span><span class="nm"></span></div>
        <div class="value">--</div>
        <div class="meter"><i style="width:0%"></i></div>
        <div class="foot"></div>`;
      host.appendChild(el);
    }

    el.dataset.on = String(d.on);
    el.dataset.online = String(d.online);

    el.querySelector(".dot").className =
      "dot " + (!d.online ? "offline" : d.on ? "on" : "off");
    el.querySelector(".nm").textContent = d.label;
    el.querySelector(".value").textContent = d.on ? d.level_text : "OFF";

    const pct = d.on && d.level !== null
      ? ((d.level - d.range[0]) / (d.range[1] - d.range[0])) * 100
      : 0;
    el.querySelector(".meter i").style.width = pct.toFixed(1) + "%";

    el.querySelector(".foot").textContent = !d.online
      ? "leaf offline"
      : `${d.source} · confidence ${d.confidence.toFixed(2)}`;
  });
}

function renderModel(s) {
  const p = s.policy;
  $("p-ver").textContent = p.model_v;
  $("p-auc").textContent = p.cv_auc === null ? "--" : p.cv_auc.toFixed(3);
  $("p-size").textContent = p.size_bytes
    ? `${p.size_bytes.toLocaleString()} B ${p.kind || ""}`.trim()
    : "--";
  $("p-cloud").textContent = s.egress.cloud_bytes;

  // Only present while it means something -- during the PC-offline demo.
  $("spool-row").style.display = s.egress.spooled ? "block" : "none";
  $("p-spool").textContent = s.egress.spooled;

  $("btn-pc").textContent = s.node.pc_reachable ? "Cut PC link" : "Restore PC link";
  $("btn-pc").dataset.armed = String(!s.node.pc_reachable);
}

function renderLearned(rows) {
  const host = $("learned");
  host.innerHTML = "";
  rows.forEach((r) => {
    host.insertAdjacentHTML("beforeend",
      `<li><span class="what">${esc(r.text)}</span><span class="who">${esc(r.label)}</span></li>`);
  });
}

function renderLog(rows) {
  const host = $("log");
  host.innerHTML = "";
  rows.forEach((e) => {
    host.insertAdjacentHTML("beforeend", `
      <div class="log-row" data-kind="${esc(e.kind)}">
        <span class="t">${hhmmss(e.ts)}</span>
        <span class="kind">${esc(e.kind)}</span>
        <span class="body">${logBody(e)}</span>
      </div>`);
  });
}

/* A hop that takes 8 microseconds renders as "0.00 ms", which reads as broken
   rather than fast -- and that line exists to show the speed. Drop to µs below
   a millisecond. */
function latency(ms) {
  if (ms >= 1) return `${ms.toFixed(2)} ms`;
  const us = ms * 1000;
  return us < 1 ? "<1 µs" : `${us.toFixed(0)} µs`;
}

function logBody(e) {
  if (e.kind === "fanout") {
    const leaf = e.leaf.status === "leaf_ack"
      ? `leaf <b>ack ${latency(e.leaf.ms)}</b>`
      : `leaf <b>offline</b>`;
    const pc = e.pc.status === "delivered"
      ? `pc <b>delivered ${latency(e.pc.ms)}</b>`
      : `pc <b>spooled</b> (queued ${e.pc.queued})`;
    const said = e.spoken ? `<span class="said">“${esc(e.spoken)}”</span>` : "";
    return `<b>${esc(e.label)}</b> &nbsp;<span class="hop">${leaf} · ${pc}</span>${said}`;
  }
  if (e.kind === "rejected") {
    return `<b>${esc(e.reason)}</b> — ${esc(e.text || "")} · device unchanged`;
  }
  if (e.text) return esc(e.text);
  return esc(JSON.stringify(e));
}

/* ── helpers ─────────────────────────────────────────────────── */

function hhmmss(ts) {
  return new Date(ts * 1000).toTimeString().slice(0, 8);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

connect();
