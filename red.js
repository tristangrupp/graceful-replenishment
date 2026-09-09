/* Downscaling test tab.

   The page holds the metrics, not the verdicts, and recomputes every flag from
   the current threshold settings. Dragging a slider redraws the map, the counts
   and the histogram together, which is the only honest way to show how much of
   a red map is a choice of cut.

   Each product is tested on its own. Three of the five tests are per product;
   the last two compare the two products and do not move when the selection
   changes, which the interface says rather than leaving the reader to notice.

   16,397 basins is more than the DOM wants as separate path elements, so the
   map is a canvas. A second canvas of the same size is painted once with basin
   index encoded as color and used for hit testing. */
(function () {
  "use strict";
  var R = window.RED;
  var N = R.id.length;
  var RED_FILL = "#b5341c";

  /* The same clip and the same ramp as the rate of change tab, so the trend
     layer here can be read straight against that map. */
  var CLIP = 30;
  var RAMP_LIGHT = ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"];
  var RAMP_DARK = ["#a8501f", "#cf7434", "#d99a5f", "#3a4442", "#6fa6cc", "#3987e5", "#1a5fb4"];

  /* Each downscaled product points at the coarse release it was built from.
     GRACE-SeDA v1 names RL06.1Mv03; Li and Kusche names none, so it gets the
     current release. */
  var PRODUCTS = {
    G: { name: "GRACE-SeDA", grid: "0.5 degrees", trend: R.tG, p: R.pG,
         cells: R.ncG, vr: R.vrG, pr: R.prG, pre: R.prGe, rank: R.rkG,
         downscaled: true, parent: R.tC61 || R.tC, parentName: "JPL RL06.1Mv03" },
    L: { name: "Li and Kusche", grid: "0.25 degrees", trend: R.tL, p: R.pL,
         cells: R.ncL, vr: R.vrL, pr: R.prL, pre: R.prLe, rank: R.rkL,
         downscaled: true, parent: R.tC, parentName: "JPL RL06.3Mv04" },
    C: { name: "JPL RL06.3 coarse", grid: "3 degree mascons on a 0.5 degree grid",
         trend: R.tC, p: R.pC, rank: R.rkC, downscaled: false },
    C61: { name: "JPL RL06.1 coarse", grid: "the release GRACE-SeDA was built from",
           trend: R.tC61, p: R.pC61, rank: null, downscaled: false },
    C2: { name: "GSFC coarse", grid: "native mascons, about 12,400 km2", trend: R.tC2,
          p: null, rank: null, downscaled: false }
  };

  var DEFAULTS = R.meta.config;
  var state = {
    product: "G",
    layer: "TREND",
    t: {
      min_cells: DEFAULTS.min_cells,
      max_frac_dominant: DEFAULTS.max_frac_dominant,
      min_var_ratio: DEFAULTS.min_var_ratio,
      max_pred_r2: DEFAULTS.max_pred_r2,
      min_r_GL: DEFAULTS.min_r_GL,
      max_trend_diff_ratio: DEFAULTS.max_trend_diff_ratio,
      max_rank_shift: DEFAULTS.max_rank_shift
    },
    pick: -1
  };

  var SLIDERS = [
    { k: "min_cells", label: "Product cells needed", min: 1, max: 8, step: 1, dp: 0,
      note: "fewer than this in a basin is not a field" },
    { k: "max_frac_dominant", label: "Share inside one mascon", min: 0.5, max: 1, step: 0.01, dp: 2,
      note: "above this the basin sits in a single coarse footprint" },
    { k: "min_var_ratio", label: "Departure variance ratio", min: 0.005, max: 0.5, step: 0.005, dp: 3,
      note: "below this the product is the coarse series resampled" },
    { k: "max_pred_r2", label: "Departure explained by weather", min: 0.4, max: 0.99, step: 0.01, dp: 2,
      note: "above this the added structure is precipitation and soil moisture" },
    { k: "min_r_GL", label: "Correlation between products", min: 0, max: 0.99, step: 0.01, dp: 2,
      note: "below this the two products describe different basins" },
    { k: "max_trend_diff_ratio", label: "Trend gap over trend size", min: 0.1, max: 5, step: 0.1, dp: 1,
      note: "above this they differ by more than the signal" },
    { k: "max_rank_shift", label: "Rank shift, percentile points", min: 2, max: 60, step: 1, dp: 0,
      note: "above this a priority list would reorder" }
  ];

  var OWN = [
    { k: "RED_GEOMETRY", label: "Not resolved" },
    { k: "RED_NO_INDEPENDENT_DEPARTURE", label: "No independent departure" },
    { k: "RED_PREDICTOR_DERIVED", label: "Weather field" }
  ];
  var PAIR = [
    { k: "RED_DISAGREEMENT", label: "Products disagree" },
    { k: "RED_RANK_UNSTABLE", label: "Ranking unstable" }
  ];
  var LABEL = { TREND: "Storage trend", ANY: "Flagged by any test" };
  OWN.concat(PAIR).forEach(function (f) { LABEL[f.k] = f.label; });

  /* ------------------------------------------------------------------ flags */
  var tested = R.tested;
  var flag = {};
  OWN.concat(PAIR).forEach(function (f) { flag[f.k] = new Uint8Array(N); });
  var anyFlag = new Uint8Array(N);
  var anyOwn = new Uint8Array(N);

  function compute() {
    var t = state.t, P = PRODUCTS[state.product];
    var cells = P.cells || null, vr = P.vr || null, pr = P.pr || null;
    for (var i = 0; i < N; i++) {
      var c = cells ? cells[i] : null;
      var g = (c !== null && c !== undefined && c < t.min_cells) ||
              (R.fdom[i] !== null && R.fdom[i] > t.max_frac_dominant);
      var v = vr ? vr[i] : null;
      var nd = v !== null && v !== undefined && v < t.min_var_ratio;
      var q = pr ? pr[i] : null;
      var wf = q !== null && q !== undefined && q > t.max_pred_r2;
      var dis = (R.rGL[i] !== null && R.rGL[i] < t.min_r_GL) ||
                (R.tdr[i] !== null && R.tdr[i] > t.max_trend_diff_ratio);
      var rk = R.shift[i] !== null && R.shift[i] > t.max_rank_shift;

      flag.RED_GEOMETRY[i] = g ? 1 : 0;
      flag.RED_NO_INDEPENDENT_DEPARTURE[i] = nd ? 1 : 0;
      flag.RED_PREDICTOR_DERIVED[i] = wf ? 1 : 0;
      flag.RED_DISAGREEMENT[i] = dis ? 1 : 0;
      flag.RED_RANK_UNSTABLE[i] = rk ? 1 : 0;
      anyOwn[i] = (g || nd || wf) ? 1 : 0;
      anyFlag[i] = (g || nd || wf || dis || rk) ? 1 : 0;
    }
  }

  function active() {
    if (state.layer === "ANY") return anyFlag;
    return flag[state.layer] || anyFlag;
  }

  function tally(mask) {
    var n = 0, a = 0, tot = 0;
    for (var i = 0; i < N; i++) {
      if (!tested[i]) continue;
      tot += R.area[i];
      if (mask[i]) { n++; a += R.area[i]; }
    }
    return { n: n, share: tot ? a / tot : 0 };
  }

  /* -------------------------------------------------------------- geometry */
  var paths = new Array(N);
  for (var i = 0; i < N; i++) paths[i] = new Path2D(R.d[i]);

  var cv = document.getElementById("map");
  var ctx = cv.getContext("2d");
  var pickCv = document.createElement("canvas");
  var pickCtx = pickCv.getContext("2d", { willReadFrequently: true });
  var scale = 1;

  function css(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  }
  function isDark() {
    var stamped = document.documentElement.getAttribute("data-theme");
    if (stamped === "dark") return true;
    if (stamped === "light") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function ramp() { return isDark() ? RAMP_DARK : RAMP_LIGHT; }
  function mix(a, b, t) {
    var pa = [1, 3, 5].map(function (i) { return parseInt(a.substr(i, 2), 16); });
    var pb = [1, 3, 5].map(function (i) { return parseInt(b.substr(i, 2), 16); });
    return "rgb(" + pa.map(function (v, i) {
      return Math.round(v + (pb[i] - v) * t);
    }).join(",") + ")";
  }
  function colorFor(v) {
    var r = ramp();
    var x = Math.max(-CLIP, Math.min(CLIP, v));
    var u = (x + CLIP) / (2 * CLIP) * (r.length - 1);
    var i = Math.min(r.length - 2, Math.floor(u));
    return mix(r[i], r[i + 1], u - i);
  }

  function sizeCanvas() {
    var w = cv.parentNode.clientWidth || 900;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pxw = Math.round(w * dpr);
    scale = pxw / R.width;
    cv.width = pxw;
    cv.height = Math.round(R.height * scale);
    cv.style.width = w + "px";
    cv.style.height = Math.round(R.height * scale / dpr) + "px";
    pickCv.width = cv.width;
    pickCv.height = cv.height;
    paintPick();
  }

  function paintPick() {
    pickCtx.setTransform(1, 0, 0, 1, 0, 0);
    pickCtx.clearRect(0, 0, pickCv.width, pickCv.height);
    pickCtx.setTransform(scale, 0, 0, scale, 0, 0);
    for (var i = 0; i < N; i++) {
      pickCtx.fillStyle = "rgb(" + (i & 255) + "," + ((i >> 8) & 255) + ",200)";
      pickCtx.fill(paths[i], "evenodd");
    }
  }

  function drawMap() {
    var nodata = css("--nodata") || "#dcdcd6";
    var sunk = css("--sunk") || "#e8e8e4";
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    var i;
    if (state.layer === "TREND") {
      var tr = PRODUCTS[state.product].trend;
      for (i = 0; i < N; i++) {
        var v = tr ? tr[i] : null;
        ctx.fillStyle = (v === null || v === undefined) ? nodata : colorFor(v);
        ctx.fill(paths[i], "evenodd");
      }
    } else {
      var mask = active();
      ctx.fillStyle = nodata;
      for (i = 0; i < N; i++) if (!tested[i]) ctx.fill(paths[i], "evenodd");
      ctx.fillStyle = sunk;
      for (i = 0; i < N; i++) if (tested[i] && !mask[i]) ctx.fill(paths[i], "evenodd");
      ctx.fillStyle = RED_FILL;
      for (i = 0; i < N; i++) if (tested[i] && mask[i]) ctx.fill(paths[i], "evenodd");
    }
    if (state.pick >= 0) {
      ctx.strokeStyle = css("--ink") || "#151513";
      ctx.lineWidth = 6 / scale;
      ctx.stroke(paths[state.pick]);
    }
  }

  /* ----------------------------------------------------------------- panels */
  function fmt(v, dp) {
    if (v === null || v === undefined || !isFinite(v)) return "n/a";
    return Number(v).toFixed(dp === undefined ? 2 : dp);
  }
  function signed(v, dp) {
    if (v === null || v === undefined || !isFinite(v)) return "n/a";
    return (v > 0 ? "+" : "") + Number(v).toFixed(dp === undefined ? 1 : dp);
  }
  function thousands(v) { return Math.round(v).toLocaleString("en-US"); }
  function median(a) {
    if (!a.length) return null;
    var s = a.slice().sort(function (x, y) { return x - y; });
    var h = Math.floor(s.length / 2);
    return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
  }

  function drawCounts() {
    var P = PRODUCTS[state.product];
    var rows = "";
    document.getElementById("counts-title").textContent =
      P.downscaled ? "Counts for " + P.name : "Counts";
    if (!P.downscaled) {
      document.getElementById("counts").innerHTML =
        "<tr><td class=\"name ns\" colspan=\"3\">" + P.name +
        " is the reference, not a product under test. Pick a downscaled solution above.</td></tr>";
      document.getElementById("w-red").textContent = "n/a";
      return;
    }
    var own = tally(anyOwn);
    rows += "<tr><td class=\"name\"><b>Any of its own tests</b></td><td><b>" + thousands(own.n) +
            "</b></td><td><b>" + (own.share * 100).toFixed(0) + "%</b></td></tr>";
    OWN.forEach(function (f) {
      var c = tally(flag[f.k]);
      rows += "<tr><td class=\"name\">" + f.label + "</td><td>" + thousands(c.n) +
              "</td><td>" + (c.share * 100).toFixed(0) + "%</td></tr>";
    });
    PAIR.forEach(function (f) {
      var c = tally(flag[f.k]);
      rows += "<tr><td class=\"name ns\">" + f.label + ", both products</td><td class=\"ns\">" +
              thousands(c.n) + "</td><td class=\"ns\">" + (c.share * 100).toFixed(0) +
              "%</td></tr>";
    });
    var all = tally(anyFlag);
    rows += "<tr><td class=\"name\">Any test at all</td><td>" + thousands(all.n) +
            "</td><td>" + (all.share * 100).toFixed(0) + "%</td></tr>";
    var notRed = 0, notArea = 0, tot = 0;
    for (var i = 0; i < N; i++) {
      if (!tested[i]) continue;
      tot += R.area[i];
      if (!anyFlag[i]) { notRed++; notArea += R.area[i]; }
    }
    rows += "<tr><td class=\"name ns\">not flagged by anything</td><td class=\"ns\">" +
            thousands(notRed) + "</td><td class=\"ns\">" +
            (notArea / tot * 100).toFixed(0) + "%</td></tr>";
    document.getElementById("counts").innerHTML = rows;
    document.getElementById("w-red").textContent =
      thousands(own.n) + " / " + thousands(R.meta.n_tested);
  }

  /* The part that says why the map above should not be read as a fine-scale
     result. Every row is computed from the payload, so it moves with the
     selection instead of being a fixed sentence. */
  function drawEviscerate() {
    var P = PRODUCTS[state.product];
    var tr = P.trend, pv = P.p, tc = P.parent || R.tC, tc2 = R.tC2;
    var signSel = 0, signPair = 0, nSel = 0, nPair = 0, weak = 0, nP = 0;
    var gaps = [], mags = [], resolved = 0;
    for (var i = 0; i < N; i++) {
      if (!tested[i]) continue;
      var a = tr ? tr[i] : null, b = tc[i], c2 = tc2 ? tc2[i] : null;
      if (a !== null && b !== null) {
        nSel++;
        if ((a < 0) !== (b < 0)) signSel++;
        gaps.push(Math.abs(a - b));
        mags.push(Math.abs(b));
      }
      if (b !== null && c2 !== null) {
        nPair++;
        if ((b < 0) !== (c2 < 0)) signPair++;
      }
      if (pv && pv[i] !== null) { nP++; if (pv[i] >= 0.05) weak++; }
      var cells = P.cells ? P.cells[i] : null;
      if (cells !== null && cells !== undefined && cells >= 2 &&
          R.fdom[i] !== null && R.fdom[i] <= 0.95) resolved++;
    }
    var mg = median(gaps), mm = median(mags);
    var rows = [];
    if (P.downscaled) {
      rows.push(["basins whose sign flips against " + (P.parentName || "the coarse solution"),
        thousands(signSel) + " of " + thousands(nSel) +
        ", " + (signSel / nSel * 100).toFixed(0) + "%"]);
    }
    rows.push(["basins whose sign flips between the two processing centers",
      thousands(signPair) + " of " + thousands(nPair) +
      ", " + (signPair / nPair * 100).toFixed(0) + "%"]);
    if (nP) {
      rows.push(["basins whose own trend is not separable from zero at p 0.05",
        thousands(weak) + " of " + thousands(nP) + ", " + (weak / nP * 100).toFixed(0) + "%"]);
    }
    if (P.downscaled) {
      rows.push(["median gap from the coarse trend, against the median trend size",
        fmt(mg, 2) + " mm/yr against " + fmt(mm, 2) + " mm/yr"]);
      rows.push(["basins the geometry test says are resolved at all",
        thousands(resolved) + " of " + thousands(R.meta.n_tested) +
        ", " + (resolved / R.meta.n_tested * 100).toFixed(0) + "%"]);
    }
    var g = R.meta.geometry;
    rows.push(["basins reaching the 63,000 km2 reliable unit",
      thousands(g.n_above_reliable_threshold) + " of " + thousands(g.n_basins) +
      ", " + (g.area_share_above_reliable_threshold * 100).toFixed(1) + "% of the land area"]);
    document.getElementById("evis").innerHTML = rows.map(function (r) {
      return "<tr><td class=\"name\">" + r[0] + "</td><td>" + r[1] + "</td></tr>";
    }).join("");

    document.getElementById("evis-sub").textContent = P.name;
    var note = "";
    if (P.downscaled) {
      note = "The fit itself is sound: least squares with annual and semi-annual harmonics, on a " +
        "real series. Three things argue against reading it basin by basin. Two processing " +
        "centers already disagree on the direction of change in " +
        (signPair / nPair * 100).toFixed(0) + " percent of these basins before any downscaling. " +
        "The median gap between " + P.name + " and its own parent solution is " + fmt(mg, 2) +
        " mm/yr against a median trend of " + fmt(mm, 2) + " mm/yr. And in most basins the " +
        "value drawn is a mascon value repeated across every basin inside that mascon, so the " +
        "color implies a resolution the observation does not have.";
    } else {
      note = "This is a coarse solution drawn on level 6 outlines. Neighboring basins inside one " +
        "mascon are given the same value, so any texture in this map is the basin outlines, not " +
        "the gravity field. Switch to the other coarse solution to see how much of the pattern " +
        "survives a change of processing center.";
    }
    document.getElementById("evis-note").textContent = note;
  }

  var DIST = {
    RED_GEOMETRY: { arr: function () { return R.fdom; }, log: false,
                    label: "share of basin inside one mascon", markKey: "max_frac_dominant" },
    RED_NO_INDEPENDENT_DEPARTURE: { arr: function () { return PRODUCTS[state.product].vr; }, log: true,
                        label: "departure variance over coarse variance", markKey: "min_var_ratio" },
    RED_PREDICTOR_DERIVED: { arr: function () { return PRODUCTS[state.product].pr; }, log: false,
                             label: "adjusted R squared on weather fields", markKey: "max_pred_r2" },
    RED_DISAGREEMENT: { arr: function () { return R.rGL; }, log: false,
                        label: "correlation between the two products", markKey: "min_r_GL" },
    RED_RANK_UNSTABLE: { arr: function () { return R.shift; }, log: false,
                         label: "rank shift, percentile points", markKey: "max_rank_shift" }
  };

  function distSpec() {
    if (DIST[state.layer]) return DIST[state.layer];
    return { arr: function () { return R.area; }, log: true, label: "basin area, km2",
             mark: 63000, markLabel: "63,000 km2 reliable unit" };
  }

  function drawDist() {
    var spec = distSpec();
    var arr = spec.arr();
    var c = document.getElementById("dist");
    var w = c.parentNode.clientWidth || 420, h = 140;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = w * dpr; c.height = h * dpr;
    c.style.width = w + "px"; c.style.height = h + "px";
    var g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    document.getElementById("dist-sub").textContent = spec.label;
    if (!arr) {
      g.fillStyle = css("--muted");
      g.font = "11px 'IBM Plex Mono', monospace";
      g.fillText("not available for this solution", 4, 20);
      return;
    }

    var mask = state.layer === "TREND" ? anyOwn : active();
    var vals = [], i, v;
    for (i = 0; i < N; i++) {
      if (!tested[i]) continue;
      v = arr[i];
      if (v === null || v === undefined || !isFinite(v)) continue;
      if (spec.log && v <= 0) continue;
      vals.push(i);
    }
    if (!vals.length) return;
    var lows = Infinity, highs = -Infinity;
    for (i = 0; i < vals.length; i++) {
      v = spec.log ? Math.log10(arr[vals[i]]) : arr[vals[i]];
      if (v < lows) lows = v;
      if (v > highs) highs = v;
    }
    var NB = 46, pad = 26, plotW = w - pad - 6, plotH = h - 22;
    var red = new Float64Array(NB), pass = new Float64Array(NB);
    for (i = 0; i < vals.length; i++) {
      v = spec.log ? Math.log10(arr[vals[i]]) : arr[vals[i]];
      var b = Math.min(NB - 1, Math.floor((v - lows) / (highs - lows || 1) * NB));
      if (mask[vals[i]]) red[b]++; else pass[b]++;
    }
    var top = 0;
    for (i = 0; i < NB; i++) top = Math.max(top, red[i] + pass[i]);
    var bw = plotW / NB;
    for (i = 0; i < NB; i++) {
      var x = pad + i * bw;
      var hp = (pass[i] / top) * plotH, hr = (red[i] / top) * plotH;
      g.fillStyle = css("--sunk") || "#e8e8e4";
      g.fillRect(x, plotH - hp, Math.max(bw - 1, 1), hp);
      g.fillStyle = RED_FILL;
      g.fillRect(x, plotH - hp - hr, Math.max(bw - 1, 1), hr);
    }
    var markVal = spec.mark !== undefined ? spec.mark
      : (spec.markKey ? state.t[spec.markKey] : null);
    if (markVal !== null && markVal !== undefined) {
      var mv = spec.log ? Math.log10(markVal) : markVal;
      if (mv >= lows && mv <= highs) {
        var mx = pad + (mv - lows) / (highs - lows) * plotW;
        g.strokeStyle = css("--ink") || "#151513";
        g.setLineDash([3, 3]);
        g.beginPath(); g.moveTo(mx, 0); g.lineTo(mx, plotH); g.stroke();
        g.setLineDash([]);
      }
    }
    g.fillStyle = css("--muted") || "#6d6d66";
    g.font = "10px 'IBM Plex Mono', monospace";
    var lab = function (x) { return spec.log ? Math.pow(10, x) : x; };
    g.fillText(shortNum(lab(lows)), pad, h - 6);
    g.textAlign = "right";
    g.fillText(shortNum(lab(highs)), w - 6, h - 6);
    g.textAlign = "left";
    if (spec.markLabel) g.fillText(spec.markLabel, pad, 10);
  }

  function shortNum(v) {
    if (!isFinite(v)) return "";
    if (Math.abs(v) >= 10000) return (v / 1000).toFixed(0) + "k";
    if (Math.abs(v) >= 10) return v.toFixed(0);
    if (Math.abs(v) >= 1) return v.toFixed(1);
    return v.toFixed(3);
  }

  function drawRanks() {
    var c = document.getElementById("ranks");
    var w = c.parentNode.clientWidth || 420;
    var pad = 30;
    var size = Math.max(Math.min((w - 3 * pad) / 2, 320), 120);
    var h = size + 26;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = w * dpr; c.height = h * dpr;
    c.style.width = w + "px"; c.style.height = h + "px";
    var g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    var sp = R.meta.spearman || {};
    var panels = [
      { y: R.rkG, name: "GRACE-SeDA", rho: sp.G_vs_coarse },
      { y: R.rkL, name: "Li and Kusche", rho: sp.L_vs_coarse }
    ];
    g.font = "10px 'IBM Plex Mono', monospace";
    panels.forEach(function (p, k) {
      var x0 = pad + k * (size + pad + 10), y0 = 12;
      g.strokeStyle = css("--line") || "#cfcfc9";
      g.strokeRect(x0, y0, size, size);
      g.beginPath(); g.moveTo(x0, y0 + size); g.lineTo(x0 + size, y0); g.stroke();
      if (!p.y) {
        g.fillStyle = css("--muted");
        g.fillText("not available", x0 + 6, y0 + size / 2);
        return;
      }
      g.fillStyle = "rgba(181,52,28,0.30)";
      for (var i = 0; i < N; i++) {
        if (!tested[i] || R.rkC[i] === null || p.y[i] === null) continue;
        var px = x0 + (R.rkC[i] / 100) * size;
        var py = y0 + size - (p.y[i] / 100) * size;
        g.fillRect(px, py, 1.2, 1.2);
      }
      g.fillStyle = css("--ink-2") || "#3c3c38";
      g.fillText(p.name + (p.rho !== undefined && p.rho !== null
        ? "  rho " + p.rho.toFixed(3) : ""), x0, y0 - 3);
    });
    document.getElementById("rank-sub").textContent =
      sp.G_vs_L !== undefined && sp.G_vs_L !== null
        ? "the two products agree with each other at rho " + sp.G_vs_L.toFixed(3) : "";
  }

  function drawSliders() {
    var html = "";
    SLIDERS.forEach(function (s) {
      html += "<div class=\"slider\">" +
        "<label for=\"s-" + s.k + "\">" + s.label +
        "<b class=\"mono\" id=\"v-" + s.k + "\"></b></label>" +
        "<input type=\"range\" id=\"s-" + s.k + "\" min=\"" + s.min + "\" max=\"" + s.max +
        "\" step=\"" + s.step + "\" value=\"" + state.t[s.k] + "\">" +
        "<span class=\"snote\">" + s.note + " &middot; published run " +
        fmt(DEFAULTS[s.k], s.dp) + "</span></div>";
    });
    document.getElementById("sliders").innerHTML = html;
    SLIDERS.forEach(function (s) {
      var el = document.getElementById("s-" + s.k);
      el.addEventListener("input", function () {
        state.t[s.k] = parseFloat(el.value);
        document.getElementById("v-" + s.k).textContent = fmt(state.t[s.k], s.dp);
        recompute();
      });
      document.getElementById("v-" + s.k).textContent = fmt(state.t[s.k], s.dp);
    });
  }

  /* ---------------------------------------------------------------- picking */
  var tip = document.getElementById("tip");

  function pickAt(ev) {
    var r = cv.getBoundingClientRect();
    var dpr = cv.width / r.width;
    var x = Math.round((ev.clientX - r.left) * dpr);
    var y = Math.round((ev.clientY - r.top) * dpr);
    if (x < 1 || y < 1 || x >= cv.width - 1 || y >= cv.height - 1) return -1;
    var d = pickCtx.getImageData(x - 1, y - 1, 3, 3).data;
    var best = -1, bestCount = 0, seen = {};
    for (var p = 0; p < 9; p++) {
      var o = p * 4;
      if (d[o + 3] !== 255 || d[o + 2] !== 200) continue;
      var idx = d[o] + (d[o + 1] << 8);
      seen[idx] = (seen[idx] || 0) + 1;
      if (seen[idx] > bestCount) { bestCount = seen[idx]; best = idx; }
    }
    return best < N ? best : -1;
  }

  function pickRows(i) {
    if (i < 0) return "<tr><td class=\"name\">move over the map</td><td></td></tr>";
    var P = PRODUCTS[state.product];
    var rows = [
      ["basin", R.id[i]],
      ["region", R.reg[i] + "  " + Math.abs(R.lat[i]).toFixed(1) + (R.lat[i] < 0 ? "S " : "N ") +
        Math.abs(R.lon[i]).toFixed(1) + (R.lon[i] < 0 ? "W" : "E")],
      ["area, km2", thousands(R.area[i])],
      ["trend, mm/yr", signed(P.trend ? P.trend[i] : null, 2) +
        (P.p && P.p[i] !== null ? "  p " + fmt(P.p[i], 3) : "")],
      ["trend, JPL then GSFC coarse", signed(R.tC[i], 2) + " / " + signed(R.tC2 ? R.tC2[i] : null, 2)],
      ["cells, SeDA / Li and Kusche", (R.ncG[i] === null ? "n/a" : R.ncG[i]) + " / " +
        (R.ncL && R.ncL[i] !== null ? R.ncL[i] : "n/a")],
      ["mascons overlapped", R.nfp[i]],
      ["share in largest mascon", fmt(R.fdom[i], 2)],
      ["departure variance ratio", fmt(P.vr ? P.vr[i] : null, 3)],
      ["two coarse solutions differ by", fmt(R.vrS[i], 3)],
      ["departure on weather, adj R2", fmt(P.pr ? P.pr[i] : null, 2)],
      ["products correlate", fmt(R.rGL[i], 2)],
      ["rank shift", fmt(R.shift[i], 1)]
    ];
    var out = rows.map(function (r) {
      return "<tr><td class=\"name\">" + r[0] + "</td><td>" + r[1] + "</td></tr>";
    }).join("");
    var fl = [];
    OWN.concat(PAIR).forEach(function (f) { if (flag[f.k][i]) fl.push(f.label); });
    out += "<tr><td class=\"name\">flags</td><td>" +
      (tested[i] ? (fl.length ? fl.join(", ") : "none") : "not tested") + "</td></tr>";
    return out;
  }

  cv.addEventListener("mousemove", function (ev) {
    var i = pickAt(ev);
    if (i !== state.pick) {
      state.pick = i;
      document.getElementById("pick").innerHTML = pickRows(i);
      drawMap();
    }
    if (i >= 0) {
      tip.innerHTML = "<b>" + R.id[i] + "</b><span class=\"r\">" + R.reg[i] + ", " +
        thousands(R.area[i]) + " km2</span>";
      tip.style.opacity = 1;
      tip.style.left = Math.min(ev.clientX + 12, window.innerWidth - 260) + "px";
      tip.style.top = (ev.clientY + 14) + "px";
    } else {
      tip.style.opacity = 0;
    }
  });
  cv.addEventListener("mouseleave", function () {
    tip.style.opacity = 0;
    state.pick = -1;
    document.getElementById("pick").innerHTML = pickRows(-1);
    drawMap();
  });

  /* ------------------------------------------------------------------- wire */
  function press(container, value) {
    [].forEach.call(document.querySelectorAll(container + " button"), function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.v === value));
    });
  }

  function syncChrome() {
    var P = PRODUCTS[state.product];
    var isTrend = state.layer === "TREND";
    document.getElementById("legend-trend").hidden = !isTrend;
    document.getElementById("legend-flags").hidden = isTrend;
    document.getElementById("ramp").style.background =
      "linear-gradient(90deg," + ramp().join(",") + ")";

    document.getElementById("map-title").textContent =
      isTrend ? "Storage trend, " + P.name : LABEL[state.layer];

    var coarseOnly = !P.downscaled;
    [].forEach.call(document.querySelectorAll("#seg-layer button, #seg-pair button"),
      function (b) { b.disabled = coarseOnly && b.dataset.v !== "TREND"; });
    document.getElementById("prod-hint").textContent = coarseOnly
      ? "a coarse reference, shown for the trend layer only"
      : P.name + ", " + P.grid + ", tested on its own";

    var sub = document.getElementById("map-sub");
    var note = document.getElementById("map-note");
    if (isTrend) {
      sub.textContent = R.meta.n_months + " months, " + R.meta.common_period[0] + " to " +
        R.meta.common_period[1];
      note.textContent = "Slope of one line fitted through every month, with annual and " +
        "semi-annual harmonics alongside it, in millimeters of water per year. Same estimator " +
        "and same color scale as the first tab, on 16,397 level 6 basins rather than 247, and " +
        "over 2002 to 2022 rather than the GRACE-FO window. Read the panel below before using " +
        "any of it.";
    } else {
      var c = tally(active());
      sub.textContent = thousands(c.n) + " of " + thousands(R.meta.n_tested) +
        " tested basins, " + (c.share * 100).toFixed(0) + "% of tested land area";
      note.textContent = PAIR.some(function (f) { return f.k === state.layer; })
        ? "This test compares the two products with each other, so it does not move when the " +
          "solution above changes."
        : "Computed for " + P.name + " alone. Nothing in this layer asks the two products to " +
          "agree.";
    }
  }

  document.getElementById("seg-product").addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    state.product = b.dataset.v;
    if (!PRODUCTS[state.product].downscaled) state.layer = "TREND";
    press("#seg-product", state.product);
    press("#seg-layer", state.layer);
    press("#seg-pair", state.layer);
    recompute();
  });

  function layerClick(ev) {
    var b = ev.target.closest("button");
    if (!b || b.disabled) return;
    state.layer = b.dataset.v;
    press("#seg-layer", state.layer);
    press("#seg-pair", state.layer);
    recompute();
  }
  document.getElementById("seg-layer").addEventListener("click", layerClick);
  document.getElementById("seg-pair").addEventListener("click", layerClick);

  document.getElementById("reset").addEventListener("click", function () {
    SLIDERS.forEach(function (s) {
      state.t[s.k] = DEFAULTS[s.k];
      var el = document.getElementById("s-" + s.k);
      el.value = DEFAULTS[s.k];
      document.getElementById("v-" + s.k).textContent = fmt(DEFAULTS[s.k], s.dp);
    });
    recompute();
  });

  function recompute() {
    compute();
    syncChrome();
    drawMap();
    drawCounts();
    drawEviscerate();
    drawDist();
  }

  function fillText() {
    var m = R.meta;
    document.getElementById("w-window").textContent =
      m.common_period[0] + " to " + m.common_period[1];
    document.getElementById("nav-window").textContent =
      "Downscaling test, " + m.common_period[0] + " to " + m.common_period[1];

    var g = m.geometry;
    document.getElementById("foot-area").innerHTML =
      "<b>Basin size.</b> " + thousands(g.n_above_reliable_threshold) + " of " +
      thousands(g.n_basins) + " level 6 basins reach the 63,000 km2 reliable unit of Vishwakarma, " +
      "Devaraju and Sneeuw (2018), which is " + (g.area_share_above_reliable_threshold * 100).toFixed(1) +
      " percent of the level's land area. The median basin is " +
      thousands(g.area_km2["50"]) + " km2 and holds " + g.median_n_cells_G +
      " GRACE-SeDA cells and " + g.median_n_cells_L + " Li and Kusche cells.";
    document.getElementById("foot-solution").innerHTML =
      "<b>Two floors under the departure.</b> For the median basin the departure from the release it " +
      "was built from is " + fmt(m.medians.var_ratio_G, 3) + " of the coarse variance for " +
      "GRACE-SeDA and " + fmt(m.medians.var_ratio_L, 3) + " for Li and Kusche. Moving the same " +
      "center one release, JPL RL06.1 to RL06.3, costs " + fmt(m.medians.var_ratio_release, 5) +
      ". Moving between two centers, JPL to GSFC, costs " +
      fmt(m.medians.var_ratio_solution, 3) + ", so the whole of Li and Kusche's departure is " +
      "about a fifth of what changing processing center does to the same months.";
    var sp = m.spearman || {};
    document.getElementById("foot-spearman").innerHTML =
      "<b>Ranking.</b> Ranked by depletion trend, GRACE-SeDA agrees with the coarse solution at " +
      "Spearman " + fmt(sp.G_vs_coarse, 3) + " and Li and Kusche at " + fmt(sp.L_vs_coarse, 3) +
      ". The two downscaled products agree with each other at " + fmt(sp.G_vs_L, 3) +
      ", and the two coarse solutions agree at " + fmt(sp.coarse_JPL_vs_GSFC, 3) + ".";
    var co = R.corners;
    if (co) {
      document.getElementById("foot-corners").innerHTML =
        "<b>How much of this is the thresholds.</b> Set all seven sliders to the most generous " +
        "end of their range at once and " + thousands(co.most_generous.n_RED_ANY) +
        " basins stay flagged, " + Math.round(co.most_generous.share_of_tested * 100) +
        " percent of those tested. Set them all to the strictest end and " +
        thousands(co.strictest.n_RED_ANY) + " are, every basin the test could reach. Those two " +
        "counts use all five tests together.";
    }
  }

  window.addEventListener("resize", function () {
    sizeCanvas(); drawMap(); drawDist(); drawRanks();
  });
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  if (mq.addEventListener) mq.addEventListener("change", function () { recompute(); });

  fillText();
  drawSliders();
  sizeCanvas();
  compute();
  syncChrome();
  drawMap();
  drawCounts();
  drawEviscerate();
  drawDist();
  drawRanks();
  document.getElementById("pick").innerHTML = pickRows(-1);
})();
