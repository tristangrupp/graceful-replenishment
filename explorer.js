const D = window.GRACE;
const MONTHS = D.months;
const NM = MONTHS.length;
const CLIP = 30;
const state = { product: "t", level: "03", sel: [], dropUnresolved: false };
const SERIES = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6"];

const RAMP_LIGHT = ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"];
const RAMP_DARK = ["#a8501f", "#cf7434", "#d99a5f", "#3a4442", "#6fa6cc", "#3987e5", "#1a5fb4"];

function isDark() {
  const stamped = document.documentElement.getAttribute("data-theme");
  if (stamped === "dark") return true;
  if (stamped === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function ramp() { return isDark() ? RAMP_DARK : RAMP_LIGHT; }

function mix(a, b, t) {
  const pa = [1, 3, 5].map(i => parseInt(a.substr(i, 2), 16));
  const pb = [1, 3, 5].map(i => parseInt(b.substr(i, 2), 16));
  return "rgb(" + pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(",") + ")";
}
function colorFor(v) {
  const r = ramp();
  const x = Math.max(-CLIP, Math.min(CLIP, v));
  const u = (x + CLIP) / (2 * CLIP) * (r.length - 1);
  const i = Math.min(r.length - 2, Math.floor(u));
  return mix(r[i], r[i + 1], u - i);
}

const cur = () => D.levels[state.level];
const trendKey = () => (state.product === "t" ? "tt" : "gt");
const pKey = () => (state.product === "t" ? "tp" : "gp");
const serKey = () => (state.product === "t" ? "t" : "g");
const fmt = n => (n > 0 ? "+" : "") + n.toFixed(2);
const label = b => b.region + " " + b.id;
const place = b => Math.abs(b.lat).toFixed(1) + (b.lat >= 0 ? "N " : "S ") +
  Math.abs(b.lon).toFixed(1) + (b.lon >= 0 ? "E" : "W");

/* ---------------------------------------------------------------- the map */
const mapEl = document.getElementById("map");

function buildMap() {
  const L = cur();
  let fills = "", hatch = "";
  L.basins.forEach((b, i) => {
    fills += '<path class="basin" data-i="' + i + '" d="' + b.d + '"></path>';
    hatch += '<path class="hatch" data-i="' + i + '" d="' + b.d + '" fill="url(#hx)"></path>';
  });
  const hatchInk = getComputedStyle(document.body).getPropertyValue("--hatch").trim();
  mapEl.setAttribute("viewBox", "0 0 " + D.width + " " + D.height);
  mapEl.innerHTML =
    '<defs><pattern id="hx" width="34" height="34" patternUnits="userSpaceOnUse" ' +
    'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="34" stroke="' + hatchInk +
    '" stroke-width="8" opacity="0.55"></line></pattern></defs>' +
    '<g id="fills">' + fills + '</g><g id="hatches">' + hatch + '</g>';
  paint();
}

function paint() {
  const L = cur(), tk = trendKey(), pk = pKey();
  const fills = mapEl.querySelectorAll("#fills path");
  const hats = mapEl.querySelectorAll("#hatches path");
  L.basins.forEach((b, i) => {
    const v = b[tk];
    const f = fills[i];
    const missing = v === null || v === undefined;
    const unresolved = missing || b[pk] >= 0.05;
    /* Dropped basins leave the map entirely, so what remains is only what the
       record resolves. Hatching says the same thing more quietly. */
    const drop = state.dropUnresolved && unresolved;
    f.classList.toggle("dropped", drop);
    f.style.fill = missing ? "var(--nodata)" : colorFor(v);
    const k = state.sel.indexOf(b.id);
    f.classList.toggle("sel", k >= 0);
    f.style.stroke = k >= 0 ? "var(" + SERIES[k] + ")" : "";
    hats[i].style.display = (!drop && !missing && b[pk] >= 0.05) ? "" : "none";
  });
  document.getElementById("ramp").style.background =
    "linear-gradient(90deg," + ramp().join(",") + ")";
  document.getElementById("sw-hatch").style.background =
    "repeating-linear-gradient(45deg,transparent 0 3px,var(--hatch) 3px 4px)";
  const withVal = L.basins.filter(b => b[tk] !== null && b[tk] !== undefined);
  const sig = withVal.filter(b => b[pk] < 0.05).length;
  document.getElementById("map-title").textContent =
    state.product === "t" ? "Total water storage trend" : "Groundwater estimate trend";
  document.getElementById("map-sub").textContent = state.dropUnresolved
    ? sig + " basins shown, the rest dropped"
    : withVal.length + " basins mapped, " + sig + " separable from zero";
  document.getElementById("movers-sub").textContent =
    (state.product === "t" ? "total water storage" : "groundwater estimate") +
    ", level " + Number(state.level);
}

/* ------------------------------------------------------------- the tooltip */
const tip = document.getElementById("tip");
function showTip(html, x, y) {
  tip.innerHTML = html;
  tip.style.opacity = "1";
  const r = tip.getBoundingClientRect();
  let left = x + 14, top = y + 14;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
  tip.style.left = Math.max(6, left) + "px";
  tip.style.top = Math.max(6, top) + "px";
}
const hideTip = () => { tip.style.opacity = "0"; };

mapEl.addEventListener("pointermove", e => {
  const p = e.target.closest(".basin");
  if (!p) { hideTip(); return; }
  const b = cur().basins[+p.dataset.i];
  const v = b[trendKey()], pv = b[pKey()];
  const missing = v === null || v === undefined;
  const body = missing
    ? '<span class="r">withheld from this layer</span>'
    : '<span class="r">' + fmt(v) + " mm/yr" +
      (pv >= 0.05 ? ", not separable from zero" : ", p = " + pv.toFixed(3)) + "</span>";
  showTip("<b>" + label(b) + "</b>" + body +
    '<span class="r">' + place(b) + ", " + b.area.toLocaleString() + " km2, " +
    b.nm + " mascons</span>", e.clientX, e.clientY);
});
mapEl.addEventListener("pointerleave", hideTip);
mapEl.addEventListener("click", e => {
  const p = e.target.closest(".basin");
  if (!p) return;
  toggle(cur().basins[+p.dataset.i].id);
});

function toggle(id) {
  const k = state.sel.indexOf(id);
  if (k >= 0) state.sel.splice(k, 1);
  else if (state.sel.length < 6) state.sel.push(id);
  else { flashHint("Six basins is the limit. Remove one first."); return; }
  render();
}
let hintTimer = null;
function flashHint(msg) {
  const h = document.getElementById("hint");
  h.textContent = msg;
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => { h.textContent = ""; }, 2600);
}

/* ------------------------------------------------------------- the chart */
const chartEl = document.getElementById("chart");
const CW = 720, CH = 300, PL = 46, PR = 16, PT = 14, PB = 26;
let chartGeom = null;

function niceStep(span) {
  const raw = span / 5;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag;
}

function drawChart() {
  const L = cur(), sk = serKey();
  const picked = state.sel.map(id => L.basins.find(b => b.id === id)).filter(Boolean);
  const globalSer = state.product === "t" ? L.global_t : L.global_g;

  const all = [];
  picked.forEach(b => (b[sk] || []).forEach(v => { if (v !== null) all.push(v / 10); }));
  globalSer.forEach(v => { if (v !== null) all.push(v / 10); });
  if (!all.length) all.push(-10, 10);
  let lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
  const padv = Math.max((hi - lo) * 0.12, 4);
  lo -= padv; hi += padv;
  const step = niceStep(hi - lo);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;

  const X = i => PL + (i / (NM - 1)) * (CW - PL - PR);
  const Y = v => PT + (1 - (v - lo) / (hi - lo)) * (CH - PT - PB);
  chartGeom = { X, Y, picked, globalSer, sk };

  let s = "";
  for (let v = lo; v <= hi + 1e-9; v += step) {
    const y = Y(v).toFixed(1);
    s += '<line class="' + (Math.abs(v) < 1e-9 ? "zero" : "gridline") +
      '" x1="' + PL + '" y1="' + y + '" x2="' + (CW - PR) + '" y2="' + y + '"></line>';
    s += '<text x="' + (PL - 7) + '" y="' + (Y(v) + 3.4).toFixed(1) + '" text-anchor="end">' +
      (v > 0 ? "+" : "") + Math.round(v) + "</text>";
  }
  MONTHS.forEach((m, i) => {
    if (m.slice(5) !== "01") return;
    s += '<text x="' + X(i).toFixed(1) + '" y="' + (CH - 8) + '" text-anchor="middle">' +
      m.slice(0, 4) + "</text>";
  });
  s += '<text x="' + (PL - 7) + '" y="' + (PT + 2) + '" text-anchor="end">mm</text>';

  const pathOf = arr => {
    let d = "", pen = false;
    arr.forEach((v, i) => {
      if (v === null) { pen = false; return; }
      d += (pen ? "L" : "M") + X(i).toFixed(1) + " " + Y(v / 10).toFixed(1);
      pen = true;
    });
    return d;
  };

  s += '<path class="globe" d="' + pathOf(globalSer) + '"></path>';

  picked.forEach(b => {
    const arr = b[sk];
    if (!arr) return;
    const col = "var(" + SERIES[state.sel.indexOf(b.id)] + ")";
    s += '<path class="ser" style="stroke:' + col + '" d="' + pathOf(arr) + '"></path>';
    /* The reported rate, drawn through the record mean at the record midpoint,
       so the line on the chart is the fitted harmonic model rather than a fresh
       regression that would disagree with the number in the table. */
    const vals = arr.filter(v => v !== null).map(v => v / 10);
    const mean = vals.reduce((a, c) => a + c, 0) / vals.length;
    const slope = b[trendKey()];
    if (slope !== null && slope !== undefined) {
      const half = ((NM - 1) / 12) / 2;
      s += '<path class="trend" style="stroke:' + col + '" d="M' + X(0).toFixed(1) + " " +
        Y(mean - slope * half).toFixed(1) + "L" + X(NM - 1).toFixed(1) + " " +
        Y(mean + slope * half).toFixed(1) + '"></path>';
    }
    let last = -1;
    arr.forEach((v, i) => { if (v !== null) last = i; });
    if (last >= 0) {
      s += '<circle cx="' + X(last).toFixed(1) + '" cy="' + Y(arr[last] / 10).toFixed(1) +
        '" r="3" style="fill:' + col + '"></circle>';
    }
  });

  s += '<line id="cross" class="cross" y1="' + PT + '" y2="' + (CH - PB) +
    '" x1="0" x2="0" style="display:none"></line>';
  chartEl.setAttribute("viewBox", "0 0 " + CW + " " + CH);
  chartEl.innerHTML = s;

  document.getElementById("chart-sub").textContent = picked.length
    ? picked.length + " selected. Dashed line is the fitted rate, dotted is the global land mean."
    : "Click a basin on the map to put its record here.";
  document.getElementById("clear").disabled = state.sel.length === 0;
}

chartEl.addEventListener("pointermove", e => {
  if (!chartGeom) return;
  const r = chartEl.getBoundingClientRect();
  const px = ((e.clientX - r.left) / r.width) * CW;
  const i = Math.round(((px - PL) / (CW - PL - PR)) * (NM - 1));
  if (i < 0 || i >= NM) { hideTip(); return; }
  const line = document.getElementById("cross");
  if (line) {
    line.setAttribute("x1", chartGeom.X(i));
    line.setAttribute("x2", chartGeom.X(i));
    line.style.display = "";
  }
  let html = "<b>" + MONTHS[i] + "</b>";
  chartGeom.picked.forEach(b => {
    const v = (b[chartGeom.sk] || [])[i];
    html += '<span class="r">' + label(b) + ": " +
      (v === null || v === undefined ? "no solution" : fmt(v / 10) + " mm") + "</span>";
  });
  const g = chartGeom.globalSer[i];
  html += '<span class="r">global land mean: ' + (g === null ? "no solution" : fmt(g / 10) + " mm") + "</span>";
  showTip(html, e.clientX, e.clientY);
});
chartEl.addEventListener("pointerleave", () => {
  hideTip();
  const line = document.getElementById("cross");
  if (line) line.style.display = "none";
});

/* -------------------------------------------------------------- the table */
function drawRows() {
  const L = cur(), tk = trendKey(), pk = pKey();
  const tb = document.getElementById("rows");
  if (!state.sel.length) {
    tb.innerHTML = '<tr><td colspan="5" class="ns" style="text-align:left;font-family:inherit">' +
      "Nothing selected. Pick a basin on the map, or from the extremes below.</td></tr>";
    return;
  }
  tb.innerHTML = state.sel.map((id, k) => {
    const b = L.basins.find(x => x.id === id);
    if (!b) return "";
    const v = b[tk], p = b[pk];
    const vs = (v === null || v === undefined) ? '<span class="ns">withheld</span>' : fmt(v);
    const ps = (p === null || p === undefined) ? '<span class="ns">n/a</span>'
      : (p < 0.05 ? p.toFixed(3) : '<span class="ns">' + p.toFixed(2) + "</span>");
    return '<tr><td class="name"><span class="dot" style="background:var(' + SERIES[k] + ')"></span>' +
      label(b) + '<button class="rm" data-id="' + id + '" aria-label="Remove basin">x</button></td>' +
      "<td>" + vs + "</td><td>" + ps + "</td><td>" + b.nm + "</td><td>" +
      Math.round(b.area / 1000) + "k</td></tr>";
  }).join("");
  tb.querySelectorAll(".rm").forEach(btn =>
    btn.addEventListener("click", () => toggle(+btn.dataset.id)));
}

/* ------------------------------------------------------------ the extremes */
function drawMovers() {
  const L = cur(), tk = trendKey();
  const vals = L.basins.filter(b => b[tk] !== null && b[tk] !== undefined && b.nm >= 4);
  const sorted = vals.slice().sort((a, c) => a[tk] - c[tk]);
  if (!sorted.length) return;
  const max = Math.max(Math.abs(sorted[0][tk]), Math.abs(sorted[sorted.length - 1][tk]));
  const row = b => {
    const v = b[tk], pct = Math.min(100, Math.abs(v) / max * 100);
    return '<li data-id="' + b.id + '" tabindex="0"><span class="lbl">' + label(b) +
      '</span><span class="val">' + fmt(v) + '</span>' +
      '<span class="track"><span class="fill" style="width:' + pct.toFixed(1) +
      "%;background:" + colorFor(v) + '"></span></span></li>';
  };
  document.getElementById("mv-loss").innerHTML = sorted.slice(0, 8).map(row).join("");
  document.getElementById("mv-gain").innerHTML = sorted.slice(-8).reverse().map(row).join("");
  document.querySelectorAll(".mv li").forEach(li => {
    const go = () => toggle(+li.dataset.id);
    li.addEventListener("click", go);
    li.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  });
}

/* ------------------------------------------------------------------ wiring */
function render() { paint(); drawChart(); drawRows(); drawMovers(); }

document.getElementById("seg-product").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  state.product = b.dataset.v;
  Array.from(e.currentTarget.children).forEach(x =>
    x.setAttribute("aria-pressed", String(x === b)));
  render();
});
document.getElementById("seg-level").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  state.level = b.dataset.v;
  Array.from(e.currentTarget.children).forEach(x =>
    x.setAttribute("aria-pressed", String(x === b)));
  state.sel = [];
  buildMap();
  defaults();
  render();
});
document.getElementById("clear").addEventListener("click", () => {
  state.sel = [];
  render();
});
const dropBtn = document.getElementById("drop");
dropBtn.addEventListener("click", () => {
  state.dropUnresolved = !state.dropUnresolved;
  dropBtn.setAttribute("aria-pressed", String(state.dropUnresolved));
  dropBtn.textContent = state.dropUnresolved ? "Show all basins" : "Drop unresolved";
  paint();
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  buildMap();
  render();
});

/* Opens in a working state rather than an empty shell: the sharpest loss and the
   sharpest gain among basins with enough mascons to mean something, plus one
   whose rate the test cannot separate from zero, so the hatching has an example. */
function defaults() {
  const L = cur();
  const solid = L.basins.filter(b => b.nm >= 20 && b.tt !== null && b.tt !== undefined);
  const byTrend = solid.slice().sort((a, c) => a.tt - c.tt);
  const flat = solid.filter(b => b.tp >= 0.05).sort((a, c) => Math.abs(a.tt) - Math.abs(c.tt));
  const picks = [byTrend[0], byTrend[byTrend.length - 1], flat[0]].filter(Boolean);
  state.sel = picks.map(b => b.id).slice(0, 3);
}

document.getElementById("w-window").textContent = MONTHS[0] + " to " + MONTHS[NM - 1];
buildMap();
defaults();
render();
