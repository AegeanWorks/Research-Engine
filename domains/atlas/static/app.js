/* Atlas workspace: canvas + graph share ONE analysis model. No silent divergence. */
const $ = (id) => document.getElementById(id);
let state = { figure: null, analysis: null, zoom: 1, selected: null, category: "" };

function visibleEntities() {
  if (!state.analysis) return [];
  if (!state.category) return state.analysis.entities;
  return state.analysis.entities.filter((e) => e.category === state.category);
}

// Busy state for slow calls: disables the button and labels it, so users
// never fire duplicate Muse/SAM requests while one is in flight.
async function withBusy(btn, label, fn) {
  if (!btn || btn.disabled) return;
  const old = btn.textContent;
  btn.disabled = true;
  btn.textContent = label || "Working…";
  try {
    return await fn();
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

async function api(path, body) {
  const r = await fetch(path, { method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(data.error || r.statusText);
    err.cause = data.cause; err.fix = data.fix;
    throw err;
  }
  return data;
}

// Demo-proof download: the browser-only demo fixture has no server-side
// figure_id, so its artifact links POST the loaded model inline and save the
// returned bytes. Server-saved models keep their plain GET hrefs.
async function demoDownload(url, format) {
  const box = $("summary");
  try {
    const r = await fetch(url, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis: state.analysis, format }) });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.error || r.statusText);
    }
    const blob = await r.blob();
    const disp = r.headers.get("Content-Disposition") || "";
    const name = (/filename="([^"]+)"/.exec(disp) || [])[1]
      || url.split("?")[0].split("/").pop() || "atlas-download";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  } catch (err) { box.textContent = `Download failed: ${honestMsg(err)}`; }
}

async function refreshHealth() {
  try {
    const h = await api("/api/health");
    $("status").textContent =
      `Muse ${h.config.muse_model} · SAM ${h.config.sam_model} · Atlas standalone`;
  } catch (e) { $("status").textContent = "backend unreachable — start: python -m atlas.app"; }
}

function svgEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function renderAll() {
  renderFilter(); renderOverlay(); renderList(); renderGraph();
  const fid = state.figureId || "workspace-figure";
  $("download-obj").href = `/api/model3d?figure_id=${encodeURIComponent(fid)}&format=obj`;
  $("anki-link").href = `/api/flashcards/export?figure_id=${encodeURIComponent(fid)}`;
  $("link-diagram-svg").href = `/api/diagram?figure_id=${encodeURIComponent(fid)}&format=svg`;
  $("link-diagram-png").href = `/api/diagram?figure_id=${encodeURIComponent(fid)}&format=png`;
  $("link-podcast").href = `/api/podcast?figure_id=${encodeURIComponent(fid)}&format=md`;
  $("link-questions").href = `/api/questions?figure_id=${encodeURIComponent(fid)}&format=md`;
  // Browser-only demo fixture ("demo") has no server-side figure_id, so plain
  // GET downloads would 404: POST the loaded model inline and save the blob.
  const demoOnly = state.analysis && state.figureId === "demo";
  for (const [id, fmt] of [["download-obj", "obj"], ["anki-link", "tsv"],
      ["link-diagram-svg", "svg"], ["link-diagram-png", "png"],
      ["link-podcast", "md"], ["link-questions", "md"]]) {
    $(id).onclick = demoOnly ? (e) => { e.preventDefault(); demoDownload($(id).href, fmt); } : null;
  }
  $("link-video").onclick = (e) => withBusy($("link-video"), "Rendering…", async () => {
    e.preventDefault();
    const box = $("summary"); box.textContent = "Rendering study video (title, spotlights, recap)…";
    try {
      const v = await api("/api/video", state.analysis
        ? { figure_id: fid, analysis: state.analysis }
        : { figure_id: fid });
      box.innerHTML = "";
      box.appendChild(packEl("div", "pack-title", "Study video ready"));
      const stats = packEl("div", "pack-stats");
      stats.appendChild(packEl("span", "chip", `${v.scenes} scenes`));
      stats.appendChild(packEl("span", "chip", `${v.duration_s}s`));
      stats.appendChild(packEl("span", "chip", `${v.fps}fps`));
      box.appendChild(stats);
      const a = document.createElement("a");
      a.href = v.mp4_url; a.textContent = "Download study MP4 ↓";
      box.appendChild(a);
    } catch (err) { box.textContent = `Video failed: ${honestMsg(err)}`; }
  });
}

$("btn-quality").onclick = () => withBusy($("btn-quality"), "Scoring…", async () => {
  const box = $("summary"); box.textContent = "Scoring flashcards, podcast, infographic, 3D model, tour, questions, summary, learn…";
  try {
    // Inline analysis: scores the model on screen even when it only lives in
    // the browser (demo fixture), not just server-saved figure_ids.
    const q = await api("/api/quality", { analysis: state.analysis });
    box.innerHTML = "";
    renderQualityInto(box, q);
  } catch (err) { box.textContent = `Quality check failed: ${honestMsg(err)}`; }
});

$("btn-tour").onclick = async () => {
  const box = $("summary"); box.textContent = "Planning 3D tour…";
  try {
    // Browser-only demo fixture has no server-side figure_id: send the loaded
    // model inline so the tour never 404s on the demo (study-all parity).
    const t = state.analysis
      ? await api("/api/tour", { analysis: state.analysis })
      : await api(`/api/tour?figure_id=${encodeURIComponent(state.figureId || "workspace-figure")}`);
    box.innerHTML = "";
    renderTourInto(box, t);
  } catch (err) { box.textContent = `Tour failed: ${honestMsg(err)}`; }
};

function resetModelView() {
  state.iso = false; state.isoData = null;
  $("toggle-3d").textContent = "3D";
  $("layer-wrap").style.display = "none";
  quiz = null; $("quiz-box").innerHTML = "";
  $("toggle-labels").checked = true;
  state.learnHi = null;
  deck = { cards: [], i: 0, know: 0, seen: 0 };
  showCard();
}

function toPct(b) { return { x: b.x_min * 100, y: b.y_min * 100, w: (b.x_max - b.x_min) * 100, h: (b.y_max - b.y_min) * 100 }; }

// Overlay must sit exactly over the centered image, not the viewport
// top-left: #viewport is flex-start with img margin:auto (centered when small,
// scrollable when large), so the image still has a real offset.
function alignOverlay(svg, img) {
  svg.style.width = img.clientWidth + "px"; svg.style.height = img.clientHeight + "px";
  svg.style.left = img.offsetLeft + "px"; svg.style.top = img.offsetTop + "px";
}

function renderOverlay() {
  const svg = $("overlay"); svg.innerHTML = "";
  if (state.iso && state.isoData) return renderIso(svg);
  if (quiz && quiz.challenge && quiz.challenge.highlight_bbox) {
    // Quiz mode: exactly one highlighted region, no labels, no other boxes.
    svg.setAttribute("viewBox", "0 0 100 100");
    const img = $("figure");
    alignOverlay(svg, img);
    const p = toPct(quiz.challenge.highlight_bbox);
    svg.appendChild(svgEl("rect", { x: p.x, y: p.y, width: p.w, height: p.h,
      fill: "rgba(34,211,238,.28)", stroke: "#22d3ee", "stroke-width": .8 }));
    return;
  }
  if (state.learnHi) {
    // Learn-mode spatial recall: same single-highlight treatment as the quiz.
    svg.setAttribute("viewBox", "0 0 100 100");
    const img = $("figure");
    alignOverlay(svg, img);
    const p = toPct(state.learnHi);
    svg.appendChild(svgEl("rect", { x: p.x, y: p.y, width: p.w, height: p.h,
      fill: "rgba(34,211,238,.28)", stroke: "#22d3ee", "stroke-width": .8 }));
    return;
  }
  const img = $("figure");
  if (!state.analysis || !img.naturalWidth) return;
  const showLabels = $("toggle-labels").checked, showBoxes = $("toggle-masks").checked;
  svg.setAttribute("viewBox", `0 0 100 100`);
  alignOverlay(svg, img);
  for (const e of visibleEntities()) {
    if (e.mask_ref && typeof e.mask_ref === "string" && e.mask_ref.startsWith("/")) {
      // Full-crop mask overlay (mask assumed to match the analyzed crop's frame).
      const im = svgEl("image", { x: 0, y: 0, width: 100, height: 100, opacity: showBoxes ? .5 : 0 });
      im.setAttribute("href", e.mask_ref);
      svg.appendChild(im);
    }
    if (!e.bbox) continue;
    const p = toPct(e.bbox);
    const g = svgEl("g", { class: "hit" });
    if (showBoxes) {
      const r = svgEl("rect", { x: p.x, y: p.y, width: p.w, height: p.h,
        fill: e.id === state.selected ? "rgba(34,211,238,.28)" : "rgba(139,92,246,.28)",
        stroke: e.id === state.selected ? "#22d3ee" : "#a78bfa", "stroke-width": e.id === state.selected ? .8 : .9,
        class: e.id === state.selected ? "active" : "" });
      r.addEventListener("click", () => select(e.id));
      g.appendChild(r);
    }
    if (showLabels) {
      const t = svgEl("text", { x: p.x, y: Math.max(2, p.y - 0.8), "font-size": 2.6, fill: "#eaf2ff" });
      t.textContent = e.name;
      t.addEventListener("click", () => select(e.id));
      g.appendChild(t);
    }
    svg.appendChild(g);
  }
}

function renderIso(svg) {
  // 2.5D stacked view: layer order = category depth, top faces face the reader.
  // Auto-fit: static frames clip dense stacks (Thalamus-only shot), so fit the
  // data bounding box with padding instead of a fixed frame.
  let vb = "-1 -1.1 2 2.3";
  try {
    const pts = [];
    for (const p of (state.isoData.polygons || [])) {
      if (state.category && p.category !== state.category) continue;
      if (p.layer > Number($("layer").value)) continue;
      for (const q of (p.top || []).concat(p.base || [])) pts.push(q);
    }
    if (pts.length) {
      const xs = pts.map((q) => q[0]), ys = pts.map((q) => q[1]);
      const x0 = Math.min(...xs) - .12, x1 = Math.max(...xs) + .12;
      const y0 = Math.min(...ys) - .14, y1 = Math.max(...ys) + .14;
      vb = `${x0} ${y0} ${Math.max(x1 - x0, .2)} ${Math.max(y1 - y0, .2)}`;
    }
  } catch (e) { /* keep static frame */ }
  svg.setAttribute("viewBox", vb);
  alignOverlay(svg, $("figure"));
  $("layer-wrap").style.display = "inline";
  const maxLayer = Number($("layer").value);
  for (const p of state.isoData.polygons) {
    if (state.category && p.category !== state.category) continue;
    if (p.layer > maxLayer) continue;
    const base = svgEl("polygon", { points: p.base.map((q) => q.join(",")).join(" "),
      fill: "rgba(139,92,246,.12)", stroke: "#3b548c", "stroke-width": .01 });
    const top = svgEl("polygon", { points: p.top.map((q) => q.join(",")).join(" "),
      fill: p.id === state.selected ? "rgba(34,211,238,.45)" : "rgba(34,211,238,.20)",
      stroke: p.id === state.selected ? "#22d3ee" : "#8b5cf6", "stroke-width": .015,
      class: "hit" });
    top.addEventListener("click", () => select(p.id));
    const c = p.top.reduce((a, q) => [a[0] + q[0] / 4, a[1] + q[1] / 4], [0, 0]);
    // Labels ride above the top face (not inside the cuboid) at a smaller
    // size, so stacked neighbours stay readable instead of overlapping.
    const t = svgEl("text", { x: c[0], y: c[1] - .045, "font-size": .05, fill: "#eaf2ff",
      "text-anchor": "middle", class: "iso-label" });
    t.textContent = p.name;
    t.addEventListener("click", () => select(p.id));
    svg.appendChild(base); svg.appendChild(top); svg.appendChild(t);
  }
}

$("toggle-3d").onclick = async () => {
  state.iso = !state.iso;
  $("toggle-3d").textContent = state.iso ? "2D" : "3D";
  $("layer-wrap").style.display = state.iso ? "inline" : "none";
  if (state.iso && state.analysis && !state.isoData) {
    try {
      // Single-source: POST inline analysis so the browser-only demo fixture
      // never 404s (tour/download parity). GET fallback only when no model.
      state.isoData = state.analysis
        ? await api("/api/model3d", { analysis: state.analysis })
        : await api(`/api/model3d?figure_id=${encodeURIComponent(state.figureId || "workspace-figure")}`);
    }
    catch (e) { state.isoData = null; state.iso = false; $("toggle-3d").textContent = "3D"; }
  }
  renderAll();
};

let deck = { cards: [], i: 0, know: 0, seen: 0 };
function showCard() {
  const f = $("card-front"), b = $("card-back");
  if (!deck.cards.length) { f.textContent = "Build a deck first."; b.classList.add("hidden"); return; }
  const c = deck.cards[deck.i % deck.cards.length];
  f.innerHTML = "";
  const kind = document.createElement("span");
  kind.className = "card-kind";
  kind.textContent = c.kind;
  f.appendChild(kind);
  const q = document.createElement("span");
  q.className = "card-q";
  q.textContent = c.front.text;
  f.appendChild(q);
  b.innerHTML = "";
  const ans = document.createElement("span");
  ans.className = "card-a";
  ans.textContent = c.back.text;
  b.appendChild(ans);
  if (c.back.detail) {
    const det = document.createElement("span");
    det.className = "card-d";
    det.textContent = ` — ${c.back.detail}`;
    b.appendChild(det);
  }
  b.classList.add("hidden");
  $("deck-score").textContent = `card ${deck.i % deck.cards.length + 1}/${deck.cards.length} · known ${deck.know}/${deck.seen}`;
}
$("btn-deck").onclick = async () => {
  if (!state.analysis) return alert("Analyze or load a model first.");
  const d = await api("/api/flashcards", { analysis: state.analysis }).catch((e) => alert(e.message));
  if (!d) return;
  deck = { cards: d.cards, i: 0, know: 0, seen: 0 };
  showCard();
};
$("btn-flip").onclick = () => $("card-back").classList.toggle("hidden");
$("btn-know").onclick = () => { if (!deck.cards.length) return; deck.know++; deck.seen++; deck.i++; showCard(); };
$("btn-dunno").onclick = () => { if (!deck.cards.length) return; deck.seen++; deck.i++; showCard(); };

function renderFilter() {
  const sel = $("category-filter");
  const cur = state.category;
  sel.innerHTML = '<option value="">All categories</option>';
  if (!state.analysis) { state.category = ""; return; }
  for (const c of [...new Set(state.analysis.entities.map((e) => e.category))].sort()) {
    const o = document.createElement("option");
    o.value = c; o.textContent = c;
    sel.appendChild(o);
  }
  sel.value = [...sel.options].some((o) => o.value === cur) ? cur : "";
  state.category = sel.value;
}

function renderList() {
  const ul = $("entity-list"); ul.innerHTML = "";
  if (!state.analysis) return;
  for (const e of visibleEntities()) {
    const li = document.createElement("li");
    li.textContent = `${e.name} · ${e.category} · ${(e.confidence * 100).toFixed(0)}%`;
    if (e.id === state.selected) li.classList.add("active");
    li.onclick = () => select(e.id);
    ul.appendChild(li);
  }
}

function renderGraph() {
  const svg = $("graph"); svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 100 100");
  if (!state.analysis) return;
  const ents = visibleEntities();
  const ids = new Set(ents.map((e) => e.id));
  const n = Math.max(ents.length, 1);
  const pos = {};
  ents.forEach((e, i) => {
    // Radius 30 (was 38): labels need the outer 20 units, or edge names
    // ("Cortex") clip and neighbours ("SNr"/"Thalamus") collide.
    const a = (2 * Math.PI * i) / n;
    pos[e.id] = { x: 50 + 30 * Math.cos(a), y: 50 + 30 * Math.sin(a), a };
  });
  for (const r of state.analysis.relationships) {
    if (!ids.has(r.source_id) || !ids.has(r.target_id)) continue;
    const a = pos[r.source_id], b = pos[r.target_id];
    if (!a || !b) continue; // same-model invariant: skip dangling instead of inventing
    svg.appendChild(svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y }));
  }
  for (const [i, e] of ents.entries()) {
    const c = svgEl("circle", { cx: pos[e.id].x, cy: pos[e.id].y, r: e.id === state.selected ? 7 : 5,
      class: e.id === state.selected ? "active" : "" });
    c.addEventListener("click", () => select(e.id));
    // Labels ride radially outward from the ring (not alternating sides, which
    // piles them in the middle): each sits past its own node, away from centre.
    // Radius 37 keeps even the widest name inside the 0..100 frame.
    const a = pos[e.id].a ?? 0;
    const t = svgEl("text", { x: 50 + 37 * Math.cos(a), y: 50 + 37 * Math.sin(a),
      "font-size": 4, fill: "#dbe7ff", "text-anchor": "middle" });
    t.textContent = e.name;
    svg.appendChild(c); svg.appendChild(t);
  }
}

function select(id) {
  if (!state.analysis) return;
  state.selected = id;
  const e = state.analysis.entities.find((x) => x.id === id);
  if (!e) return;
  const rels = state.analysis.relationships.filter((r) => r.source_id === id || r.target_id === id);
  const names = Object.fromEntries(state.analysis.entities.map((x) => [x.id, x.name]));
  const box = $("detail");
  box.innerHTML = "";
  box.appendChild(packEl("div", "pack-title", e.name));
  const meta = packEl("div", "pack-stats");
  meta.appendChild(packEl("span", "chip", e.category || "other"));
  if (typeof e.confidence === "number") meta.appendChild(packEl("span", "chip strong", `${Math.round(e.confidence * 100)}%`));
  box.appendChild(meta);
  if (e.description) box.appendChild(packEl("div", "pack-sub", e.description));
  if (e.source_evidence) box.appendChild(packEl("div", "pack-note", `evidence: ${e.source_evidence}`));
  if (e.uncertainty && e.uncertainty !== "—") box.appendChild(packEl("div", "pack-note", `uncertainty: ${e.uncertainty}`));
  const ul = packEl("ul", "pack-list");
  for (const r of rels) {
    const li = document.createElement("li");
    li.textContent = `${names[r.source_id]} --${r.rel_type}--> ${names[r.target_id]}${r.explanation ? ` (${r.explanation})` : ""}`;
    ul.appendChild(li);
  }
  if (!rels.length) {
    const li = document.createElement("li");
    li.textContent = "no relationships";
    ul.appendChild(li);
  }
  box.appendChild(ul);
  renderAll();
}

$("toggle-labels").onchange = renderOverlay;
$("toggle-masks").onchange = renderOverlay;
$("category-filter").onchange = (e) => { state.category = e.target.value; renderAll(); };

// Drag-to-pan: mousedown on the image pans the viewport; overlay shapes keep clicks.
(() => {
  const vp = $("viewport");
  let sx = 0, sy = 0, sl = 0, st = 0, panning = false;
  vp.addEventListener("mousedown", (e) => {
    if (e.target.id !== "figure") return;
    panning = true; sx = e.clientX; sy = e.clientY; sl = vp.scrollLeft; st = vp.scrollTop;
  });
  window.addEventListener("mousemove", (e) => {
    if (!panning) return;
    vp.scrollLeft = sl - (e.clientX - sx);
    vp.scrollTop = st - (e.clientY - sy);
  });
  window.addEventListener("mouseup", () => { panning = false; });
})();

$("btn-segment").onclick = () => withBusy($("btn-segment"), "Segmenting…", async () => {
  const box = $("segment-status");
  const say = (kind, text) => { box.className = "seg " + kind; box.textContent = text; };
  if (!state.analysis || !state.selected) { say("info", "Select a structure first."); return; }
  if (!state.figureFile) { say("warn", "Segmentation needs a server-side figure (not the demo SVG). Select a figure, then analyze."); return; }
  const e = state.analysis.entities.find((x) => x.id === state.selected);
  say("info", `Segmenting "${e.name}" with SAM 3.1…`);
  try {
    const seg = await api("/api/segment", { image_path: state.figureFile,
      prompt: e.name, entity_id: e.id, bbox: e.bbox || undefined });
    const attached = await api("/api/analysis/attach-mask", { figure_id: state.figureId || "workspace-figure",
      entity_id: e.id, kind: seg.kind, mask_ref: seg.mask_ref || "", bbox: seg.bbox || undefined });
    state.analysis = attached.analysis;
    state.isoData = null; // 3D polygons must rebuild from the new analysis
    say(seg.kind === "mask" ? "good" : "info", seg.kind === "mask"
      ? `Mask attached to "${e.name}".`
      : `SAM returned no decodable mask — honest bbox fallback kept for "${e.name}".`);
    renderAll();
  } catch (err) { say("bad", `Segmentation failed: ${honestMsg(err)}`); }
});
function applyZoom() {
  // Percent widths alone cannot grow the figure: the stylesheet caps
  // max-height at 96% (fitted view), which clamps replaced-element layout
  // back down. Lifting max-height while zoomed lets width % take effect;
  // the scrollable viewport then pans the enlarged figure. Overlay tracks
  // via img.clientWidth in alignOverlay, so boxes stay glued on.
  const img = $("figure");
  img.style.width = `${state.zoom * 100}%`;
  img.style.maxWidth = state.zoom === 1 ? "" : "none";
  img.style.maxHeight = state.zoom === 1 ? "" : "none";
  img.style.height = state.zoom === 1 ? "" : "auto";
  // The viewport is a flex row: a bare width % gets flex-shrunk straight
  // back to fit. Pin the item while zoomed so % widths take effect.
  img.style.flex = state.zoom === 1 ? "" : "none";
  renderOverlay();
}
$("zoom-in").onclick = () => { state.zoom = Math.min(4, state.zoom + .25); applyZoom(); };
$("zoom-out").onclick = () => { state.zoom = Math.max(.5, state.zoom - .25); applyZoom(); };
$("reset-view").onclick = () => {
  // A viewport reset: zoom, pan, and label visibility. Active quiz/learn
  // highlights are owned by their challenges (the overlay skips labels
  // while one is shown), so restoring the checkbox here is always safe.
  state.zoom = 1; applyZoom();
  const vp = $("viewport");
  vp.scrollTo(0, 0);
  $("toggle-labels").checked = true;
  renderAll();
};

$("btn-import").onclick = async () => {
  const path = $("doc-path").value.trim();
  if (!path) return alert("Enter a server-local document/image path.");
  const r = await api("/api/import", { path }).catch((e) => alert(e.message));
  if (r) { $("provenance").innerHTML = ""; provenanceDetails(`Imported ${path} — click for full provenance`, r); state.figure = r; }
};
$("btn-render").onclick = async () => {
  const src = $("doc-path").value.trim();
  if (!src) return alert("Import a PDF first, then render its page.");
  const page = Math.max(1, parseInt($("page").value || "1", 10));
  try {
    const r = await api("/api/pdf/render", { path: src, page });
    setFigure(r.image_path, r.figure_url);
    $("provenance").textContent = `Rendered page ${r.page} → select a crop, then Analyze.`;
  } catch (e) { alert(e.message); }
};
$("btn-figure").onclick = async () => {
  const src = $("doc-path").value.trim();
  const crop = $("crop").value.split(",").map(Number);
  const r = await api("/api/figure/select", { image_path: src, crop }).catch((e) => alert(e.message));
  if (r) { setFigure(r.image_path, r.figure_url); $("provenance").innerHTML = ""; provenanceDetails(`Figure crop ${crop} — click for full provenance`, r); }
};
$("btn-analyze").onclick = () => withBusy($("btn-analyze"), "Analyzing…", async () => {
  const src = state.figureFile || $("doc-path").value.trim();
  const r = await api("/api/analyze", { image_path: src, note: $("note").value,
    figure_id: "workspace-figure" }).catch((e) => alert(e.message));
  if (r) { state.analysis = r.analysis; state.selected = null; state.figureId = "workspace-figure"; resetModelView(); renderAll(); }
});
$("btn-demo").onclick = async () => {
  const r = await fetch("/static/basal_ganglia_sample.json").then((x) => x.json()).catch(() => null);
  // Demo fixture ships with the app when present; otherwise explain the live path.
  if (!r) return alert("Demo fixture missing; run demo/basal_ganglia_demo.py --fixture-only to create it.");
  state.analysis = r;
  state.figureFile = "";
  state.figureId = "demo";
  setFigure("", r._demo_image || "/static/basal_ganglia_demo.svg");
  resetModelView();
  renderAll();
};
function setFigure(filePath, displayUrl) {
  state.figureFile = filePath;
  state.figureUrl = displayUrl;
  $("empty-hint").hidden = true;
  const img = $("figure");
  img.src = displayUrl;
  img.onload = () => { state.zoom = 1; img.style.width = "100%"; img.style.maxWidth = ""; img.style.maxHeight = ""; renderOverlay(); };
}
// Text models (books, articles, transcripts) have no figure: clear the canvas so a
// stale image can never pose as the current model's evidence.
function showModel(auto, stagedPath) {
  state.analysis = auto.analysis;
  state.offline = !!auto.offline;
  state.modelWarning = auto.warning || "";
  const eh = document.getElementById("empty-hint");
  if (eh) eh.hidden = true;
  state.selected = null; state.figureId = auto.figure_id;
  if (auto.offline || auto.warning) {
    $("provenance").textContent =
      (auto.offline ? "[offline-extractive model: no API key] " : "") + (auto.warning || "");
  }
  if (auto.figure_url) {
    state.figureFile = stagedPath || "";
    setFigure(stagedPath || "", auto.figure_url);
  } else {
    state.figureFile = "";
    const img = $("figure"); img.removeAttribute("src"); img.style.width = "100%";
    $("overlay").innerHTML = "";
  }
  resetModelView();
  renderAll();
}

// Provenance stays audit-complete but stops shouting: one human summary
// line, full JSON one click away (was a raw JSON wall on every upload).
function provenanceDetails(summary, obj) {
  const box = $("provenance");
  box.innerHTML = "";
  const d = document.createElement("details");
  const s = document.createElement("summary");
  s.textContent = summary;
  const pre = document.createElement("pre");
  pre.className = "mono";
  pre.textContent = JSON.stringify(obj, null, 2);
  d.appendChild(s); d.appendChild(pre);
  box.appendChild(d);
}

// One drop -> one model: upload the file, then auto-create (images fully automatic).
const dz = $("dropzone");
function honestMsg(err) {
  // api() throws Error(data.error); structured cause/fix ride on err.cause/err.fix.
  const parts = [String((err && err.message) || err)];
  if (err && err.cause) parts.push(`Cause: ${err.cause}`);
  if (err && err.fix) parts.push(`Fix: ${err.fix}`);
  return parts.join(" ");
}
// Tour/reveal/narration status in the same tone vocabulary as quiz grades
// (info / warn / good) instead of one flat mono line.
function tourStatus(kind, text) {
  const box = $("tour-status");
  box.className = "tstat " + kind;
  box.textContent = text;
}
["dragover", "dragenter"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
dz.addEventListener("drop", async (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file, file.name);
  dz.textContent = `Uploading ${file.name}… (1/3)`;
  try {
    const up = await fetch("/api/upload", { method: "POST", body: fd }).then((r) => r.json());
    if (up.error) {
      const err = new Error(up.error); err.cause = up.cause; err.fix = up.fix;
      throw err;
    }
    $("provenance").innerHTML = "";
    provenanceDetails(`Uploaded ${file.name}${typeof up.size === "number" ? ` (${up.size} bytes)` : ""} — click for full provenance`, up);
    dz.textContent = `Reading ${file.name}… (2/3)`;
    await new Promise((r) => setTimeout(r, 30));
    dz.textContent = `Building learning model… (3/3)`;
    const auto = await api("/api/auto-create", { path: up.staged_path, note: $("note").value, figure_id: "workspace-figure" });
    if (!auto.model_created) { dz.textContent = "Stored. " + (auto.document.figure_hint || "Done."); return; }
    showModel(auto, up.staged_path);
    const tag = auto.offline ? "offline-extractive (no key)" : auto.source_kind;
    const extra = auto.warning ? ` ${auto.warning}` : "";
    const frames = auto.frames_report
      ? ` Frames kept ${auto.frames_report.kept.length}/${auto.frames_report.frames.length}.` : "";
    dz.textContent = auto.figure_url
      ? `Model created (${tag}): ${auto.analysis.entities.length} entities, ${auto.analysis.relationships.length} relationships.${frames}${extra}`
      : `Text model created (${tag}): graph + learning ready, no figure overlay.${extra}`;
  } catch (err) { dz.textContent = `Drop failed: ${honestMsg(err)}`; }
});

$("btn-link").onclick = async () => {
  const url = $("link-input").value.trim();
  if (!url) return;
  dz.textContent = `Creating model from link… (1/2)`;
  try {
    const auto = await api("/api/auto-create", { path: url, note: $("note").value, figure_id: "workspace-figure" });
    if (!auto.model_created) { dz.textContent = "Stored. " + (auto.document.figure_hint || "Done."); return; }
    showModel(auto, "");
    const tag = auto.offline ? "offline-extractive (no key)" : auto.source_kind;
    dz.textContent = `Model created from link (${tag}): ${auto.analysis.entities.length} entities, ${auto.analysis.relationships.length} relationships (graph + learning ready).${auto.warning ? " " + auto.warning : ""}`;
  } catch (err) { dz.textContent = `Link failed: ${honestMsg(err)}`; }
};

// One click: PDF page -> figure overlay -> live/offline analysis. Composes the
// existing render + select + analyze endpoints; no new backend route.
$("btn-pdf-figure").onclick = () => withBusy($("btn-pdf-figure"), "Building figure…", async () => {
  const src = $("doc-path").value.trim();
  if (!src) return alert("Enter a server-local PDF path first (or drop the PDF above).");
  const page = Math.max(1, parseInt($("page").value || "1", 10));
  try {
    dz.textContent = `Rendering PDF page ${page}…`;
    const r = await api("/api/pdf/render", { path: src, page });
    const crop = ($("crop").value || "0.05,0.05,0.95,0.95").split(",").map(Number);
    dz.textContent = `Selecting figure…`;
    const fig = await api("/api/figure/select", { image_path: r.image_path, crop });
    setFigure(fig.image_path, fig.figure_url);
    dz.textContent = `Analyzing figure…`;
    const a = await api("/api/analyze", { image_path: fig.image_path,
      note: $("note").value, figure_id: "workspace-figure" });
    state.analysis = a.analysis; state.selected = null; state.figureId = "workspace-figure";
    resetModelView(); renderAll();
    dz.textContent = `Figure overlay ready: page ${page}, ${a.analysis.entities.length} entities.`;
  } catch (e) { dz.textContent = `Figure failed: ${honestMsg(e)}`; }
});

let quiz = null; // active on-figure quiz {challenge, score:[got,total]}
let learnScore = [0, 0]; // session-cumulative Learn score, mirrors quiz.score
$("btn-quiz").onclick = async () => {
  if (!state.analysis) return alert("Analyze or load a model first.");
  // Text models (books, transcripts) have no canvas to point at: quiz on
  // descriptions instead of highlights. Same grading, no silent refusal.
  const visual = state.analysis.entities.some((e) => e.bbox);
  if (!visual && !state.analysis.entities.some((e) => e.description)) {
    $("quiz-box").textContent = "Quiz needs descriptions or located entities — this model has neither.";
    return;
  }
  await nextQuiz(visual ? "spatial-recall" : "visual-identification");
};
async function nextQuiz(mode) {
  const c = await api("/api/learn", { analysis: state.analysis,
    mode: mode || "spatial-recall", seed: Date.now() % 100000 }).catch((e) => alert(e.message));
  if (!c) return;
  quiz = { challenge: c, score: quiz ? quiz.score : [0, 0], mode: mode || "spatial-recall",
           visual: mode !== "visual-identification" };
  state._labels = $("toggle-labels").checked;
  $("toggle-labels").checked = false; // names must not leak the answer
  renderQuiz(); renderOverlay();
}
function renderQuiz() {
  const box = $("quiz-box"); box.innerHTML = "";
  if (!quiz || !quiz.challenge) return;
  const c = quiz.challenge;
  const p = document.createElement("div");
  p.className = "quiz-head";
  const headText = () => `${quiz.visual === false ? "Text quiz" : "On-figure quiz"} — ${c.prompt} (score ${quiz.score[0]}/${quiz.score[1]})`;
  p.textContent = headText();
  box.appendChild(p);
  for (const o of c.options) {
    const b = document.createElement("button"); b.className = "opt"; b.textContent = o.name;
    b.onclick = async () => {
      const g = await api("/api/learn/grade", { challenge: c, answer: o.id });
      quiz.score[1]++; if (g.correct) quiz.score[0]++;
      const head = box.querySelector(".quiz-head");
      if (head) head.textContent = headText();
      const d = document.createElement("div"); d.className = "mono " + (g.correct ? "good" : "bad");
      const right = c.options.find((x) => x.id === c.answer_id);
      d.textContent = g.correct ? "correct ✓" : `not quite — answer: ${right ? right.name : c.answer_id}`;
      box.appendChild(d);
      if (g.correct) setTimeout(() => nextQuiz(quiz.mode), 700);
      else renderQuiz();
    };
    box.appendChild(b);
  }
  const stop = document.createElement("button"); stop.textContent = "End quiz";
  stop.onclick = () => {
    quiz = null;
    $("toggle-labels").checked = state._labels !== false;
    box.innerHTML = ""; renderOverlay();
  };
  box.appendChild(stop);
}

$("layer").onchange = renderOverlay;

$("btn-summary").onclick = () => withBusy($("btn-summary"), "Generating…", async () => {
  if (!state.analysis) { alert("Analyze or load a model first."); return; }
  const box = $("summary"); box.textContent = "Generating study pack…";
  try {
    const s = await api("/api/summary", { analysis: state.analysis });
    renderPackSummary(box, s);
  } catch (err) { box.textContent = `Summary failed: ${honestMsg(err)}`; }
});

// Structured study-pack render (same words as the old mono wall, real hierarchy).
function packEl(tag, cls, text) {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (text != null) d.textContent = text;
  return d;
}
function renderQualityInto(box, q) {
  const rows = Object.entries(q).filter(([k]) => !["overall", "weakest", "floor", "skipped"].includes(k))
    .sort((a, b) => a[1].score - b[1].score); // worst-first: weak artifacts surface
  const stats = packEl("div", "pack-stats");
  stats.appendChild(packEl("span", "chip strong", `Quality overall: ${q.overall}/100`));
  if (q.weakest) stats.appendChild(packEl("span", "chip weak", `weakest: ${q.weakest}`));
  if (q.floor === false) stats.appendChild(packEl("span", "chip fail", "FLOOR FAIL (<50)"));
  box.appendChild(stats);
  const ul = packEl("ul", "pack-quality");
  for (const [k, r] of rows) {
    const li = document.createElement("li");
    const head = document.createElement("div");
    head.className = "qrow";
    const nm = document.createElement("span");
    nm.textContent = k;
    const sc = document.createElement("span");
    sc.className = "qscore";
    sc.textContent = `${r.score}/100`;
    head.appendChild(nm); head.appendChild(sc);
    li.appendChild(head);
    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("i");
    fill.style.width = `${Math.max(0, Math.min(100, r.score))}%`;
    bar.appendChild(fill);
    li.appendChild(bar);
    if (r.issues && r.issues.length) li.appendChild(packEl("div", "qissue", r.issues[0]));
    ul.appendChild(li);
  }
  box.appendChild(ul);
  box.appendChild(packEl("div", "pack-note",
    `Skipped: ${(q.skipped && q.skipped.length ? q.skipped.join("; ") : "none")}`));
}
function renderTourInto(box, t) {
  box.appendChild(packEl("div", "pack-h", `3D tour: ${t.stops.length} stops (bottom layer first)`));
  if (!t.stops.length) {
    box.appendChild(packEl("div", "pack-note",
      "No located structures to tour — analyze a figure (or load the demo) for the 3D walkthrough."));
    return;
  }
  const ol = packEl("ol", "pack-list tour-stops");
  for (const s of t.stops) {
    const li = document.createElement("li");
    const nm = document.createElement("span");
    nm.className = "tour-stop-name";
    nm.textContent = `${s.name} (layer ${s.layer})`;
    li.appendChild(nm);
    const ob = document.createElement("div");
    ob.className = "tour-stop-observe";
    ob.textContent = `${s.observe} | links: ${(s.connections || []).join("; ") || "—"} | ${s.camera}`;
    li.appendChild(ob);
    ol.appendChild(li);
  }
  box.appendChild(ol);
}
function renderPackSummary(box, s, note = true) {
  const ex = s.extractive;
  box.innerHTML = "";
  box.appendChild(packEl("div", "pack-title", ex.title));
  box.appendChild(packEl("div", "pack-sub", ex.overview));
  if (ex.entities.length) {
    const ul = packEl("ul", "pack-list");
    for (const e of ex.entities.slice(0, 12)) {
      const li = document.createElement("li");
      li.textContent = e;
      ul.appendChild(li);
    }
    if (ex.entities.length > 12) {
      const li = document.createElement("li");
      li.textContent = `… and ${ex.entities.length - 12} more`;
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
  if (ex.pathways.length) {
    box.appendChild(packEl("div", "pack-h", `Pathways (${ex.pathways_total || ex.pathways.length} distinct routes)`));
    const ul = packEl("ul", "pack-list");
    for (const p of ex.pathways) {
      const li = document.createElement("li");
      li.textContent = `→ ${p}`;
      ul.appendChild(li);
    }
    if (ex.pathways_truncated) {
      const li = document.createElement("li");
      li.textContent = `… and ${ex.pathways_total - ex.pathways.length} more distinct routes`;
      ul.appendChild(li);
    }
    box.appendChild(ul);
  }
  if (note) box.appendChild(packEl("div", "pack-note",
    s.polished ? `POLISHED SUMMARY: ${s.polished}`
               : "(offline extractive brief — add MODEL_API_KEY for a polished summary)"));
}
function renderPackAll(box, s, t, deck, q) {
  renderPackSummary(box, s, false);
  if (s.polished) box.appendChild(packEl("div", "pack-note", `POLISHED SUMMARY: ${s.polished}`));
  const stats = packEl("div", "pack-stats");
  if (t && t.stops) stats.appendChild(packEl("span", "chip", `3D tour: ${t.stops.length} stops`));
  if (deck) stats.appendChild(packEl("span", "chip", `Flashcards: ${deck.cards.length} cards`));
  // Overall/weakest/floor chips live in renderQualityInto — don't duplicate them here.
  if (stats.children.length) box.appendChild(stats);
  if (q) renderQualityInto(box, q);
  if (state.modelWarning) box.appendChild(packEl("div", "pack-note", `Note: ${state.modelWarning}`));
  if (state.offline) box.appendChild(packEl("div", "pack-note",
    "[offline-extractive model: add MODEL_API_KEY for live Muse vision]"));
}

$("btn-study-all").onclick = () => withBusy($("btn-study-all"), "Building…", async () => {
  if (!state.analysis) { alert("Analyze or load a model first."); return; }
  const box = $("summary"); box.textContent = "Building study pack: summary (1/4)…";
  try {
    const s = await api("/api/summary", { analysis: state.analysis });
    box.textContent = "Building study pack: 3D tour (2/4)…";
    const t = await api("/api/tour", { analysis: state.analysis }).catch(() => null);
    box.textContent = "Building study pack: flashcards (3/4)…";
    const deck = await api("/api/flashcards", { analysis: state.analysis }).catch(() => null);
    box.textContent = "Building study pack: quality (4/4)…";
    const q = await api("/api/quality", { analysis: state.analysis }).catch(() => null);
    const ex = s.extractive;
    renderPackAll(box, s, t, deck, q);
  } catch (err) { box.textContent = `Study pack failed: ${honestMsg(err)}`; }
});

$("btn-learn").onclick = async () => {
  if (!state.analysis) return alert("Analyze a figure first.");
  const box = $("challenge"); box.innerHTML = "";
  // A spatial challenge with no visible highlight asks about nothing:
  // mirror the quiz treatment (labels off, one glowing box) and restore
  // both on the next challenge.
  state.learnHi = null; $("toggle-labels").checked = true;
  // Boxless models honestly refuse spatial recall (and friends): surface the
  // refusal with a way forward instead of dying silently on a rejection.
  let c;
  try {
    c = await api("/api/learn", { analysis: state.analysis,
      mode: $("learn-mode").value, seed: Date.now() % 100000 });
  } catch (err) {
    box.appendChild(packEl("div", "challenge-q", "No challenge for this mode yet"));
    const why = honestMsg(err).replace(/^\w*(Error|error):\s*/, "");
    box.appendChild(packEl("div", "pack-note", `${why} — try Visual identification instead.`));
    return;
  }
  const p = document.createElement("div"); p.className = "challenge-q";
  const modeLabel = ($("learn-mode").selectedOptions[0] || {}).textContent || c.mode || "Challenge";
  const headText = () => `${modeLabel} — ${c.prompt} (score ${learnScore[0]}/${learnScore[1]})`;
  p.textContent = headText(); box.appendChild(p);
  if (c.highlight_bbox) {
    state.learnHi = c.highlight_bbox;
    $("toggle-labels").checked = false;
    renderOverlay();
  }
  const answer = async (value) => {
    const g = await api("/api/learn/grade", { challenge: c, answer: value });
    learnScore[1]++; if (g.correct) learnScore[0]++;
    const head = box.querySelector(".challenge-q");
    if (head) head.textContent = headText();
    const d = document.createElement("div"); d.className = "mono " + (g.correct ? "good" : "bad");
    d.textContent = g.correct ? "correct ✓" : `not quite — expected ${JSON.stringify(g.expected)}`;
    box.appendChild(d);
    if (c.chain_names && c.chain_names.length) {
      const ol = document.createElement("ol");
      ol.className = "pack-list pathway-stops";
      for (const nm of c.chain_names) {
        const li = document.createElement("li");
        li.textContent = nm;
        ol.appendChild(li);
      }
      box.appendChild(ol);
    }
  };
  if (c.options) {
    for (const o of c.options) {
      const b = document.createElement("button");
      b.className = "opt"; b.textContent = typeof o === "string" ? o : o.name;
      b.onclick = () => answer(typeof o === "string" ? o : o.id);
      box.appendChild(b);
    }
  } else if (c.chain) {
    const b = document.createElement("button");
    b.className = "opt"; b.textContent = "Reveal pathway order";
    b.onclick = () => answer(c.chain);
    const hint = document.createElement("div"); hint.className = "mono";
    hint.textContent = `Trace ${c.chain.length} connected structures in order, starting at ${c.chain_names ? c.chain_names[0] : c.chain[0]}.`;
    box.appendChild(hint); box.appendChild(b);
  } else {
    const input = document.createElement("input"); input.placeholder = "rel_type, e.g. inhibits";
    const b = document.createElement("button"); b.textContent = "Check";
    b.onclick = () => answer(input.value.trim());
    box.appendChild(input); box.appendChild(b);
  }
};

/* Showpieces (all offline-safe, no network): cinematic tour, browser voice, AI-vision reveal. */
const tour = { stops: [], i: 0, playing: false, timer: null };
function tourStops() {
  if (!state.analysis) return [];
  return visibleEntities().filter((e) => e.bbox || e.description);
}
function tourCaption(stop, idx, total) {
  const box = $("tour-caption");
  box.hidden = false;
  box.innerHTML = "";
  const b = document.createElement("b");
  b.textContent = stop.name || stop.id;
  box.appendChild(b);
  if (typeof stop.confidence === "number") {
    const conf = document.createElement("span");
    conf.className = "tour-conf";
    conf.textContent = `${(stop.confidence * 100).toFixed(0)}%`;
    box.appendChild(conf);
  }
  const span = document.createElement("span");
  span.textContent = ` — ${(stop.description || "Locate it on the figure.").slice(0, 220)}`;
  box.appendChild(span);
  const prog = document.createElement("span");
  prog.className = "tour-prog";
  prog.textContent = `${idx + 1}/${total} · ‹ › step · Esc stops`;
  box.appendChild(prog);
}
function tourGo(n) {
  const stops = tourStops();
  if (!stops.length) { tourStatus("warn", "Tour: analyze or load the demo first."); return; }
  tour.stops = stops;
  tour.i = ((n % stops.length) + stops.length) % stops.length;
  const e = stops[tour.i];
  select(e.id);
  // Cinematic pan: scroll the bbox center into view inside the viewport.
  try {
    if (e.bbox) {
      const vp = $("viewport"), img = $("figure");
      const cx = ((e.bbox.x_min + e.bbox.x_max) / 2) * img.clientWidth;
      const cy = ((e.bbox.y_min + e.bbox.y_max) / 2) * img.clientHeight;
      vp.scrollTo({ left: Math.max(0, cx - vp.clientWidth / 2), top: Math.max(0, cy - vp.clientHeight / 2), behavior: "smooth" });
    }
  } catch (_) { /* smooth scroll is a nicety, never a failure */ }
  $("viewport").classList.add("touring");
  tourCaption(e, tour.i, stops.length);
  tourStatus("info", `Tour (offline replay): stop ${tour.i + 1}/${stops.length} — ${e.name}`);
  if ($("narrate-toggle").checked) speak(`${e.name}. ${(e.description || "").slice(0, 260)}`);
}
function tourStop() {
  tour.playing = false;
  if (tour.timer) { clearInterval(tour.timer); tour.timer = null; }
  $("btn-tour-play").textContent = "▶ Tour";
  $("tour-caption").hidden = true;
  $("viewport").classList.remove("touring");
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) {}
  if (tour.stops.length) tourStatus("info", `Tour: paused at stop ${tour.i + 1}/${tour.stops.length}.`);
}
$("btn-tour-play").onclick = () => {
  if (!state.analysis) { alert("Analyze or load the demo first — the tour runs fully offline on the model."); return; }
  if (tour.playing) { tourStop(); return; }
  tour.playing = true;
  $("btn-tour-play").textContent = "⏸ Pause";
  tourGo(tour.i || 0);
  tour.timer = setInterval(() => {
    if (tour.i + 1 >= tourStops().length) { tourStop(); tourStatus("good", "Tour: finale — every structure visited. Esc to reset."); return; }
    tourGo(tour.i + 1);
  }, 3200);
};
$("btn-tour-prev").onclick = () => { if (tour.playing) tourStop(); tourGo(tour.i - 1); };
$("btn-tour-next").onclick = () => { if (tour.playing) tourStop(); tourGo(tour.i + 1); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && (tour.playing || !$("tour-caption").hidden)) tourStop(); });

// Browser-voice narration: SpeechSynthesis only (on-device, offline). No fetch, no key.
function pickVoice() {
  try {
    const synth = window.speechSynthesis;
    if (!synth) return null;
    const want = $("voice-select").value;
    const voices = synth.getVoices();
    if (want) { const v = voices.find((x) => x.name === want); if (v) return v; }
    return voices.find((x) => x.lang && x.lang.startsWith("en")) || voices[0] || null;
  } catch (_) { return null; }
}
function refreshVoices() {
  try {
    const synth = window.speechSynthesis;
    if (!synth) { $("voice-select").innerHTML = '<option value="">No local voice</option>'; return; }
    const sel = $("voice-select"), cur = sel.value;
    sel.innerHTML = '<option value="">Auto voice</option>';
    for (const v of synth.getVoices()) {
      const o = document.createElement("option");
      o.value = v.name; o.textContent = `${v.name} (${v.lang})`;
      sel.appendChild(o);
    }
    sel.value = cur;
  } catch (_) {}
}
function speak(text) {
  try {
    const synth = window.speechSynthesis;
    if (!synth || !text) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 400));
    const v = pickVoice();
    if (v) u.voice = v;
    u.rate = 1.02;
    synth.speak(u);
  } catch (_) { /* voice is enhancement-only */ }
}
$("btn-narrate").onclick = () => {
  if (!("speechSynthesis" in window)) { tourStatus("warn", "Narration: this browser has no local speech engine."); return; }
  if (!state.analysis) { alert("Analyze or load the demo first."); return; }
  const e = state.analysis.entities.find((x) => x.id === state.selected) || visibleEntities()[0];
  if (!e) return;
  speak(`${e.name}. ${e.description || ""} ${e.source_evidence ? "Evidence: " + e.source_evidence : ""}`.slice(0, 500));
  tourStatus("info", `Narrating: ${e.name} (browser voice, offline).`);
};
try {
  refreshVoices();
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = refreshVoices;
} catch (_) {}

// AI-vision reveal (offline replay): sweep line, then the LOADED model pops in
// one-by-one with confidence — a replay of the stored analysis, not live vision.
let revealTimers = [];
$("btn-reveal").onclick = () => {
  const stops = tourStops();
  if (!stops.length) { alert("Analyze or load the demo first — reveal replays the loaded model."); return; }
  if (tour.playing) tourStop();
  revealTimers.forEach(clearTimeout); revealTimers = [];
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) {}
  const svg = $("overlay");
  const scan = $("scanline");
  scan.hidden = false;
  svg.innerHTML = "";
  $("tour-caption").hidden = false;
  $("tour-caption").textContent = "AI-vision replay: scanning loaded model…";
  tourStatus("info", `Reveal (offline replay): scanning, then ${stops.length} structures replay.`);
  const ordered = [...stops].sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
  ordered.forEach((e, k) => {
    revealTimers.push(setTimeout(() => {
      if (!e.bbox) return;
      const p = toPct(e.bbox);
      const g = svgEl("g", { class: "pop" });
      const r = svgEl("rect", { x: p.x, y: p.y, width: p.w, height: p.h,
        fill: "rgba(34,211,238,.28)", stroke: "#22d3ee", "stroke-width": .8 });
      r.addEventListener("click", () => select(e.id));
      const t = svgEl("text", { x: p.x, y: Math.max(2, p.y - 0.8), "font-size": 2.3, fill: "#dbe7ff" });
      t.textContent = `${e.name} ${(typeof e.confidence === "number" ? (e.confidence * 100).toFixed(0) + "%" : "")}`;
      t.addEventListener("click", () => select(e.id));
      g.appendChild(r); g.appendChild(t); svg.appendChild(g);
      $("tour-caption").innerHTML = "";
      const b = document.createElement("b");
      b.textContent = e.name;
      $("tour-caption").appendChild(b);
      $("tour-caption").appendChild(document.createTextNode(
        ` resolves (${k + 1}/${ordered.length})${typeof e.confidence === "number" ? ` · ${(e.confidence * 100).toFixed(0)}%` : ""}`));
      if (k === ordered.length - 1) {
        revealTimers.push(setTimeout(() => {
          scan.hidden = true;
          select(e.id);
          $("tour-caption").hidden = true;
          tourStatus("good", `Reveal: complete — ${ordered.length} structures replayed from the loaded model (offline replay, not live vision).`);
        }, 900));
      }
    }, 500 + k * 450));
  });
};

window.addEventListener("resize", renderOverlay);
refreshHealth();
