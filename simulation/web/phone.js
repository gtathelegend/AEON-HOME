/* ÆON Home — phone client.
   Personal view: proposals, one-tap answers, a mic. No raw numbers -- only what
   the hub constructs. Reads the same HubState as the PC dashboard, so the two
   screens cannot disagree.

   Phase 1 uses the browser's own SpeechRecognition for dictation. Phase 3 swaps
   in Sarvam Saarika (STT) and Bulbul (TTS) behind the same two functions. */

const $ = (id) => document.getElementById(id);

let socket = null;
let retries = 0;
let dragging = null;   // device id whose slider the thumb is currently on

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  // ?client=phone so the dashboard can report that a handset is attached.
  socket = new WebSocket(`${proto}://${location.host}/ws?client=phone`);

  socket.onopen = () => {
    retries = 0;
    $("link-dot").className = "dot on";
    $("link-text").textContent = "linked";
  };
  socket.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.typ === "state") render(msg);
  };
  socket.onclose = () => {
    $("link-dot").className = "dot offline";
    $("link-text").textContent = "reconnecting";
    retries += 1;
    setTimeout(connect, Math.min(500 * retries, 4000));
  };
}

function send(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

/* ── speech ──────────────────────────────────────────────────── */

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null;

if (SR) {
  recog = new SR();
  recog.lang = "en-IN";           // handles code-mixed Hindi/English reasonably
  recog.interimResults = true;
  recog.continuous = false;

  recog.onresult = (ev) => {
    const text = Array.from(ev.results).map((r) => r[0].transcript).join("");
    $("heard").innerHTML = `<b>${esc(text)}</b>`;
    if (ev.results[ev.results.length - 1].isFinal) speak(text);
  };
  recog.onend = () => $("mic").dataset.listening = "false";
  recog.onerror = () => {
    $("mic").dataset.listening = "false";
    $("heard").innerHTML = `<span class="dim">Mic unavailable — type it instead.</span>`;
  };
}

$("mic").addEventListener("click", () => {
  if (!recog) {
    $("heard").innerHTML = `<span class="dim">This browser has no speech API — type it instead.</span>`;
    $("say-text").focus();
    return;
  }
  if ($("mic").dataset.listening === "true") {
    recog.stop();
    return;
  }
  $("mic").dataset.listening = "true";
  $("heard").innerHTML = `<span class="dim">Listening…</span>`;
  try { recog.start(); } catch (_) { /* already started */ }
});

function speak(text) {
  if (!text.trim()) return;
  send({ typ: "speak", text: text.trim() });
  confirmAloud(text.trim());
}

/* Confirmation matters: the user needs to know what was understood before it
   reprograms their house. Phase 3 replaces this with Sarvam Bulbul. */
function confirmAloud(text) {
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(`Okay. ${text}`);
  u.lang = "en-IN";
  u.rate = 1.05;
  window.speechSynthesis.speak(u);
}

$("say-go").addEventListener("click", () => {
  speak($("say-text").value);
  $("say-text").value = "";
});
$("say-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("say-go").click();
});

/* ── render ──────────────────────────────────────────────────── */

function render(s) {
  $("st-model").textContent = "v" + s.policy.model_v;
  $("st-clock").textContent = s.clock;

  const host = $("tiles");
  s.devices.forEach((d) => {
    let el = host.querySelector(`[data-id="${d.id}"]`);
    if (!el) {
      el = document.createElement("div");
      el.className = "tile";
      el.dataset.id = d.id;
      el.innerHTML = `
        <div class="nm"><span class="dot"></span><span class="t"></span></div>
        <div class="val">--</div>
        <div class="ctl">
          <input type="range" class="lvl">
          <button class="pow">Off</button>
        </div>`;
      host.appendChild(el);
      wireTile(el, d);
    }

    el.dataset.on = String(d.on);
    el.dataset.online = String(d.online);
    el.querySelector(".dot").className =
      "dot " + (!d.online ? "offline" : d.on ? "on" : "off");
    el.querySelector(".t").textContent = d.label;
    el.querySelector(".val").textContent = d.on ? d.level_text : "OFF";

    const pow = el.querySelector(".pow");
    pow.dataset.on = String(d.on);
    pow.textContent = d.on ? "On" : "Off";

    // Don't fight the user's thumb while they are dragging.
    if (dragging !== d.id) {
      const slider = el.querySelector(".lvl");
      slider.min = d.range[0];
      slider.max = d.range[1];
      slider.step = d.unit === "K" ? 50 : 1;
      slider.value = d.level ?? d.range[0];
    }
  });

  renderAsks(s.devices);

  const learned = $("learned");
  learned.innerHTML = "";
  s.learned_week.forEach((r) => {
    learned.insertAdjacentHTML("beforeend",
      `<li><span class="what">${esc(r.text)}</span><span class="who">${esc(r.label)}</span></li>`);
  });
}

/* Suggestions the model was not confident enough to act on by itself.
   Keyed by what is being proposed, not just by device, so answering a
   question does not silently suppress a different one about the same
   appliance an hour later. */
const dismissed = new Set();

function askKey(d) {
  return `${d.id}:${d.want_on ? "on" : "off"}:${d.want_level ?? ""}`;
}

function asksFrom(devices) {
  return devices.filter((d) => {
    if (d.gate !== "ask" || !d.online) return false;
    // Nothing to ask if the appliance is already doing what the model wanted.
    if (d.want_on === d.on && d.want_level === d.level) return false;
    return !dismissed.has(askKey(d));
  });
}

function renderAsks(devices) {
  const host = $("asks");
  const wrap = $("asks-wrap");
  const asks = asksFrom(devices);

  wrap.hidden = asks.length === 0;
  host.innerHTML = "";

  asks.forEach((d) => {
    const what = d.want_on
      ? `turn ${esc(d.label)} on${d.want_text ? " at " + esc(d.want_text) : ""}`
      : `turn ${esc(d.label)} off`;
    const el = document.createElement("div");
    el.className = "ask";
    el.innerHTML = `
      <div class="q">You usually ${what} around now. Want it?</div>
      <div class="why">not sure enough to act · ${d.confidence.toFixed(3)}</div>
      <div class="row">
        <button class="yes">Yes</button>
        <button class="no">Not now</button>
      </div>`;

    el.querySelector(".yes").addEventListener("click", () => {
      send({ typ: "command", device: d.id, on: d.want_on, level: d.want_level,
             spoken: "approved a suggestion" });
      dismissed.add(askKey(d));
      renderAsks(devices);
    });
    el.querySelector(".no").addEventListener("click", () => {
      dismissed.add(askKey(d));
      renderAsks(devices);
    });

    host.appendChild(el);
  });
}

function wireTile(el, d) {
  const id = el.dataset.id;
  const slider = el.querySelector(".lvl");
  const pow = el.querySelector(".pow");

  slider.addEventListener("input", () => {
    dragging = id;
    el.querySelector(".val").textContent = fmt(d, Number(slider.value));
  });

  const commit = () => {
    if (dragging !== id) return;
    dragging = null;
    send({ typ: "command", device: id, on: true, level: Number(slider.value),
           spoken: `set ${d.label.toLowerCase()} to ${fmt(d, Number(slider.value))}` });
  };
  slider.addEventListener("change", commit);
  slider.addEventListener("pointerup", commit);

  pow.addEventListener("click", () => {
    const turningOn = pow.dataset.on !== "true";
    send({ typ: "command", device: id, on: turningOn,
           level: turningOn ? Number(slider.value) : null,
           spoken: `turn ${turningOn ? "on" : "off"} the ${d.label.toLowerCase()}` });
  });
}

function fmt(d, v) {
  if (d.unit === "K") return `${Math.round(v)}K`;
  if (d.unit === "%") return `${Math.round(v)}%`;
  return `${v.toFixed(1)}${d.unit}`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

connect();
