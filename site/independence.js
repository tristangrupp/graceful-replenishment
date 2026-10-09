/* Shared signal tab.

   The other tabs hatch at a flat p 0.05 and leave the reader to assume 1,283
   basins are 1,283 findings. This page makes both assumptions movable: pick a
   multiple-testing rule and watch the map thin, and read how far the
   resemblance between basins actually reaches.

   No new geometry ships with it. data.js already holds the level 4 polygons,
   trends and p-values; independence_data.js adds the measured statistics and
   the p-value each rule accepts, which is two kilobytes. */
(function () {
  "use strict";
  var D = window.GRACE;
  var IND = window.IND;
  var L = D.levels["04"];
  var CLIP = 30;
  var RAMP_LIGHT = ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"];
  var RAMP_DARK = ["#a8501f", "#cf7434", "#d99a5f", "#3a4442", "#6fa6cc", "#3987e5", "#1a5fb4"];
  var state = { product: "t", rule: "raw" };

  var RULES = {
    raw: "one test per basin, nothing adjusted",
    bh: "false discovery rate at 5 percent, valid under independence or positive dependence",
    by: "false discovery rate at 5 percent, valid under any dependence",
    bonferroni: "no false positive anywhere, 0.05 divided by the number of basins"
  };

  function isDark() {
    var s = document.documentElement.getAttribute("data-theme");
    if (s === "dark") return true;
    if (s === "light") return false;
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
  var fmt = function (n) { return (n > 0 ? "+" : "") + n.toFixed(2); };
  var thousands = function (n) { return n.toLocaleString(); };
  var trendKey = function () { return state.product === "t" ? "tt" : "gt"; };
  var pKey = function () { return state.product === "t" ? "tp" : "gp"; };
  var cuts = function () { return IND.layers[state.product].cuts; };
  /* Every rule reduces to one number: the largest p-value it still accepts.
     Benjamini-Hochberg and Benjamini-Yekutieli walk the sorted p-values
     against a rising threshold, and the export stores where each walk
     stopped, so the map needs a single comparison. */
  function cut() {
    var c = cuts();
    return state.rule === "raw" ? c.raw
      : state.rule === "bonferroni" ? c.bonferroni
      : c[state.rule];
  }

  /* ------------------------------------------------------------- the map */
  var mapEl = document.getElementById("map");

  function buildMap() {
    var fills = "", hatch = "";
    L.basins.forEach(function (b, i) {
      fills += '<path class="basin" data-i="' + i + '" d="' + b.d + '"></path>';
      hatch += '<path class="hatch" data-i="' + i + '" d="' + b.d + '" fill="url(#hx)"></path>';
    });
    var hatchInk = getComputedStyle(document.body).getPropertyValue("--hatch").trim();
    mapEl.setAttribute("viewBox", "0 0 " + D.width + " " + D.height);
    mapEl.innerHTML =
      '<defs><pattern id="hx" width="34" height="34" patternUnits="userSpaceOnUse" ' +
      'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="34" stroke="' + hatchInk +
      '" stroke-width="8" opacity="0.55"></line></pattern></defs>' +
      '<g id="fills">' + fills + '</g><g id="hatches">' + hatch + '</g>';
    paint();
  }

  function paint() {
    var tk = trendKey(), pk = pKey(), c = cut();
    var fills = mapEl.querySelectorAll("#fills path");
    var hats = mapEl.querySelectorAll("#hatches path");
    var kept = 0, have = 0;
    L.basins.forEach(function (b, i) {
      var v = b[tk], p = b[pk];
      var missing = v === null || v === undefined;
      var pass = !missing && p !== null && p !== undefined && p <= c;
      if (!missing) { have++; if (pass) kept++; }
      fills[i].style.fill = missing ? "var(--nodata)" : colorFor(v);
      hats[i].style.display = (!missing && !pass) ? "" : "none";
    });
    document.getElementById("ramp").style.background =
      "linear-gradient(90deg," + ramp().join(",") + ")";
    document.getElementById("sw-hatch").style.background =
      "repeating-linear-gradient(45deg,transparent 0 3px,var(--hatch) 3px 4px)";

    var lay = IND.layers[state.product];
    document.getElementById("map-title").textContent = lay.label + ", level 4";
    document.getElementById("map-sub").textContent =
      thousands(kept) + " of " + thousands(have) + " basins pass";
    document.getElementById("map-note").textContent =
      RULES[state.rule] + ". A basin needs p at or below " +
      (c < 0.0001 ? c.toExponential(1) : c.toFixed(4)) + "." +
      (state.rule === "raw" ? ""
        : " The flat cut keeps " + thousands(lay.cuts.n_raw) + ".") +
      " Either way the field is worth about " + Math.round(lay.n_eff) +
      " independent units, so these are not " + thousands(kept) + " separate findings.";
    document.getElementById("w-neff").textContent =
      Math.round(lay.n_eff) + " of " + thousands(lay.n);
  }

  /* ------------------------------------------------------- the correlogram */
  function drawCorrelogram() {
    var lay = IND.layers[state.product];
    var cg = lay.correlogram;
    var W = 620, H = 230, padL = 40, padR = 12, padT = 12, padB = 42;
    var iMax = Math.max(0.8, Math.ceil(Math.max.apply(null,
      cg.map(function (c) { return c.I; })) * 10) / 10);
    var x0 = Math.min.apply(null, cg.map(function (c) { return c.lo; }));
    var x1 = Math.max.apply(null, cg.map(function (c) { return c.hi; }));
    var X = function (v) { return padL + (v - x0) / (x1 - x0) * (W - padL - padR); };
    var Y = function (v) { return padT + (1 - v / iMax) * (H - padT - padB); };
    var s = "";
    [0, 0.2, 0.4, 0.6, 0.8].filter(function (v) { return v <= iMax; }).forEach(function (v) {
      s += '<line class="gridline" x1="' + padL + '" y1="' + Y(v).toFixed(1) +
        '" x2="' + (W - padR) + '" y2="' + Y(v).toFixed(1) + '"></line>' +
        '<text x="' + (padL - 6) + '" y="' + (Y(v) + 3).toFixed(1) +
        '" text-anchor="end">' + v.toFixed(1) + "</text>";
    });
    cg.forEach(function (c) {
      var xa = X(c.lo) + 1.5, xb = X(c.hi) - 1.5;
      var y = Y(c.I), h = Y(0) - y;
      /* A band whose permutation test does not clear 0.05 is drawn hollow, so
         the distance where resemblance runs out is visible rather than stated. */
      var solid = c.p < 0.05;
      s += '<rect x="' + xa.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' +
        Math.max(1, xb - xa).toFixed(1) + '" height="' + Math.max(0.5, h).toFixed(1) +
        '" fill="' + (solid ? "#b5341c" : "none") + '" stroke="#b5341c" ' +
        'stroke-width="1" opacity="' + (solid ? 0.85 : 1) + '"></rect>';
    });
    var ef = lay.e_folding_km;
    if (ef >= x0 && ef <= x1) {
      s += '<line class="cross" x1="' + X(ef).toFixed(1) + '" y1="' + padT +
        '" x2="' + X(ef).toFixed(1) + '" y2="' + Y(0).toFixed(1) +
        '" stroke-dasharray="4 3"></line>' +
        '<text x="' + (X(ef) + 4).toFixed(1) + '" y="' + (padT + 10) + '">' +
        ef + " km</text>";
    }
    s += '<line class="zero" x1="' + padL + '" y1="' + Y(0).toFixed(1) +
      '" x2="' + (W - padR) + '" y2="' + Y(0).toFixed(1) + '"></line>';
    [0, 1000, 2000, 3000, 4000, 5000, 6000].filter(function (v) {
      return v >= x0 && v <= x1;
    }).forEach(function (v) {
      s += '<text x="' + X(v).toFixed(1) + '" y="' + (H - padB + 16) +
        '" text-anchor="middle">' + (v / 1000) + "</text>";
    });
    s += '<text x="' + ((padL + W - padR) / 2).toFixed(1) + '" y="' + (H - 8) +
      '" text-anchor="middle">distance between basin centres, thousand km</text>';
    var el = document.getElementById("corr");
    el.setAttribute("viewBox", "0 0 " + W + " " + H);
    el.innerHTML = s;
    document.getElementById("corr-sub").textContent =
      "Moran's I " + lay.moran + ", p " + lay.moran_p;
  }

  /* ------------------------------------------------------------ the table */
  function drawStats() {
    var t = IND.layers.t, g = IND.layers.g;
    var row = function (name, a, b) {
      return "<tr><td class=\"name\">" + name + "</td><td>" + a + "</td><td>" + b + "</td></tr>";
    };
    document.getElementById("stats").innerHTML =
      row("basins with a trend", thousands(t.n), thousands(g.n)) +
      row("Moran's I, shared border", t.moran, g.moran) +
      row("Moran's I on ranks", t.moran_ranks, g.moran_ranks) +
      row("Moran's I, ice excluded", t.moran_no_ice, g.moran_no_ice) +
      row("resemblance fades by", t.e_folding_km + " km", g.e_folding_km + " km") +
      row("effective independent units", Math.round(t.n_eff), Math.round(g.n_eff)) +
      row("share of basins", (t.n_eff_share * 100).toFixed(1) + "%",
        (g.n_eff_share * 100).toFixed(1) + "%") +
      row("significant, p &lt; 0.05", thousands(t.cuts.n_raw), thousands(g.cuts.n_raw)) +
      row("significant, Benjamini-Hochberg", thousands(t.cuts.n_bh), thousands(g.cuts.n_bh)) +
      row("significant, Benjamini-Yekutieli", thousands(t.cuts.n_by), thousands(g.cuts.n_by));
    document.getElementById("stats-note").textContent =
      "Moran's I runs three ways because a few extreme basins could carry it on their own. " +
      "Ranks and the ice-free set agree with the raw field, so they do not. " +
      "c(m) is " + t.cuts.c_m.toFixed(2) + ", which is how much stricter Benjamini-Yekutieli " +
      "is than Benjamini-Hochberg at every rank.";
  }

  /* --------------------------------------------------------------- tooltip */
  var tip = document.getElementById("tip");
  mapEl.addEventListener("pointermove", function (e) {
    var p = e.target.closest(".basin");
    if (!p) { tip.style.opacity = "0"; return; }
    var b = L.basins[+p.dataset.i];
    var v = b[trendKey()], pv = b[pKey()], c = cut();
    var body = (v === null || v === undefined)
      ? '<span class="r">no value in this layer</span>'
      : '<span class="r">' + fmt(v) + " mm/yr, p " + pv.toFixed(4) + ", " +
        (pv <= c ? "passes" : "fails") + " this rule</span>";
    tip.innerHTML = "<b>" + b.region + " " + b.id + "</b>" + body +
      '<span class="r">' + b.area.toLocaleString() + " km2, " + b.nm + " mascons</span>";
    tip.style.opacity = "1";
    var r = tip.getBoundingClientRect();
    tip.style.left = Math.max(6, Math.min(e.clientX + 14, window.innerWidth - r.width - 8)) + "px";
    tip.style.top = Math.max(6, Math.min(e.clientY + 14, window.innerHeight - r.height - 8)) + "px";
  });
  mapEl.addEventListener("pointerleave", function () { tip.style.opacity = "0"; });

  /* --------------------------------------------------------------- chrome */
  function seg(id, key, after) {
    var box = document.getElementById(id);
    box.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      state[key] = btn.dataset.v;
      Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) {
        b.setAttribute("aria-pressed", String(b === btn));
      });
      after();
    });
  }
  seg("seg-product", "product", function () { paint(); drawCorrelogram(); });
  seg("seg-rule", "rule", paint);

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    buildMap();
    drawCorrelogram();
  });

  buildMap();
  drawCorrelogram();
  drawStats();
})();
