/* Against wells: the green half.

   77,556 points is far too many for the DOM, so the map is a canvas drawn from
   precomputed Robinson pixel coordinates. Picking walks a small spatial hash
   rather than a second painted canvas, because points are sparse and a colour
   index would collide at this density. */
(function () {
  "use strict";
  var G = window.GREEN;
  var N = G.px.length;
  var M = G.meta;

  var WARM = "#b5341c", COOL = "#2a78d6", NEUTRAL = "#c9c9c2";
  var RAMP_LIGHT = ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"];
  var RAMP_DARK = ["#a8501f", "#cf7434", "#d99a5f", "#3a4442", "#6fa6cc", "#3987e5", "#1a5fb4"];

  var LAYERS = {
    cover: { label: "Coverage", arr: null,
             note: "red where a well could be scored against GRACE, grey where it could not" },
    rC: { arr: G.rC, lo: -1, hi: 1, label: "correlation with the coarse solution" },
    rG: { arr: G.rG, lo: -1, hi: 1, label: "correlation with GRACE-SeDA" },
    rL: { arr: G.rL, lo: -1, hi: 1, label: "correlation with Li and Kusche" },
    dG: { arr: G.dG, lo: -0.4, hi: 0.4, label: "GRACE-SeDA minus its parent, RL06.1" },
    dL: { arr: G.dL, lo: -0.4, hi: 0.4, label: "Li and Kusche minus its parent, RL06.3" },
    aq: { arr: G.aqg, categorical: true, label: "WHYMAP aquifer class" }
  };
  var AQ_COLORS = ["#2a78d6", "#7a5aa8", "#b5341c"];
  var state = { layer: "cover", pick: -1 };

  function css(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  }
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
      return Math.round(v + (pb[i] - v) * t); }).join(",") + ")";
  }
  function colorFor(v, lo, hi) {
    var r = ramp();
    var x = Math.max(lo, Math.min(hi, v));
    var u = (x - lo) / (hi - lo) * (r.length - 1);
    var i = Math.min(r.length - 2, Math.floor(u));
    return mix(r[i], r[i + 1], u - i);
  }

  var cv = document.getElementById("map");
  var ctx = cv.getContext("2d");
  var scale = 1;
  var landPaths = G.land.map(function (d) { return new Path2D(d); });

  function sizeCanvas() {
    var w = cv.parentNode.clientWidth || 900;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pxw = Math.round(w * dpr);
    scale = pxw / G.width;
    cv.width = pxw;
    cv.height = Math.round(G.height * scale);
    cv.style.width = w + "px";
    cv.style.height = Math.round(G.height * scale / dpr) + "px";
  }

  function drawMap() {
    var spec = LAYERS[state.layer];
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = css("--sunk") || "#e8e8e4";
    for (var i = 0; i < landPaths.length; i++) ctx.fill(landPaths[i], "evenodd");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    var rad = Math.max(1.1, 1.6 * scale * (G.width / 3000));
    for (i = 0; i < N; i++) {
      var v = spec.arr ? spec.arr[i] : G.rC[i];
      var col;
      if (state.layer === "cover") {
        col = (v === null || v === undefined) ? NEUTRAL : WARM;
      } else if (v === null || v === undefined) {
        continue;
      } else if (spec.categorical) {
        col = AQ_COLORS[v] || NEUTRAL;
      } else {
        col = colorFor(v, spec.lo, spec.hi);
      }
      ctx.fillStyle = col;
      ctx.fillRect(G.px[i] * scale - rad / 2, G.py[i] * scale - rad / 2, rad, rad);
    }
    if (state.pick >= 0) {
      ctx.strokeStyle = css("--ink") || "#151513";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.arc(G.px[state.pick] * scale, G.py[state.pick] * scale, 5, 0, 6.284);
      ctx.stroke();
    }
  }

  /* ------------------------------------------------------------------ picking */
  var CELL = 12, hash = {};
  for (var i = 0; i < N; i++) {
    var k = ((G.px[i] / CELL) | 0) + "," + ((G.py[i] / CELL) | 0);
    (hash[k] || (hash[k] = [])).push(i);
  }
  function nearest(mx, my) {
    var cx = (mx / CELL) | 0, cy = (my / CELL) | 0, best = -1, bd = 1e9;
    for (var a = -1; a <= 1; a++) {
      for (var b = -1; b <= 1; b++) {
        var arr = hash[(cx + a) + "," + (cy + b)];
        if (!arr) continue;
        for (var j = 0; j < arr.length; j++) {
          var i = arr[j];
          var d = (G.px[i] - mx) * (G.px[i] - mx) + (G.py[i] - my) * (G.py[i] - my);
          if (d < bd) { bd = d; best = i; }
        }
      }
    }
    return bd < 90 ? best : -1;
  }

  function fmt(v, dp) {
    if (v === null || v === undefined || !isFinite(v)) return "n/a";
    return Number(v).toFixed(dp === undefined ? 2 : dp);
  }
  function signed(v, dp) {
    if (v === null || v === undefined || !isFinite(v)) return "n/a";
    return (v > 0 ? "+" : "") + Number(v).toFixed(dp === undefined ? 2 : dp);
  }
  function thousands(v) { return Math.round(v).toLocaleString("en-US"); }

  function pickRows(i) {
    if (i < 0) return "<tr><td class=\"name\">move over the map</td><td></td></tr>";
    var rows = [
      ["position", Math.abs(G.lat[i]).toFixed(2) + (G.lat[i] < 0 ? "S " : "N ") +
        Math.abs(G.lon[i]).toFixed(2) + (G.lon[i] < 0 ? "W" : "E")],
      ["annual values", G.ny[i]],
      ["mean precipitation, mm/yr", G.pr[i] === null ? "n/a" : thousands(G.pr[i])],
      ["mascon", G.mas[i]],
      ["r, coarse JPL", fmt(G.rC[i])],
      ["r, GRACE-SeDA", fmt(G.rG[i])],
      ["r, Li and Kusche", fmt(G.rL[i])],
      ["SeDA minus parent", signed(G.dG[i])],
      ["Li and Kusche minus parent", signed(G.dL[i])],
      ["aquifer class", (G.aqg && G.aqg[i] !== null && G.aqg[i] !== undefined)
        ? G.aq_names[G.aqg[i]] : "outside any WHYMAP polygon"]
    ];
    return rows.map(function (r) {
      return "<tr><td class=\"name\">" + r[0] + "</td><td>" + r[1] + "</td></tr>";
    }).join("");
  }

  var tip = document.getElementById("tip");
  cv.addEventListener("mousemove", function (ev) {
    var r = cv.getBoundingClientRect();
    var f = G.width / r.width;
    var i = nearest((ev.clientX - r.left) * f, (ev.clientY - r.top) * f);
    if (i !== state.pick) {
      state.pick = i;
      document.getElementById("pick").innerHTML = pickRows(i);
      drawMap();
    }
    if (i >= 0) {
      tip.innerHTML = "<b>well " + G.mas[i] + "</b><span class=\"r\">" +
        G.ny[i] + " annual values</span>";
      tip.style.opacity = 1;
      tip.style.left = Math.min(ev.clientX + 12, window.innerWidth - 240) + "px";
      tip.style.top = (ev.clientY + 14) + "px";
    } else { tip.style.opacity = 0; }
  });
  cv.addEventListener("mouseleave", function () {
    tip.style.opacity = 0; state.pick = -1;
    document.getElementById("pick").innerHTML = pickRows(-1);
    drawMap();
  });

  /* ------------------------------------------------------------------- panels */
  function drawDist() {
    var spec = LAYERS[state.layer];
    var arr = spec.arr || G.rC;
    var c = document.getElementById("dist");
    var w = c.parentNode.clientWidth || 420, h = 150;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = w * dpr; c.height = h * dpr;
    c.style.width = w + "px"; c.style.height = h + "px";
    var g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    document.getElementById("dist-sub").textContent =
      state.layer === "cover" ? "correlation with the coarse solution" : spec.label;

    if (spec.categorical) {
      var counts = [0, 0, 0], miss = 0;
      for (var q = 0; q < N; q++) {
        var c = arr[q];
        if (c === null || c === undefined) miss++; else counts[c]++;
      }
      var tot = N, y0 = 18;
      g.font = "11px 'IBM Plex Sans', sans-serif";
      (G.aq_names || []).forEach(function (nm, k) {
        g.fillStyle = AQ_COLORS[k];
        g.fillRect(6, y0 - 9, (counts[k] / tot) * (w - 12), 12);
        g.fillStyle = css("--ink-2") || "#3c3c38";
        g.fillText(nm + "  " + thousands(counts[k]), 10, y0 + 1);
        y0 += 22;
      });
      g.fillStyle = css("--muted") || "#6d6d66";
      g.fillText("outside any polygon  " + thousands(miss), 10, y0 + 1);
      return;
    }
    var lo = state.layer === "cover" ? -1 : spec.lo;
    var hi = state.layer === "cover" ? 1 : spec.hi;
    var NB = 60, pad = 26, plotW = w - pad - 6, plotH = h - 24;
    var bins = new Float64Array(NB), n = 0, sum = 0;
    for (var i = 0; i < N; i++) {
      var v = arr[i];
      if (v === null || v === undefined) continue;
      n++; sum += v;
      var b = Math.min(NB - 1, Math.max(0, Math.floor((v - lo) / (hi - lo) * NB)));
      bins[b]++;
    }
    var top = 0;
    for (i = 0; i < NB; i++) top = Math.max(top, bins[i]);
    var bw = plotW / NB;
    for (i = 0; i < NB; i++) {
      var x = pad + i * bw;
      var bh = (bins[i] / top) * plotH;
      var mid = lo + (i + 0.5) / NB * (hi - lo);
      g.fillStyle = state.layer === "cover" ? NEUTRAL : colorFor(mid, lo, hi);
      g.fillRect(x, plotH - bh, Math.max(bw - 1, 1), bh);
    }
    g.strokeStyle = css("--ink") || "#151513";
    g.setLineDash([3, 3]);
    var zx = pad + (0 - lo) / (hi - lo) * plotW;
    g.beginPath(); g.moveTo(zx, 0); g.lineTo(zx, plotH); g.stroke();
    g.setLineDash([]);
    g.fillStyle = css("--muted") || "#6d6d66";
    g.font = "10px 'IBM Plex Mono', monospace";
    g.fillText(lo.toFixed(1), pad, h - 6);
    g.textAlign = "right";
    g.fillText(hi.toFixed(1), w - 6, h - 6);
    g.textAlign = "left";
    g.fillText(thousands(n) + " wells", pad + 4, 11);
  }

  var LAB = {
    A_predictors_only: "A  weather only",
    B_plus_coarse_RL0603: "B  A + coarse RL06.3",
    B_plus_coarse_RL0601: "B  A + coarse RL06.1",
    C_plus_seda: "C  A + GRACE-SeDA",
    C_plus_liku: "C  A + Li and Kusche"
  };

  function fillTables() {
    document.getElementById("w-wells").textContent = thousands(M.n_wells);
    document.getElementById("w-mascons").textContent = M.n_mascons;
    document.getElementById("nav-window").textContent =
      "Against wells, " + M.window[0] + " to " + M.window[1];

    var names = { jpl: "JPL RL06.3, coarse", jpl61: "JPL RL06.1, coarse",
                  seda: "GRACE-SeDA", liku: "Li and Kusche" };
    document.getElementById("agree").innerHTML = Object.keys(names).map(function (k) {
      return "<tr><td class=\"name\">" + names[k] + "</td><td>" +
        fmt(M.median_r[k], 3) + "</td><td>" + thousands(M.n_scored[k]) + "</td></tr>";
    }).join("");

    var pn = { seda: "GRACE-SeDA against RL06.1", liku: "Li and Kusche against RL06.3" };
    document.getElementById("paired").innerHTML = Object.keys(pn).map(function (k) {
      var s = M.paired_against_parent[k];
      return "<tr><td class=\"name\">" + pn[k] + "</td><td>" + signed(s.median_delta_r, 3) +
        "</td><td>" + s.mascons_improved + " / " + s.n_mascons + "</td><td>" +
        fmt(s.p_value_by_mascon, 2) + "</td></tr>";
    }).join("");

    var base = "B_plus_coarse_RL0603";
    document.getElementById("ablation").innerHTML = Object.keys(LAB).map(function (k) {
      var a = M.ablation[k];
      if (!a) return "";
      var pr = M.ablation_paired_by_mascon[k + "_minus_" + base];
      var vs = pr ? signed(pr.median_delta_r2, 4) + ", " + pr.mascons_better + "/" +
        pr.n_mascons + ", p " + fmt(pr.sign_test_p, 2) : (k === base ? "reference" : "");
      return "<tr><td class=\"name\">" + LAB[k] + "</td><td>" + fmt(a.oos_r2, 4) +
        "</td><td>" + signed(a.median_well_r, 3) + "</td><td>" + vs + "</td></tr>";
    }).join("");

    var w = M.ablation_by_wetness || {};
    var dry = (w.dry_under_500mm || {}).models || {};
    var wet = (w.wet_over_500mm || {}).models || {};
    document.getElementById("wetness").innerHTML = Object.keys(LAB).filter(function (k) {
      return dry[k] || wet[k];
    }).map(function (k) {
      return "<tr><td class=\"name\">" + LAB[k] + "</td><td>" +
        (dry[k] ? fmt(dry[k].oos_r2, 4) : "n/a") + "</td><td>" +
        (wet[k] ? fmt(wet[k].oos_r2, 4) : "n/a") + "</td></tr>";
    }).join("");

    var a = M.ablation, base3 = a[base];
    document.getElementById("ablation-note").textContent =
      "Pooled skill rises from " + fmt(a.A_predictors_only.oos_r2, 3) + " to " +
      fmt(base3.oos_r2, 3) + " when the coarse GRACE term is added, so gravimetry does say " +
      "something about a well that the weather fields do not. Adding a downscaled term instead " +
      "of the coarse one moves it to " + fmt(a.C_plus_seda.oos_r2, 3) + " for GRACE-SeDA and " +
      fmt(a.C_plus_liku.oos_r2, 3) + " for Li and Kusche. Judged inside each mascon, which is " +
      "the unit that can carry a p-value here, none of those three differences is separable " +
      "from zero.";

    var scored = M.n_scored.jpl;
    document.getElementById("foot-cover").innerHTML =
      "<b>Coverage.</b> " + thousands(M.n_wells) + " wells hold at least 10 annual values " +
      "between " + M.window[0] + " and " + M.window[1] + ", and " + thousands(scored) +
      " of them could be scored against GRACE. They fall inside " + M.n_mascons +
      " mascons, so the well network is far denser than the measurement it is testing.";
    document.getElementById("foot-agree").innerHTML =
      "<b>Agreement.</b> The coarse solution tracks the median well at r " +
      fmt(M.median_r.jpl, 3) + ". GRACE-SeDA reaches " + fmt(M.median_r.seda, 3) +
      " and Li and Kusche " + fmt(M.median_r.liku, 3) + ". Paired at the same well and counted " +
      "by mascon, neither downscaled product improves on the release it was built from: " +
      signed(M.paired_against_parent.seda.median_delta_r, 3) + " for GRACE-SeDA at p " +
      fmt(M.paired_against_parent.seda.p_value_by_mascon, 2) + ", " +
      signed(M.paired_against_parent.liku.median_delta_r, 3) + " for Li and Kusche at p " +
      fmt(M.paired_against_parent.liku.p_value_by_mascon, 2) + ".";
    document.getElementById("foot-ablate").innerHTML =
      "<b>The ablation.</b> Out of sample, holding out one mascon at a time over " +
      thousands(a.A_predictors_only.n_rows) + " well-years: weather alone " +
      fmt(a.A_predictors_only.oos_r2, 3) + ", plus coarse GRACE " + fmt(base3.oos_r2, 3) +
      ", plus GRACE-SeDA " + fmt(a.C_plus_seda.oos_r2, 3) + ", plus Li and Kusche " +
      fmt(a.C_plus_liku.oos_r2, 3) + ". The finer grid buys nothing a well can see.";
  }

  function drawAquifer() {
    var by = M.by_aquifer_class || {};
    var order = ["Major groundwater basin", "Complex hydrogeological structure",
                 "Local and shallow aquifer"];
    var cols = ["A_predictors_only", "B_plus_coarse_RL0603", "C_plus_seda", "C_plus_liku"];
    var rows = order.filter(function (k) { return by[k]; }).map(function (k) {
      var v = by[k];
      return "<tr><td class=\"name\">" + k + "</td><td>" + thousands(v.n_wells) + "</td>" +
        cols.map(function (c) {
          return "<td>" + (v.models[c] ? fmt(v.models[c].oos_r2, 4) : "n/a") + "</td>";
        }).join("") + "</tr>";
    }).join("");
    document.getElementById("aquifer").innerHTML = rows;
    var mb = by["Major groundwater basin"], ls = by["Local and shallow aquifer"];
    if (mb && ls && mb.models.A_predictors_only && ls.models.A_predictors_only) {
      document.getElementById("aquifer-note").textContent =
        "Gravimetry earns its place where the aquifer is a major basin. There weather alone " +
        "reaches " + fmt(mb.models.A_predictors_only.oos_r2, 3) + " and adding the coarse GRACE " +
        "term nearly doubles it to " + fmt(mb.models.B_plus_coarse_RL0603.oos_r2, 3) +
        ". Over local and shallow aquifers weather alone already reaches " +
        fmt(ls.models.A_predictors_only.oos_r2, 3) + ", because a shallow water table answers to " +
        "rainfall directly, and GRACE adds far less. In every class the downscaled terms land on " +
        "top of the coarse one.";
    }
  }

  function syncChrome() {
    var spec = LAYERS[state.layer];
    var cover = state.layer === "cover";
    var cat = !!spec.categorical;
    document.getElementById("legend").hidden = cover || cat;
    document.getElementById("legend-cat").hidden = !cat;
    document.getElementById("map-title").textContent =
      cover ? "Where the open well records are" : "Agreement at each well";
    document.getElementById("map-sub").textContent =
      cover ? thousands(M.n_scored.jpl) + " of " + thousands(M.n_wells) + " scored"
            : spec.label;
    document.getElementById("map-note").textContent = cover
      ? "Red where a well has enough annual values and a GRACE cell to be scored, grey where "
        + "it does not. The gaps are the limit of what this page can speak for."
      : "One dot per well, colored by " + spec.label + ". Wells that could not be scored are "
        + "left off this layer.";
    document.getElementById("hint").textContent = cover
      ? "hover a well for its numbers" : "";
    if (!cover && !cat) {
      document.getElementById("ramp").style.background =
        "linear-gradient(90deg," + ramp().join(",") + ")";
      var mid = (spec.lo + spec.hi) / 2;
      document.getElementById("ticks").innerHTML =
        "<span>" + spec.lo.toFixed(1) + "</span><span>" + mid.toFixed(1) +
        "</span><span>+" + spec.hi.toFixed(1) + "</span>";
      document.getElementById("legend-note").textContent =
        state.layer.charAt(0) === "d" ? "positive means the downscaled product agrees better"
                                      : "correlation of annual anomalies";
    }
  }

  document.getElementById("seg-layer").addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    state.layer = b.dataset.v;
    [].forEach.call(this.querySelectorAll("button"), function (x) {
      x.setAttribute("aria-pressed", String(x === b));
    });
    syncChrome(); drawMap(); drawDist();
  });

  window.addEventListener("resize", function () { sizeCanvas(); drawMap(); drawDist(); });
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  if (mq.addEventListener) mq.addEventListener("change", function () {
    syncChrome(); drawMap(); drawDist();
  });

  fillTables();
  drawAquifer();
  sizeCanvas();
  syncChrome();
  drawMap();
  drawDist();
  document.getElementById("pick").innerHTML = pickRows(-1);
})();
