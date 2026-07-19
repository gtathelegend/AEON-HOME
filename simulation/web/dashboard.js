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

/* The automation switch sends the state it wants, not a "toggle" -- two
   dashboards open at once would otherwise race each other into the wrong one. */
let automationOn = true;
$("btn-auto").addEventListener("click", () =>
  send({ typ: "set_automation", on: !automationOn }));

/* ── render ──────────────────────────────────────────────────── */

function render(s) {
  $("clock").textContent = s.clock;
  $("clock-day").textContent = s.clock_day;

  $("node-dot").className = "dot " + (s.node.online ? "on live" : "offline");
  $("node-text").textContent = s.node.online ? "online" : "offline";

  // Whether a handset is actually attached. Worth knowing BEFORE speaking into
  // it: a phone that silently failed to connect looks identical to a phone
  // whose command was ignored.
  const phones = s.node.phones || 0;
  $("phone-dot").className = "dot " + (phones ? "on live" : "off");
  $("phone-text").textContent = phones
    ? (phones === 1 ? "connected" : `${phones} connected`)
    : "not connected";
  $("hdr-temp").textContent = s.ambient.temp_c.toFixed(1) + "°C";
  $("hdr-occ").textContent = s.ambient.occupied ? "present" : "empty";

  renderAutomation(s.node.automation !== false);
  renderDevices(s.devices);
  renderModel(s);
  renderCandidate(s.candidate);
  renderAIHub(s.aihub, s.candidate);
  renderLearned(s.learned_week);
  renderLog(s.log);
}

function renderAutomation(on) {
  automationOn = on;
  const state = $("auto-state");
  state.textContent = on ? "AUTOMATION ON" : "AUTOMATION OFF";
  state.dataset.on = String(on);
  $("auto-note").textContent = on
    ? "the model may act on what it has learned"
    : "manual only — the house does what you tell it, nothing else";
  $("btn-auto").textContent = on ? "Disable automation" : "Enable automation";
  $("btn-auto").dataset.armed = String(!on);
  document.body.dataset.automation = String(on);
}

/* Retrain produces a verdict; Redeploy acts on it. The button stays disabled
   until a candidate exists AND beat the incumbent, so "deploy something worse"
   is not a thing the screen will let you do. */
function renderCandidate(c) {
  if (!c || !c.trained_at) { $("cand").style.display = "none"; return; }
  $("cand").style.display = "block";

  const verdict = $("cand-verdict");
  verdict.textContent = c.better ? "BETTER — ready to deploy" : "NOT BETTER";
  verdict.dataset.better = String(!!c.better);
  verdict.title = c.reason || "";

  const was = c.incumbent_auc === null || c.incumbent_auc === undefined
    ? "none" : c.incumbent_auc.toFixed(3);
  $("cand-auc").textContent =
    c.cv_auc === null || c.cv_auc === undefined
      ? `-- (live ${was})`
      : `${c.cv_auc.toFixed(3)}  ·  live ${was}`;

  $("cand-windows").textContent = c.n_windows
    ? `${c.n_windows.toLocaleString()} (${c.stated_windows.toLocaleString()} stated + ${c.observed_windows.toLocaleString()} observed)`
    : "--";
  $("cand-observed").textContent = c.observed_hours
    ? `${c.observed_hours.toLocaleString()} h recorded`
    : "none yet";
  $("cand-secs").textContent = c.train_seconds ? `${c.train_seconds.toFixed(2)} s` : "--";

  // Per-device error, with the live model's number beside it. This is where
  // "better" is actually visible -- AUC saturates at 1.000 and stops moving.
  const host = $("cand-mae");
  host.innerHTML = "";
  Object.entries(c.level_mae || {}).forEach(([id, m]) => {
    const better = m.was !== null && m.was !== undefined && m.value < m.was;
    const worse = m.was !== null && m.was !== undefined && m.value > m.was;
    const arrow = better ? "▼" : worse ? "▲" : "";
    const was = m.was_text ? ` <span class="was">was ${esc(m.was_text)}</span>` : "";
    host.insertAdjacentHTML("beforeend",
      `<li data-dir="${better ? "down" : worse ? "up" : ""}">
         <span class="who">${esc(id)}</span>
         <span class="what">${arrow} ${esc(m.text)}${was}</span>
       </li>`);
  });

  $("btn-deploy").disabled = !c.better;
}

function renderAIHub(a, c) {
  if (!a || a.state === "idle") { $("hub").style.display = "none"; return; }
  $("hub").style.display = "block";

  const label = {
    running: "compiling + profiling on Snapdragon…",
    done: "measured on real silicon",
    failed: "job failed",
    unavailable: "not configured",
  }[a.state] || a.state;

  const st = $("hub-state");
  st.textContent = a.device ? `${label} · ${a.device}` : label;
  st.dataset.state = a.state;
  st.title = a.reason || "";

  $("hub-us").textContent = a.inference_us === null || a.inference_us === undefined
    ? (a.state === "running" ? "…" : "--")
    : `${a.inference_us.toFixed(0)} µs${a.compute_unit ? " · " + esc(a.compute_unit) : ""}`;
  $("hub-local").textContent = a.local_us ? `${a.local_us.toFixed(1)} µs · CPU` : "12.4 µs · CPU";
  $("hub-mem").textContent = a.peak_memory_mb ? `${a.peak_memory_mb.toFixed(1)} MB` : "--";
  $("hub-cjob").textContent = a.compile_job || "--";
  $("hub-pjob").textContent = a.profile_job || "--";
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

    // Three decimals: the model genuinely moves in the third one, and a
    // confidence pinned at "1.00" every tick looks printed on rather than
    // computed. Two decimals were hiding a live number.
    // "held" means the model decided and was not allowed to act. Saying `model`
    // while automation is off would credit it with something it did not do.
    const verdict = d.gate === "held"
      ? `held · ${d.confidence.toFixed(3)}`
      : `${esc(d.source)} · ${d.confidence.toFixed(3)}`;
    el.querySelector(".foot").innerHTML = !d.online
      ? `<span class="link off">leaf offline</span>`
      : `<span class="link">connected</span> · ${verdict}`;
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
