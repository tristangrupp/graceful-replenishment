const D = window.GRACE;
const MONTHS = D.months;
const NM = MONTHS.length;
const YEARS = Array.from(new Set(MONTHS.map(m => +m.slice(0, 4)))).sort((a, b) => a - b);
const MONTH_OF = MONTHS.map(m => +m.slice(5, 7));
const YEAR_OF = MONTHS.map(m => +m.slice(0, 4));
const MONTH_NAMES = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

const state = { product: "t", level: "03", mode: "level", year: YEARS[0], sel: null, playing: false };

const RAMP_LIGHT = ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"];
const RAMP_DARK = ["#a8501f", "#cf7434", "#d99a5f", "#3a4442", "#6fa6cc", "#3987e5", "#1a5fb4"];
/* Year is an ordered quantity, so the per-year lines take a single-hue
   sequential ramp, light for the earliest year to dark for the latest. */
const YEAR_RAMP_LIGHT = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281"];
const YEAR_RAMP_DARK = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#6da7ec", "#9ec5f4"];

function isDark() {
  const stamped = document.documentElement.getAttribute("data-theme");
  if (stamped === "dark") return true;
  if (stamped === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
const ramp = () => (isDark() ? RAMP_DARK : RAMP_LIGHT);
function yearColor(y) {
  const r = isDark() ? YEAR_RAMP_DARK : YEAR_RAMP_LIGHT;
  const i = YEARS.indexOf(y);
  return r[Math.round(i / Math.max(1, YEARS.length - 1) * (r.length - 1))];
}

function mix(a, b, t) {
  const pa = [1, 3, 5].map(i => parseInt(a.substr(i, 2), 16));
  const pb = [1, 3, 5].map(i => parseInt(b.substr(i, 2), 16));
  return "rgb(" + pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(",") + ")";
}
function colorFor(v, lim) {
  const r = ramp();
  const x = Math.max(-lim, Math.min(lim, v));
  const u = (x + lim) / (2 * lim) * (r.length - 1);
  const i = Math.min(r.length - 2, Math.floor(u));
  return mix(r[i], r[i + 1], u - i);
}

const cur = () => D.levels[state.level];
const serKey = () => (state.product === "t" ? "t" : "g");
const fmt = n => (n > 0 ? "+" : "") + n.toFixed(1);
const label = b => b.region + " " + b.id;

/* ------------------------------------------------- deseasonalise and fold
   Each month of the year gets its own mean over the record, and that mean is
   removed from every instance of that month. Everything on this page is built
   from the result, which is what lets a 7-month year sit beside a 12-month one
   without the comparison being an artefact of which months were solved. */
const cache = new Map();

function annual(b, sk) {
  const key = b.id + sk;
  if (cache.has(key)) return cache.get(key);
  const raw = b[sk];
  if (!raw) { cache.set(key, null); return null; }

  const cSum = new Array(13).fill(0), cN = new Array(13).fill(0);
  raw.forEach((v, i) => {
    if (v === null) return;
    cSum[MONTH_OF[i]] += v / 10;
    cN[MONTH_OF[i]] += 1;
  });
  const clim = cSum.map((s, m) => (cN[m] ? s / cN[m] : 0));

  const des = raw.map((v, i) => (v === null ? null : v / 10 - clim[MONTH_OF[i]]));

  const sum = {}, n = {};
  YEARS.forEach(y => { sum[y] = 0; n[y] = 0; });
  des.forEach((v, i) => {
    if (v === null) return;
    sum[YEAR_OF[i]] += v;
    n[YEAR_OF[i]] += 1;
  });
  const mean = {}, delta = {};
  YEARS.forEach((y, k) => {
    mean[y] = n[y] ? sum[y] / n[y] : null;
    const prev = YEARS[k - 1];
    delta[y] = (k > 0 && mean[y] !== null && mean[prev] !== null) ? mean[y] - mean[prev] : null;
  });
  const out = { des, clim, mean, delta, n };
  cache.set(key, out);
  return out;
}

const Y0 = YEARS[0], Y1 = YEARS[YEARS.length - 1];
const SPAN_YEARS = (NM - 1) / 12;

const endpointChange = a =>
  (a && a.mean[Y0] !== null && a.mean[Y1] !== null) ? a.mean[Y1] - a.mean[Y0] : null;

const valueFor = (b, sk, y) => {
  const a = annual(b, sk);
  if (!a) return null;
  if (state.mode === "endpoints") return endpointChange(a);
  return state.mode === "level" ? a.mean[y] : a.delta[y];
};

/* Colour limit from the data rather than a guess: the 95th percentile of the
   absolute values across every basin and every frame, rounded up to a round
   number so the ticks read cleanly. */
function limitFor() {
  const sk = serKey();
  const vals = [];
  const frames = state.mode === "endpoints" ? [Y1] : YEARS;
  /* Both levels feed the scale. Scaling each level to its own extremes would
     paint the same basin two different colours depending on which level was
     showing, which is the one comparison this page exists to support. */
  Object.keys(D.levels).forEach(k => {
    D.levels[k].basins.forEach(b => frames.forEach(y => {
      const v = valueFor(b, sk, y);
      if (v !== null && isFinite(v)) vals.push(Math.abs(v));
    }));
  });
  if (!vals.length) return 50;
  vals.sort((a, b) => a - b);
  const p95 = vals[Math.floor(vals.length * 0.95)];
  const steps = [10, 20, 25, 40, 50, 75, 100, 150, 200, 300, 400, 500];
  return steps.find(s => s >= p95) || 500;
}
let LIMIT = 50;

/* ---------------------------------------------------------------- the map */
const mapEl = document.getElementById("map");

function buildMap() {
  const L = cur();
  let fills = "";
  L.basins.forEach((b, i) => {
    fills += '<path class="basin" data-i="' + i + '" d="' + b.d + '"></path>';
  });
  mapEl.setAttribute("viewBox", "0 0 " + D.width + " " + D.height);
  mapEl.innerHTML = '<g id="fills">' + fills + "</g>";
}

function paint() {
  const L = cur(), sk = serKey();
  const fills = mapEl.querySelectorAll("#fills path");
  L.basins.forEach((b, i) => {
    const v = valueFor(b, sk, state.year);
    const f = fills[i];
    f.style.fill = (v === null) ? "var(--nodata)" : colorFor(v, LIMIT);
    const on = state.sel === b.id;
    f.classList.toggle("sel", on);
    f.style.stroke = on ? "var(--ink)" : "";
  });
  const fixed = state.mode === "endpoints";
  document.getElementById("stage-year").textContent = fixed ? Y0 + " to " + Y1 : state.year;
  document.getElementById("stage-note").textContent =
    fixed ? "first year to last"
          : (state.mode === "level" ? "annual level" : "change from " + (state.year - 1));
  const k = YEARS.indexOf(state.year);
  document.getElementById("rail-on").style.width =
    (fixed ? 100 : (k / (YEARS.length - 1) * 100)).toFixed(1) + "%";
  /* The map does not change with the year in this mode, so the transport is
     switched off rather than left running against a still frame. */
  document.getElementById("play").disabled = fixed;
  document.getElementById("rail-on").style.opacity = fixed ? "0.35" : "1";
  document.querySelectorAll(".yrbtn").forEach(btn =>
    btn.setAttribute("aria-pressed", String(+btn.dataset.y === state.year)));
  const withVal = L.basins.filter(b => valueFor(b, sk, state.year) !== null).length;
  document.getElementById("w-basins").textContent = withVal;
}

function paintScale() {
  LIMIT = limitFor();
  document.getElementById("ramp").style.background =
    "linear-gradient(90deg," + ramp().join(",") + ")";
  const t = document.getElementById("ramp-ticks");
  t.innerHTML = [-LIMIT, -LIMIT / 2, 0, LIMIT / 2, LIMIT]
    .map(v => "<span>" + (v > 0 ? "+" : "") + Math.round(v) + "</span>").join("");
  document.getElementById("scale-note").textContent =
    "mm, clipped at " + LIMIT + ". " +
    (state.mode === "level" ? "Zero is each basin's own record mean."
     : state.mode === "delta" ? "Zero is no change from the year before."
     : "Zero is the same storage in " + Y1 + " as in " + Y0 + ".");
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
  const sk = serKey();
  const v = valueFor(b, sk, state.year);
  const a = annual(b, sk);
  const months = a ? a.n[state.year] : 0;
  let html = "<b>" + label(b) + "</b>";
  if (state.mode === "endpoints") {
    const rate = state.product === "t" ? b.tt : b.gt;
    const implied = (rate === null || rate === undefined) ? null : rate * SPAN_YEARS;
    html += '<span class="r">' + Y0 + " to " + Y1 + ": " +
      (v === null ? "no value" : fmt(v) + " mm") + "</span>";
    html += '<span class="r">fitted rate implies ' +
      (implied === null ? "no value" : fmt(implied) + " mm") + "</span>";
    html += '<span class="r">from ' + (a ? a.n[Y0] : 0) + " and " + (a ? a.n[Y1] : 0) +
      " solved months</span>";
  } else {
    html += '<span class="r">' + state.year + ": " +
      (v === null ? "no value" : fmt(v) + " mm") + "</span>";
    html += '<span class="r">' + months + " monthly solutions in " + state.year + "</span>";
  }
  html += '<span class="r">' + b.area.toLocaleString() + " km2, " + b.nm + " mascons</span>";
  showTip(html, e.clientX, e.clientY);
});
mapEl.addEventListener("pointerleave", hideTip);
mapEl.addEventListener("click", e => {
  const p = e.target.closest(".basin");
  if (!p) return;
  const b = cur().basins[+p.dataset.i];
  state.sel = (state.sel === b.id) ? null : b.id;
  paint();
  drawPicked();
});

/* ------------------------------------------------- the folded-by-year chart */
const CW = 720, CH = 250, PL = 46, PR = 44, PT = 14, PB = 26;

function niceStep(span) {
  const raw = span / 5;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag;
}

function axis(lo, hi, step, X0, X1, Y) {
  let s = "";
  for (let v = lo; v <= hi + 1e-9; v += step) {
    const y = Y(v).toFixed(1);
    s += '<line class="' + (Math.abs(v) < 1e-9 ? "zero" : "gridline") +
      '" x1="' + X0 + '" y1="' + y + '" x2="' + X1 + '" y2="' + y + '"></line>';
    s += '<text x="' + (X0 - 7) + '" y="' + (Y(v) + 3.4).toFixed(1) + '" text-anchor="end">' +
      (v > 0 ? "+" : "") + Math.round(v) + "</text>";
  }
  return s;
}

function drawCycle(b) {
  const el = document.getElementById("cycle");
  const sk = serKey();
  const a = annual(b, sk);
  if (!a) { el.innerHTML = ""; return; }

  const byYear = {};
  YEARS.forEach(y => { byYear[y] = new Array(13).fill(null); });
  a.des.forEach((v, i) => { if (v !== null) byYear[YEAR_OF[i]][MONTH_OF[i]] = v; });

  const all = a.des.filter(v => v !== null);
  let lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
  const pad = Math.max((hi - lo) * 0.12, 3);
  lo -= pad; hi += pad;
  const step = niceStep(hi - lo);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;

  const X = m => PL + ((m - 1) / 11) * (CW - PL - PR);
  const Y = v => PT + (1 - (v - lo) / (hi - lo)) * (CH - PT - PB);

  let s = axis(lo, hi, step, PL, CW - PR, Y);
  MONTH_NAMES.forEach((nm, k) => {
    s += '<text x="' + X(k + 1).toFixed(1) + '" y="' + (CH - 8) + '" text-anchor="middle">' + nm + "</text>";
  });
  s += '<text x="' + (PL - 7) + '" y="' + (PT + 2) + '" text-anchor="end">mm</text>';

  YEARS.forEach(y => {
    let d = "", pen = false, lastM = 0;
    for (let m = 1; m <= 12; m++) {
      const v = byYear[y][m];
      if (v === null) { pen = false; continue; }
      d += (pen ? "L" : "M") + X(m).toFixed(1) + " " + Y(v).toFixed(1);
      pen = true;
      lastM = m;
    }
    if (!d) return;
    const dim = (state.year === y) ? 1 : 0.42;
    const wide = (state.year === y) ? 2.6 : 1.5;
    s += '<path class="yr" d="' + d + '" stroke="' + yearColor(y) + '" stroke-width="' + wide +
      '" opacity="' + dim + '"></path>';
    s += '<text class="yrlab" x="' + (X(lastM) + 5).toFixed(1) + '" y="' +
      (Y(byYear[y][lastM]) + 3).toFixed(1) + '" fill="' + yearColor(y) +
      '" opacity="' + dim + '">' + y + "</text>";
  });

  el.setAttribute("viewBox", "0 0 " + CW + " " + CH);
  el.innerHTML = s;
  document.getElementById("cycle-span").textContent =
    "highlighted year " + state.year + ", every other year faded";
}

function drawBars(b) {
  const el = document.getElementById("bars");
  const sk = serKey();
  const a = annual(b, sk);
  if (!a) { el.innerHTML = ""; return; }
  const H = 150, BL = 46, BR = 16, BT = 12, BB = 24;
  const vals = YEARS.map(y => a.mean[y]).filter(v => v !== null);
  let lo = Math.min.apply(null, vals.concat([0])), hi = Math.max.apply(null, vals.concat([0]));
  const pad = Math.max((hi - lo) * 0.15, 2);
  lo -= pad; hi += pad;
  const step = niceStep(hi - lo);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  const Y = v => BT + (1 - (v - lo) / (hi - lo)) * (H - BT - BB);
  const bw = (CW - BL - BR) / YEARS.length;

  let s = axis(lo, hi, step, BL, CW - BR, Y);
  YEARS.forEach((y, k) => {
    const v = a.mean[y];
    const x = BL + k * bw + bw * 0.18;
    const w = bw * 0.64;
    if (v !== null) {
      const y0 = Y(0), y1 = Y(v);
      s += '<rect x="' + x.toFixed(1) + '" y="' + Math.min(y0, y1).toFixed(1) +
        '" width="' + w.toFixed(1) + '" height="' + Math.max(1.5, Math.abs(y1 - y0)).toFixed(1) +
        '" rx="2" fill="' + colorFor(v, LIMIT) + '"' +
        (y === state.year ? ' stroke="var(--ink)" stroke-width="1.2"' : "") + "></rect>";
    }
    s += '<text x="' + (x + w / 2).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle"' +
      (y === state.year ? ' font-weight="600"' : "") + ">" + String(y).slice(2) + "</text>";
  });
  el.setAttribute("viewBox", "0 0 " + CW + " " + H);
  el.innerHTML = s;
}

function drawRows(b) {
  const tb = document.getElementById("rows");
  const a = annual(b, serKey());
  if (!a) { tb.innerHTML = ""; return; }
  const rowsHtml = YEARS.map(y => {
    const m = a.mean[y], d = a.delta[y];
    const hot = (state.mode === "endpoints") ? (y === Y0 || y === Y1) : (y === state.year);
    return "<tr" + (hot ? ' style="background:var(--accent-soft)"' : "") + "><td>" + y +
      "</td><td>" + a.n[y] + "</td><td>" +
      (m === null ? '<span class="ns">n/a</span>' : fmt(m)) + "</td><td>" +
      (d === null ? '<span class="ns">n/a</span>' : fmt(d)) + "</td></tr>";
  }).join("");

  const ec = endpointChange(a);
  const rate = state.product === "t" ? b.tt : b.gt;
  const implied = (rate === null || rate === undefined) ? null : rate * SPAN_YEARS;
  const foot =
    '<tr><td colspan="2" style="font-family:inherit">' + Y0 + " to " + Y1 + ", end to end</td>" +
    '<td colspan="2"><b>' + (ec === null ? "n/a" : fmt(ec) + " mm") + "</b></td></tr>" +
    '<tr><td colspan="2" class="ns" style="font-family:inherit">fitted rate over ' +
    SPAN_YEARS.toFixed(1) + " years implies</td>" +
    '<td colspan="2" class="ns">' + (implied === null ? "n/a" : fmt(implied) + " mm") + "</td></tr>";
  tb.innerHTML = rowsHtml + foot;
}

function drawPicked() {
  const L = cur();
  const b = state.sel === null ? null : L.basins.find(x => x.id === state.sel);
  const title = document.getElementById("pick-title");
  const sub = document.getElementById("pick-sub");
  document.getElementById("clear").disabled = !b;
  if (!b) {
    title.textContent = "Pick a basin";
    sub.textContent = "Click any basin on the map to open its deseasonalised record.";
    document.getElementById("cycle").innerHTML = "";
    document.getElementById("bars").innerHTML = "";
    document.getElementById("rows").innerHTML = "";
    document.getElementById("year-swatches").innerHTML = "";
    document.getElementById("cycle-span").textContent = "";
    return;
  }
  title.textContent = label(b);
  sub.textContent = b.area.toLocaleString() + " km2, " + b.nm + " mascons, " +
    (state.product === "t" ? "total water storage" : "groundwater estimate");
  document.getElementById("year-swatches").innerHTML =
    YEARS.map(y => '<i style="background:' + yearColor(y) + '" title="' + y + '"></i>').join("");
  drawCycle(b);
  drawBars(b);
  drawRows(b);
}

/* --------------------------------------------------------------- animation */
const playBtn = document.getElementById("play");
let timer = null;
function setPlaying(on) {
  state.playing = on;
  playBtn.textContent = on ? "Pause" : "Play";
  clearInterval(timer);
  if (on) {
    timer = setInterval(() => {
      const k = YEARS.indexOf(state.year);
      state.year = YEARS[(k + 1) % YEARS.length];
      paint();
      if (state.sel !== null) { drawCycle(cur().basins.find(x => x.id === state.sel)); drawBars(cur().basins.find(x => x.id === state.sel)); drawRows(cur().basins.find(x => x.id === state.sel)); }
    }, 1100);
  }
}
playBtn.addEventListener("click", () => setPlaying(!state.playing));

function buildYearButtons() {
  const wrap = document.getElementById("year-buttons");
  const counts = {};
  YEARS.forEach(y => { counts[y] = MONTHS.filter(m => +m.slice(0, 4) === y).length; });
  wrap.innerHTML = YEARS.map(y =>
    '<button class="yrbtn' + (counts[y] < 12 ? " partial" : "") + '" data-y="' + y +
    '" aria-pressed="' + (y === state.year) + '" title="' + counts[y] +
    ' months in the record">' + y + "</button>").join("");
  wrap.querySelectorAll(".yrbtn").forEach(btn =>
    btn.addEventListener("click", () => {
      setPlaying(false);
      state.year = +btn.dataset.y;
      paint();
      if (state.sel !== null) drawPicked();
    }));
  document.getElementById("w-years").textContent = YEARS[0] + " to " + YEARS[YEARS.length - 1];
}

/* ------------------------------------------------------------------ wiring */
function fullRender() {
  cache.clear();
  paintScale();
  paint();
  drawPicked();
}

document.getElementById("seg-product").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  state.product = b.dataset.v;
  Array.from(e.currentTarget.children).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  fullRender();
});
document.getElementById("seg-level").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  state.level = b.dataset.v;
  Array.from(e.currentTarget.children).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  buildMap();
  defaults();
  fullRender();
});
document.getElementById("seg-mode").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  state.mode = b.dataset.v;
  Array.from(e.currentTarget.children).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  /* Change is undefined for the first year, so a mode switch onto it would show
     an empty frame; step to the first year that has a value instead. */
  if (state.mode === "delta" && state.year === YEARS[0]) state.year = YEARS[1];
  if (state.mode === "endpoints") setPlaying(false);
  paintScale();
  paint();
  drawPicked();
});
document.getElementById("clear").addEventListener("click", () => {
  state.sel = null;
  paint();
  drawPicked();
});
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  buildMap();
  fullRender();
});

/* Opens on a basin worth looking at rather than an empty panel, and paused if
   the viewer asked for reduced motion. */
function defaults() {
  const L = cur();
  /* Prefer a basin that has both layers, so switching to the groundwater
     estimate does not blank the panel on an ice sheet that is withheld there. */
  const solid = L.basins.filter(b => b.nm >= 20 && b.tt !== null && b.tt !== undefined);
  const both = solid.filter(b => b.gt !== null && b.gt !== undefined && b.g);
  const pool = both.length ? both : solid;
  const worst = pool.slice().sort((a, c) => a.tt - c.tt)[0];
  state.sel = worst ? worst.id : null;
}

buildYearButtons();
buildMap();
defaults();
fullRender();
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) setPlaying(true);
