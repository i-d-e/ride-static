/*
 * explore.js — interactive corpus exploration (/data/explore/).
 * See knowledge/exploration.md. Renders the facet browser (P1) and the
 * issue timeline (P3) with D3 from the inline JSON island. Filtering keeps
 * comparisons set-internal: colour encodes the criteria set, and the
 * yes-ratio axis is only meaningful within one set.
 */
(function () {
  "use strict";
  var d3 = window.d3;
  var island = document.getElementById("ride-explore-data");
  if (!d3 || !island) return;

  var data = JSON.parse(island.textContent);
  var reviews = data.reviews || [];
  var setLabels = data.sets || {};

  // Fixed palette per criteria set; unknown / missing set falls back to grey.
  var SET_COLOR = {
    "digital-editions-1.1": "#2563eb",
    "tools-1.0": "#d97706",
    "text-collections-1.0": "#7c3aed"
  };
  function colorOf(slug) { return SET_COLOR[slug] || "#9ca3af"; }
  function setName(slug) { return setLabels[slug] || (slug || "no questionnaire"); }

  // Horizontal-axis options for the main beeswarm.
  var X_OPTIONS = [
    { key: "chars", label: "Length", fmt: function (v) { return Math.round(v / 1000) + "k"; } },
    { key: "yes_pct", label: "Yes-ratio (set-internal)", fmt: function (v) { return v + "%"; }, domain: [0, 100] },
    { key: "figures", label: "Figures" },
    { key: "notes", label: "Footnotes" },
    { key: "external_refs", label: "External links" },
    { key: "resource_age", label: "Resource age (yrs)" }
  ];

  var state = {
    sets: new Set(),
    langs: new Set(),
    x: "chars",
    sortKey: "yes_pct",
    sortDir: -1
  };

  function isActive(d) {
    return (state.sets.size === 0 || state.sets.has(d.set_slug)) &&
           (state.langs.size === 0 || state.langs.has(d.language));
  }
  function activeReviews() { return reviews.filter(isActive); }

  var tooltip = document.getElementById("xp-tooltip");
  function showTip(html, ev) {
    tooltip.innerHTML = html;
    tooltip.style.opacity = "1";
    tooltip.setAttribute("aria-hidden", "false");
    moveTip(ev);
  }
  function moveTip(ev) {
    var x = ev.clientX + 14, y = ev.clientY + 14;
    var w = tooltip.offsetWidth, h = tooltip.offsetHeight;
    if (x + w > window.innerWidth) x = ev.clientX - w - 14;
    if (y + h > window.innerHeight) y = ev.clientY - h - 14;
    tooltip.style.left = x + "px";
    tooltip.style.top = y + "px";
  }
  function hideTip() { tooltip.style.opacity = "0"; tooltip.setAttribute("aria-hidden", "true"); }

  function tipHtml(d) {
    var bits = [
      "<b>" + escapeHtml(d.title || d.id) + "</b>",
      "<span class='xp-tt-meta'>" + setName(d.set_slug) + " · issue " + d.issue + " · " + (d.year || "n.d.") + " · " + (d.language || "") + "</span>"
    ];
    if (d.yes_pct != null) bits.push("yes-ratio " + d.yes_pct + "% (set-internal)");
    bits.push(Math.round((d.chars || 0) / 1000) + "k chars · " + d.figures + " fig · " + d.notes + " notes");
    if (d.resource_age != null) bits.push("reviewed resource age " + d.resource_age + " yrs");
    return bits.join("<br>");
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ── chips / facets ──────────────────────────────────────────────
  function distinct(key) {
    var seen = [];
    reviews.forEach(function (d) { if (d[key] != null && seen.indexOf(d[key]) < 0) seen.push(d[key]); });
    return seen;
  }

  function buildChips() {
    buildFacet("set_slug", distinct("set_slug"), state.sets, true);
    buildFacet("language", distinct("language").sort(), state.langs, false);
    buildAxisChips();
  }

  function buildFacet(key, values, store, withDot) {
    var host = document.querySelector('[data-chips="' + key + '"]');
    if (!host) return;
    host.innerHTML = "";
    values.forEach(function (v) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "xp-chip";
      btn.setAttribute("aria-pressed", store.has(v) ? "true" : "false");
      var n = reviews.filter(function (d) { return d[key] === v; }).length;
      var dot = withDot ? '<span class="xp-chip__dot" style="background:' + colorOf(v) + '"></span>' : "";
      var label = key === "set_slug" ? setName(v) : v;
      btn.innerHTML = dot + '<span class="xp-chip__label">' + escapeHtml(label) +
        '</span><span class="xp-chip__n">' + n + "</span>";
      btn.addEventListener("click", function () {
        if (store.has(v)) store.delete(v); else store.add(v);
        btn.setAttribute("aria-pressed", store.has(v) ? "true" : "false");
        update();
      });
      host.appendChild(btn);
    });
  }

  function buildAxisChips() {
    var host = document.querySelector('[data-chips="x"]');
    if (!host) return;
    host.innerHTML = "";
    X_OPTIONS.forEach(function (opt) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "xp-chip";
      btn.innerHTML = '<span class="xp-chip__label">' + escapeHtml(opt.label) + "</span>";
      btn.setAttribute("aria-pressed", state.x === opt.key ? "true" : "false");
      btn.addEventListener("click", function () {
        state.x = opt.key;
        host.querySelectorAll(".xp-chip").forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
        btn.setAttribute("aria-pressed", "true");
        renderBeeswarm();
      });
      host.appendChild(btn);
    });
  }

  // ── main beeswarm (P1) ──────────────────────────────────────────
  var W = 920, H = 384, M = { top: 16, right: 24, bottom: 60, left: 24 };
  var swarm = d3.select("#xp-beeswarm").attr("viewBox", "0 0 " + W + " " + H);
  var swarmAxis = swarm.append("g").attr("class", "xp-axis").attr("transform", "translate(0," + (H - M.bottom) + ")");
  var swarmAxisTitle = swarm.append("text").attr("class", "xp-axis-title").attr("x", W / 2).attr("y", H - 18).attr("text-anchor", "middle");
  var swarmAxisSub = swarm.append("text").attr("class", "xp-axis-sub").attr("x", W / 2).attr("y", H - 3).attr("text-anchor", "middle");
  var swarmDots = swarm.append("g");
  var sim = null;

  function xOption() { return X_OPTIONS.find(function (o) { return o.key === state.x; }) || X_OPTIONS[0]; }

  function renderBeeswarm() {
    var opt = xOption();
    var vals = reviews.map(function (d) { return d[opt.key]; }).filter(function (v) { return v != null; });
    var domain = opt.domain || [0, d3.max(vals) || 1];
    var x = d3.scaleLinear().domain(domain).nice(opt.domain ? false : true).range([M.left, W - M.right]);
    var r = d3.scaleSqrt().domain([0, d3.max(reviews, function (d) { return d.figures + d.notes; }) || 1]).range([4, 11]);

    swarmAxis.transition().duration(500).call(d3.axisBottom(x).ticks(6).tickFormat(opt.fmt || null));
    swarmAxisTitle.text(opt.label);
    swarmAxisSub.text(opt.key === "yes_pct" ? "comparable within one criteria set only" : "");

    reviews.forEach(function (d) { d._tx = x(d[opt.key] != null ? d[opt.key] : domain[0]); d._r = r(d.figures + d.notes); });

    var sel = swarmDots.selectAll("circle").data(reviews, function (d) { return d.id; });
    sel.exit().remove();
    var ent = sel.enter().append("circle")
      .attr("class", "xp-dot")
      .attr("cx", function (d) { return d._tx; })
      .attr("cy", H / 2)
      .attr("fill", function (d) { return colorOf(d.set_slug); })
      .attr("stroke", "#fff").attr("stroke-width", .6)
      .on("mousemove", function (ev, d) { showTip(tipHtml(d), ev); })
      .on("mouseleave", hideTip)
      .on("click", function (ev, d) { if (d.url) window.location.href = d.url; });
    ent.append("title").text(function (d) { return d.title; });
    var all = ent.merge(sel);
    all.attr("r", function (d) { return d._r; }).attr("fill", function (d) { return colorOf(d.set_slug); });

    if (sim) sim.stop();
    sim = d3.forceSimulation(reviews)
      .force("x", d3.forceX(function (d) { return d._tx; }).strength(.95))
      .force("y", d3.forceY(H / 2).strength(.06))
      .force("collide", d3.forceCollide(function (d) { return d._r + 1.2; }))
      .alpha(.9).alphaDecay(.045)
      .on("tick", function () { all.attr("cx", function (d) { return d.x; }).attr("cy", function (d) { return d.y; }); });
    applyDim();
  }

  function applyDim() {
    swarmDots.selectAll("circle").classed("dimmed", function (d) { return !isActive(d); });
  }

  // ── timeline (P3) ───────────────────────────────────────────────
  var TW = 920, TH = 240, TM = { top: 14, right: 24, bottom: 36, left: 24 };
  var tl = d3.select("#xp-timeline").attr("viewBox", "0 0 " + TW + " " + TH);
  var tlAxis = tl.append("g").attr("transform", "translate(0," + (TH - TM.bottom) + ")");
  var tlDots = tl.append("g");
  var tlSim = null;

  function renderTimeline() {
    var years = reviews.map(function (d) { return d.year; }).filter(Boolean);
    var x = d3.scaleLinear().domain([d3.min(years) - 1, d3.max(years) + 1]).range([TM.left, TW - TM.right]);
    tlAxis.call(d3.axisBottom(x).ticks(8).tickFormat(d3.format("d")));
    reviews.forEach(function (d) { d._tlx = x(d.year || d3.min(years)); });

    var sel = tlDots.selectAll("circle").data(reviews, function (d) { return d.id; });
    sel.exit().remove();
    var ent = sel.enter().append("circle")
      .attr("class", "xp-dot").attr("r", 5)
      .attr("cx", function (d) { return d._tlx; }).attr("cy", TH / 2)
      .attr("fill", function (d) { return colorOf(d.set_slug); })
      .attr("stroke", "#fff").attr("stroke-width", .6)
      .on("mousemove", function (ev, d) { showTip(tipHtml(d), ev); })
      .on("mouseleave", hideTip)
      .on("click", function (ev, d) { if (d.url) window.location.href = d.url; });
    var all = ent.merge(sel);

    if (tlSim) tlSim.stop();
    tlSim = d3.forceSimulation(reviews)
      .force("x", d3.forceX(function (d) { return d._tlx; }).strength(1))
      .force("y", d3.forceY(TH / 2).strength(.05))
      .force("collide", d3.forceCollide(6))
      .alpha(.9).alphaDecay(.05)
      .on("tick", function () { all.attr("cx", function (d) { return d.x; }).attr("cy", function (d) { return d.y; }); });
    all.classed("dimmed", function (d) { return !isActive(d); });
  }

  // ── table ───────────────────────────────────────────────────────
  var COLS = [
    { key: "title", label: "Review", kind: "link" },
    { key: "issue", label: "Iss", kind: "num" },
    { key: "year", label: "Year", kind: "num" },
    { key: "language", label: "Lang" },
    { key: "set_slug", label: "Set", kind: "set" },
    { key: "yes_pct", label: "Yes %", kind: "num" },
    { key: "chars", label: "Chars", kind: "num" },
    { key: "figures", label: "Fig", kind: "num" },
    { key: "notes", label: "Notes", kind: "num" },
    { key: "external_refs", label: "Links", kind: "num" }
  ];

  function buildHead() {
    var tr = document.getElementById("xp-thead");
    tr.innerHTML = "";
    COLS.forEach(function (c) {
      var th = document.createElement("th");
      th.textContent = c.label;
      if (c.key === "yes_pct") {
        var info = document.createElement("span");
        info.className = "xp-info";
        info.textContent = " ⓘ";
        info.title = "Set-relative — sort and compare within one criteria set only.";
        th.appendChild(info);
      }
      if (state.sortKey === c.key) th.setAttribute("aria-sort", state.sortDir < 0 ? "descending" : "ascending");
      th.addEventListener("click", function () {
        if (state.sortKey === c.key) state.sortDir *= -1; else { state.sortKey = c.key; state.sortDir = -1; }
        renderTable(); buildHead();
      });
      tr.appendChild(th);
    });
  }

  function renderTable() {
    var rows = activeReviews().slice().sort(function (a, b) {
      var av = a[state.sortKey], bv = b[state.sortKey];
      if (av == null) return 1; if (bv == null) return -1;
      if (typeof av === "string") return state.sortDir * av.localeCompare(bv);
      return state.sortDir * (av - bv);
    });
    var tb = document.getElementById("xp-tbody");
    tb.innerHTML = "";
    rows.forEach(function (d) {
      var tr = document.createElement("tr");
      COLS.forEach(function (c) {
        var td = document.createElement("td");
        if (c.kind === "num") td.className = "num";
        if (c.kind === "link") {
          td.className = "xp-td-title";
          var a = document.createElement("a");
          a.href = d.url; a.textContent = d.title || d.id; a.title = d.title || d.id;
          td.appendChild(a);
        } else if (c.kind === "set") {
          var pill = document.createElement("span");
          pill.className = "xp-pill";
          pill.style.background = colorOf(d.set_slug);
          pill.textContent = (d.set_slug || "—").replace(/-1\.[01]$/, "");
          td.appendChild(pill);
        } else {
          var v = d[c.key];
          td.textContent = c.key === "chars" && v != null ? Math.round(v / 1000) + "k" : (v == null ? "—" : v);
        }
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
  }

  // ── update orchestration ────────────────────────────────────────
  function update() {
    document.getElementById("xp-n").textContent = activeReviews().length;
    applyDim();
    tlDots.selectAll("circle").classed("dimmed", function (d) { return !isActive(d); });
    renderTable();
  }

  document.getElementById("xp-reset").addEventListener("click", function () {
    state.sets.clear(); state.langs.clear();
    buildChips();
    update();
  });
  tooltip && document.addEventListener("scroll", hideTip, true);

  // ── init ────────────────────────────────────────────────────────
  document.getElementById("xp-total").textContent = reviews.length;
  buildChips();
  buildHead();
  renderBeeswarm();
  renderTimeline();
  renderTable();
  update();
})();
