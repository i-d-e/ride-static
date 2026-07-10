/*
 * explore.js — interactive corpus exploration (/data/explore/).
 * See knowledge/exploration.md. Renders the facet browser (P1) and the
 * issue timeline (P3) with D3 from the inline JSON island. Filtering keeps
 * comparisons set-internal: colour encodes the criteria set, and the
 * yes-ratio axis is only meaningful within one set.
 *
 * ES module. D3 is provided as a global by the vendored classic <script>
 * loaded before this module (explore.html), so we read window.d3 rather
 * than import it — the vendored bundle is not an ES module.
 */
const d3 = window.d3;

const runExplore = (data) => {
  const reviews = data.reviews || [];
  const setLabels = data.sets || {};

  // Fixed palette per criteria set; unknown / missing set falls back to grey.
  const SET_COLOR = {
    "digital-editions-1.1": "#2563eb",
    "tools-1.0": "#d97706",
    "text-collections-1.0": "#7c3aed",
  };
  const colorOf = (slug) => SET_COLOR[slug] || "#9ca3af";
  const setName = (slug) => setLabels[slug] || slug || "no questionnaire";

  // Horizontal-axis options for the main beeswarm.
  const X_OPTIONS = [
    { key: "chars", label: "Length", fmt: (v) => Math.round(v / 1000) + "k" },
    { key: "yes_pct", label: "Yes-ratio (set-internal)", fmt: (v) => v + "%", domain: [0, 100] },
    { key: "figures", label: "Figures" },
    { key: "notes", label: "Footnotes" },
    { key: "external_refs", label: "External links" },
    { key: "resource_age", label: "Resource age (yrs)" },
  ];

  const state = {
    sets: new Set(),
    langs: new Set(),
    x: "chars",
    sortKey: "yes_pct",
    sortDir: -1,
  };

  const isActive = (d) =>
    (state.sets.size === 0 || state.sets.has(d.set_slug)) &&
    (state.langs.size === 0 || state.langs.has(d.language));
  const activeReviews = () => reviews.filter(isActive);

  const tooltip = document.getElementById("xp-tooltip");
  const showTip = (html, ev) => {
    tooltip.innerHTML = html;
    tooltip.style.opacity = "1";
    tooltip.setAttribute("aria-hidden", "false");
    moveTip(ev);
  };
  const moveTip = (ev) => {
    let x = ev.clientX + 14;
    let y = ev.clientY + 14;
    const w = tooltip.offsetWidth;
    const h = tooltip.offsetHeight;
    if (x + w > window.innerWidth) x = ev.clientX - w - 14;
    if (y + h > window.innerHeight) y = ev.clientY - h - 14;
    tooltip.style.left = x + "px";
    tooltip.style.top = y + "px";
  };
  const hideTip = () => {
    tooltip.style.opacity = "0";
    tooltip.setAttribute("aria-hidden", "true");
  };

  const tipHtml = (d) => {
    const bits = [
      "<b>" + escapeHtml(d.title || d.id) + "</b>",
      "<span class='xp-tt-meta'>" + setName(d.set_slug) + " · issue " + d.issue + " · " + (d.year || "n.d.") + " · " + (d.language || "") + "</span>",
    ];
    if (d.yes_pct != null) bits.push("yes-ratio " + d.yes_pct + "% (set-internal)");
    bits.push(Math.round((d.chars || 0) / 1000) + "k chars · " + d.figures + " fig · " + d.notes + " notes");
    if (d.resource_age != null) bits.push("reviewed resource age " + d.resource_age + " yrs");
    return bits.join("<br>");
  };
  const escapeHtml = (s) =>
    String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ── chips / facets ──────────────────────────────────────────────
  const distinct = (key) => {
    const seen = [];
    reviews.forEach((d) => { if (d[key] != null && seen.indexOf(d[key]) < 0) seen.push(d[key]); });
    return seen;
  };

  const buildChips = () => {
    buildFacet("set_slug", distinct("set_slug"), state.sets, true);
    buildFacet("language", distinct("language").sort(), state.langs, false);
    buildAxisChips();
  };

  const buildFacet = (key, values, store, withDot) => {
    const host = document.querySelector('[data-chips="' + key + '"]');
    if (!host) return;
    host.innerHTML = "";
    values.forEach((v) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "xp-chip";
      btn.setAttribute("aria-pressed", store.has(v) ? "true" : "false");
      const n = reviews.filter((d) => d[key] === v).length;
      const dot = withDot ? '<span class="xp-chip__dot" style="background:' + colorOf(v) + '"></span>' : "";
      const label = key === "set_slug" ? setName(v) : v;
      btn.innerHTML = dot + '<span class="xp-chip__label">' + escapeHtml(label) +
        '</span><span class="xp-chip__n">' + n + "</span>";
      btn.addEventListener("click", () => {
        if (store.has(v)) store.delete(v); else store.add(v);
        btn.setAttribute("aria-pressed", store.has(v) ? "true" : "false");
        update();
      });
      host.appendChild(btn);
    });
  };

  const buildAxisChips = () => {
    const host = document.querySelector('[data-chips="x"]');
    if (!host) return;
    host.innerHTML = "";
    X_OPTIONS.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "xp-chip";
      btn.innerHTML = '<span class="xp-chip__label">' + escapeHtml(opt.label) + "</span>";
      btn.setAttribute("aria-pressed", state.x === opt.key ? "true" : "false");
      btn.addEventListener("click", () => {
        state.x = opt.key;
        host.querySelectorAll(".xp-chip").forEach((b) => b.setAttribute("aria-pressed", "false"));
        btn.setAttribute("aria-pressed", "true");
        renderBeeswarm();
      });
      host.appendChild(btn);
    });
  };

  // ── main beeswarm (P1) ──────────────────────────────────────────
  const W = 920, H = 384, M = { top: 16, right: 24, bottom: 60, left: 24 };
  const swarm = d3.select("#xp-beeswarm").attr("viewBox", "0 0 " + W + " " + H);
  const swarmAxis = swarm.append("g").attr("class", "xp-axis").attr("transform", "translate(0," + (H - M.bottom) + ")");
  const swarmAxisTitle = swarm.append("text").attr("class", "xp-axis-title").attr("x", W / 2).attr("y", H - 18).attr("text-anchor", "middle");
  const swarmAxisSub = swarm.append("text").attr("class", "xp-axis-sub").attr("x", W / 2).attr("y", H - 3).attr("text-anchor", "middle");
  const swarmDots = swarm.append("g");
  let sim = null;

  const xOption = () => X_OPTIONS.find((o) => o.key === state.x) || X_OPTIONS[0];

  const renderBeeswarm = () => {
    const opt = xOption();
    const vals = reviews.map((d) => d[opt.key]).filter((v) => v != null);
    const domain = opt.domain || [0, d3.max(vals) || 1];
    const x = d3.scaleLinear().domain(domain).nice(opt.domain ? false : true).range([M.left, W - M.right]);
    const r = d3.scaleSqrt().domain([0, d3.max(reviews, (d) => d.figures + d.notes) || 1]).range([4, 11]);

    swarmAxis.transition().duration(500).call(d3.axisBottom(x).ticks(6).tickFormat(opt.fmt || null));
    swarmAxisTitle.text(opt.label);
    swarmAxisSub.text(opt.key === "yes_pct" ? "comparable within one criteria set only" : "");

    reviews.forEach((d) => { d._tx = x(d[opt.key] != null ? d[opt.key] : domain[0]); d._r = r(d.figures + d.notes); });

    const sel = swarmDots.selectAll("circle").data(reviews, (d) => d.id);
    sel.exit().remove();
    const ent = sel.enter().append("circle")
      .attr("class", "xp-dot")
      .attr("cx", (d) => d._tx)
      .attr("cy", H / 2)
      .attr("fill", (d) => colorOf(d.set_slug))
      .attr("stroke", "#fff").attr("stroke-width", .6)
      .on("mousemove", (ev, d) => showTip(tipHtml(d), ev))
      .on("mouseleave", hideTip)
      .on("click", (ev, d) => { if (d.url) window.location.href = d.url; });
    ent.append("title").text((d) => d.title);
    const all = ent.merge(sel);
    all.attr("r", (d) => d._r).attr("fill", (d) => colorOf(d.set_slug));

    if (sim) sim.stop();
    sim = d3.forceSimulation(reviews)
      .force("x", d3.forceX((d) => d._tx).strength(.95))
      .force("y", d3.forceY(H / 2).strength(.06))
      .force("collide", d3.forceCollide((d) => d._r + 1.2))
      .alpha(.9).alphaDecay(.045)
      .on("tick", () => all.attr("cx", (d) => d.x).attr("cy", (d) => d.y));
    applyDim();
  };

  const applyDim = () => {
    swarmDots.selectAll("circle").classed("dimmed", (d) => !isActive(d));
  };

  // ── timeline (P3) ───────────────────────────────────────────────
  const TW = 920, TH = 240, TM = { top: 14, right: 24, bottom: 36, left: 24 };
  const tl = d3.select("#xp-timeline").attr("viewBox", "0 0 " + TW + " " + TH);
  const tlAxis = tl.append("g").attr("transform", "translate(0," + (TH - TM.bottom) + ")");
  const tlDots = tl.append("g");
  let tlSim = null;

  const renderTimeline = () => {
    const years = reviews.map((d) => d.year).filter(Boolean);
    const x = d3.scaleLinear().domain([d3.min(years) - 1, d3.max(years) + 1]).range([TM.left, TW - TM.right]);
    tlAxis.call(d3.axisBottom(x).ticks(8).tickFormat(d3.format("d")));
    reviews.forEach((d) => { d._tlx = x(d.year || d3.min(years)); });

    const sel = tlDots.selectAll("circle").data(reviews, (d) => d.id);
    sel.exit().remove();
    const ent = sel.enter().append("circle")
      .attr("class", "xp-dot").attr("r", 5)
      .attr("cx", (d) => d._tlx).attr("cy", TH / 2)
      .attr("fill", (d) => colorOf(d.set_slug))
      .attr("stroke", "#fff").attr("stroke-width", .6)
      .on("mousemove", (ev, d) => showTip(tipHtml(d), ev))
      .on("mouseleave", hideTip)
      .on("click", (ev, d) => { if (d.url) window.location.href = d.url; });
    const all = ent.merge(sel);

    if (tlSim) tlSim.stop();
    tlSim = d3.forceSimulation(reviews)
      .force("x", d3.forceX((d) => d._tlx).strength(1))
      .force("y", d3.forceY(TH / 2).strength(.05))
      .force("collide", d3.forceCollide(6))
      .alpha(.9).alphaDecay(.05)
      .on("tick", () => all.attr("cx", (d) => d.x).attr("cy", (d) => d.y));
    all.classed("dimmed", (d) => !isActive(d));
  };

  // ── table ───────────────────────────────────────────────────────
  const COLS = [
    { key: "title", label: "Review", kind: "link" },
    { key: "issue", label: "Iss", kind: "num" },
    { key: "year", label: "Year", kind: "num" },
    { key: "language", label: "Lang" },
    { key: "set_slug", label: "Set", kind: "set" },
    { key: "yes_pct", label: "Yes %", kind: "num" },
    { key: "chars", label: "Chars", kind: "num" },
    { key: "figures", label: "Fig", kind: "num" },
    { key: "notes", label: "Notes", kind: "num" },
    { key: "external_refs", label: "Links", kind: "num" },
  ];

  const buildHead = () => {
    // The template ships an empty <thead> (a <tr> without cells is
    // invalid HTML); the full header row is built here.
    const thead = document.getElementById("xp-thead");
    const tr = document.createElement("tr");
    COLS.forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c.label;
      if (c.key === "yes_pct") {
        const info = document.createElement("span");
        info.className = "xp-info";
        info.textContent = " ⓘ";
        info.title = "Set-relative — sort and compare within one criteria set only.";
        th.appendChild(info);
      }
      if (state.sortKey === c.key) th.setAttribute("aria-sort", state.sortDir < 0 ? "descending" : "ascending");
      th.addEventListener("click", () => {
        if (state.sortKey === c.key) state.sortDir *= -1; else { state.sortKey = c.key; state.sortDir = -1; }
        renderTable(); buildHead();
      });
      tr.appendChild(th);
    });
    thead.replaceChildren(tr);
  };

  const renderTable = () => {
    const rows = activeReviews().slice().sort((a, b) => {
      const av = a[state.sortKey], bv = b[state.sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string") return state.sortDir * av.localeCompare(bv);
      return state.sortDir * (av - bv);
    });
    const tb = document.getElementById("xp-tbody");
    tb.innerHTML = "";
    rows.forEach((d) => {
      const tr = document.createElement("tr");
      COLS.forEach((c) => {
        const td = document.createElement("td");
        if (c.kind === "num") td.className = "num";
        if (c.kind === "link") {
          td.className = "xp-td-title";
          const a = document.createElement("a");
          a.href = d.url; a.textContent = d.title || d.id; a.title = d.title || d.id;
          td.appendChild(a);
        } else if (c.kind === "set") {
          const pill = document.createElement("span");
          pill.className = "xp-pill";
          pill.style.background = colorOf(d.set_slug);
          pill.textContent = (d.set_slug || "—").replace(/-1\.[01]$/, "");
          td.appendChild(pill);
        } else {
          const v = d[c.key];
          td.textContent = c.key === "chars" && v != null ? Math.round(v / 1000) + "k" : (v == null ? "—" : v);
        }
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
  };

  // ── update orchestration ────────────────────────────────────────
  const update = () => {
    document.getElementById("xp-n").textContent = activeReviews().length;
    applyDim();
    tlDots.selectAll("circle").classed("dimmed", (d) => !isActive(d));
    renderTable();
  };

  document.getElementById("xp-reset").addEventListener("click", () => {
    state.sets.clear(); state.langs.clear();
    buildChips();
    update();
  });
  if (tooltip) document.addEventListener("scroll", hideTip, true);

  // ── init ────────────────────────────────────────────────────────
  document.getElementById("xp-total").textContent = reviews.length;
  buildChips();
  buildHead();
  renderBeeswarm();
  renderTimeline();
  renderTable();
  update();
};

const island = document.getElementById("ride-explore-data");
if (d3 && island) runExplore(JSON.parse(island.textContent));
