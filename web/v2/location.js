// Location check. Draws the area's streets and a quiet heat of café counts, lets the reader pick a spot, and reads
// that spot's five-minute walk aloud in plain words. Everything comes from published aggregates (data/location.json).
(() => {
  const canvas = document.querySelector(".loc-canvas"), report = document.querySelector(".loc-report");
  if (!canvas || !report) return;
  const ctx = canvas.getContext("2d");
  const placesEl = document.querySelector(".loc-places");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const inr = (v) => "₹" + v.toLocaleString("en-IN");
  const LBL = { "Coffee-led": "coffee-led cafés", "Tea & chai": "chai cafés", Bakery: "bakery cafés", "All-day café": "all-day cafés" };
  const COL = { "Coffee-led": "#b0533d", "Tea & chai": "#3f74ad", Bakery: "#e3ad9f", "All-day café": "#dddcd7" };
  let D, R, area = 0, pick = null, view = null;

  Promise.all([fetch("../data/location.json").then((r) => r.json()), fetch("../data/roads.json").then((r) => r.json())]).then(([d, roads]) => {
    D = d; R = roads;
    D.names = Object.keys(D.areas);
    D.byArea = D.names.map((_, i) => D.spots.filter((s) => s[2] === i));
    D.busy = D.byArea.map((list) => list.map((s) => s[3].n).filter((n) => n > 0).sort((a, b) => a - b));   // spots with any café
    // what a typical café spot in each area has around it, group by group (median and upper quartile)
    const q = (xs, p) => { const v = [...xs].sort((a, b) => a - b); return v.length ? v[Math.min(v.length - 1, Math.floor(p * v.length))] : 0; };
    D.groups = D.demand_groups || [];
    D.typ = D.byArea.map((list) => {
      const cafeSpots = list.filter((s) => s[3].n > 0), t = {};
      for (const [g] of D.groups) { const xs = cafeSpots.map((s) => (s[3].demand || {})[g] || 0); t[g] = { mid: q(xs, 0.5), high: q(xs, 0.75) }; }
      const tot = (s) => Object.values(s[3].demand || {}).reduce((a, b) => a + b, 0);
      t.perCafe = q(cafeSpots.filter((s) => s[3].n >= 3).map((s) => tot(s) / s[3].n), 0.5);
      return t;
    });
    frame();
    setArea(0);
    new ResizeObserver(draw).observe(canvas);
  }).catch(() => { report.innerHTML = '<p class="lr-k">The map could not load. Please refresh the page.</p>'; });

  function setArea(i) {
    area = i;
    document.querySelectorAll("[data-area]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.area === i)));
    const a = D.areas[D.names[i]];
    placesEl.innerHTML = a.places.map((p, j) => `<button type="button" class="seg" data-place="${j}">${esc(p[0])}</button>`).join("");
    placesEl.querySelectorAll("[data-place]").forEach((b) => b.addEventListener("click", () => {
      const p = a.places[+b.dataset.place]; choose(p[1], p[2], p[0]);
      placesEl.querySelectorAll("[data-place]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }));
    shown = null; hover = null;
    if (view) frame();
    const p0 = a.places[0]; choose(p0[1], p0[2], p0[0]);
    placesEl.querySelector("[data-place]")?.setAttribute("aria-pressed", "true");
  }
  document.querySelectorAll("[data-area]").forEach((b) => b.addEventListener("click", () => setArea(+b.dataset.area)));

  // map projection: the area box, padded, fitted to the canvas. The streets and the café heat are drawn once into a base
  // layer; every pointer move only repaints the light overlay on top, so hovering stays smooth.
  let base = null, hover = null, shown = null, anim = 0, queued = false;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const KX = Math.cos(26.88 * Math.PI / 180);
  function frame() {
    const w = canvas.clientWidth, h = canvas.clientHeight, dpr = Math.min(devicePixelRatio || 1, 2);
    if (!w || !h) return false;
    canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const [la0, la1, lo0, lo1] = D.areas[D.names[area]].box, pad = 0.004;
    const spanX = (lo1 - lo0 + 2 * pad) * KX, spanY = la1 - la0 + 2 * pad;
    const s = Math.min(w / spanX, h / spanY);
    const cx = (lo0 + lo1) / 2, cy = (la0 + la1) / 2;
    view = { w, h, dpr, X: (lon) => w / 2 + (lon - cx) * KX * s, Y: (lat) => h / 2 - (lat - cy) * s, s, cx, cy };
    base = paintBase();
    return true;
  }
  const roadLL = (x, z) => [R.bbox.lat[1] - (z / R.size_m[1]) * (R.bbox.lat[1] - R.bbox.lat[0]), R.bbox.lon[0] + (x / R.size_m[0]) * (R.bbox.lon[1] - R.bbox.lon[0])];

  function paintBase() {
    const { w, h, dpr, X, Y } = view;
    const b = document.createElement("canvas"); b.width = w * dpr; b.height = h * dpr;
    const c = b.getContext("2d"); c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.fillStyle = "#e9e8e4"; c.fillRect(0, 0, w, h);
    // café heat: the grid painted one pixel per spot, then scaled up smoothly, darker where more cafés stand within the walk
    const list = D.byArea[area], max = Math.max(1, ...list.map((s) => s[3].n));
    const lats = [...new Set(list.map((s) => s[0]))].sort((a, b) => b - a), lons = [...new Set(list.map((s) => s[1]))].sort((a, b) => a - b);
    const off = document.createElement("canvas"); off.width = lons.length; off.height = lats.length;
    const oc = off.getContext("2d"), img = oc.createImageData(off.width, off.height);
    const li = new Map(lats.map((v, i) => [v, i])), oi = new Map(lons.map((v, i) => [v, i]));
    for (const [la, lo, , s] of list) {
      const p = (li.get(la) * off.width + oi.get(lo)) * 4, t = Math.sqrt(s.n / max);
      img.data.set([176, 83, 61, s.n ? Math.round(255 * (0.06 + 0.55 * t)) : 0], p);
    }
    oc.putImageData(img, 0, 0);
    const half = (D.spacing_m / 111320) * view.s / 2;
    c.imageSmoothingEnabled = true; c.imageSmoothingQuality = "high";
    c.drawImage(off, X(lons[0]) - half, Y(lats[0]) - half, X(lons[lons.length - 1]) - X(lons[0]) + 2 * half, Y(lats[lats.length - 1]) - Y(lats[0]) + 2 * half);
    // streets on top, in three weights
    [0.7, 0.45, 0.22].forEach((alpha, cls) => {
      c.strokeStyle = `rgba(22, 22, 22, ${alpha})`; c.lineWidth = cls === 0 ? 1.6 : cls === 1 ? 1.1 : 0.7;
      c.beginPath();
      for (const wy of R.ways[cls] || []) {
        for (let i = 0; i + 1 < wy.length; i += 2) {
          const [la, lo] = roadLL(wy[i], wy[i + 1]);
          i === 0 ? c.moveTo(X(lo), Y(la)) : c.lineTo(X(lo), Y(la));
        }
      }
      c.stroke();
    });
    // the named places, so the map can be read at a glance
    c.font = '600 12px "Literata", Georgia, serif'; c.textBaseline = "middle";
    // labels step out of each other's way: right of the dot, then left, then above or below; a label that can't fit is left off
    const boxes = [], hit = (bx) => boxes.some((o) => bx[0] < o[0] + o[2] && o[0] < bx[0] + bx[2] && bx[1] < o[1] + o[3] && o[1] < bx[1] + bx[3]);
    for (const [nm, la, lo] of D.areas[D.names[area]].places) {
      const x = X(lo), y = Y(la), tw = c.measureText(nm).width + 8;
      c.fillStyle = "#161616"; c.beginPath(); c.arc(x, y, 3.5, 0, Math.PI * 2); c.fill();
      const tries = [[x + 8, y - 10], [x - 8 - tw, y - 10], [x - tw / 2, y - 32], [x - tw / 2, y + 12]]
        .map(([bx, by]) => [Math.min(Math.max(bx, 4), w - tw - 4), Math.min(Math.max(by, 4), h - 24), tw, 20]);
      const box = tries.find((bx) => !hit(bx));
      if (!box) continue;
      boxes.push(box);
      c.fillStyle = "rgba(245, 245, 242, .92)"; c.fillRect(box[0], box[1], box[2], box[3]);
      c.fillStyle = "#161616"; c.fillText(nm, box[0] + 4, box[1] + 10.5);
    }
    return b;
  }

  const ring = () => (D.radius_m / 111320) * view.s;
  function label(x, y, text, dark) {
    ctx.font = '600 13px "Literata", Georgia, serif'; ctx.textBaseline = "middle";
    const tw = ctx.measureText(text).width, bx = Math.min(Math.max(x - tw / 2 - 8, 4), view.w - tw - 20), by = Math.max(y - ring() - 30, 4);
    ctx.fillStyle = dark ? "#161616" : "rgba(245, 245, 242, .95)"; ctx.fillRect(bx, by, tw + 16, 24);
    ctx.fillStyle = dark ? "#f5f5f2" : "#161616"; ctx.fillText(text, bx + 8, by + 12.5);
  }
  const count = (n) => `${n} ${n === 1 ? "café" : "cafés"}`;

  function render() {
    queued = false;
    if (!D || !view || !base) return;
    const { w, h, X, Y } = view;
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(base, 0, 0, w, h);
    if (hover && !(pick && hover.lat === pick.lat && hover.lon === pick.lon)) {
      ctx.setLineDash([5, 5]); ctx.strokeStyle = "rgba(22, 22, 22, .55)"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(X(hover.lon), Y(hover.lat), ring(), 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
      label(X(hover.lon), Y(hover.lat), count(hover.n), false);
    }
    if (shown) {
      const x = X(shown.lon), y = Y(shown.lat);
      ctx.fillStyle = "rgba(245, 228, 221, .38)"; ctx.strokeStyle = "#161616"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, ring(), 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#161616"; ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
      if (!hover && pick) label(x, y, count(pick.n), true);
    }
  }
  const queue = () => { if (!queued) { queued = true; requestAnimationFrame(render); } };
  function draw() { if (D && frame()) render(); }

  // the chosen spot glides to its new place instead of jumping
  function glide(to) {
    cancelAnimationFrame(anim);
    const from = shown;
    if (!from || reduce) { shown = to; queue(); return; }
    const t0 = performance.now(), dur = 280;
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      shown = { lat: from.lat + (to.lat - from.lat) * e, lon: from.lon + (to.lon - from.lon) * e };
      render();
      if (k < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }

  function nearest(lat, lon) {
    let best = null, bd = Infinity;
    for (const s of D.byArea[area]) { const d = (s[0] - lat) ** 2 + ((s[1] - lon) * 0.89) ** 2; if (d < bd) { bd = d; best = s; } }
    return best && Math.sqrt(bd) * 111320 <= 400 ? best : null;
  }
  function at(e) {
    const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    return [view.cy - (y - view.h / 2) / view.s, view.cx + (x - view.w / 2) / (KX * view.s)];
  }
  canvas.addEventListener("pointermove", (e) => {
    if (!view || e.pointerType !== "mouse") return;
    const s = nearest(...at(e));
    const next = s ? { lat: s[0], lon: s[1], n: s[3].n } : null;
    if ((next && hover && next.lat === hover.lat && next.lon === hover.lon) || (!next && !hover)) return;
    hover = next; queue();
  });
  canvas.addEventListener("pointerleave", () => { hover = null; queue(); });
  canvas.addEventListener("click", (e) => {
    if (!view) return;
    hover = null;
    placesEl.querySelectorAll("[data-place]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    choose(...at(e), null);
  });
  // arrow keys walk the chosen spot one grid step at a time
  canvas.tabIndex = 0;
  canvas.addEventListener("keydown", (e) => {
    const dir = { ArrowUp: [1, 0], ArrowDown: [-1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
    if (!dir || !pick) return;
    e.preventDefault();
    const step = D.spacing_m / 111320;
    placesEl.querySelectorAll("[data-place]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    choose(pick.lat + dir[0] * step, pick.lon + dir[1] * step / KX, null);
  });

  function choose(lat, lon, name) {
    // the nearest grid spot in this area
    const best = nearest(lat, lon);
    if (!best) { report.innerHTML = '<p class="lr-k">That spot is outside the area I read. Pick a spot inside the map.</p>'; return; }
    pick = { lat: best[0], lon: best[1], n: best[3].n };
    if (!name) {
      // name the spot after the nearest landmark when one is close, so the report reads "near Ashok Marg"
      const lm = D.areas[D.names[area]].places.map((p) => [p[0], Math.hypot(p[1] - best[0], (p[2] - best[1]) * 0.89) * 111320]).sort((a, b) => a[1] - b[1])[0];
      if (lm && lm[1] <= 400) name = { near: lm[0] };
    }
    glide({ lat: best[0], lon: best[1] });
    read(best[3], name);
  }

  // the report, in plain words
  function read(s, name) {
    const an = D.names[area], A = D.areas[an].cafes, k = D.k;
    const where = name && name.near ? `near ${esc(name.near)}` : name ? `around ${esc(name)}` : "around this spot";
    const busy = D.busy[area], rank = busy.length ? Math.round(100 * busy.filter((n) => n < s.n).length / busy.length) : 0;
    let html = `<p class="lr-big">${s.n} <span>${s.n === 1 ? "café" : "cafés"}</span></p>`;
    html += `<p class="lr-k">within a five-minute walk ${where}.</p>`;
    html += s.n ? `<p class="lr-sub">${rank >= 50 ? `Busier than ${rank}% of café spots in ${esc(an)}.` : `Quieter than ${100 - rank}% of café spots in ${esc(an)}.`}</p>` : `<p class="lr-sub">No café within a five-minute walk.</p>`;
    const notes = [];
    if (s.mix) {
      html += `<div class="lr-mix" role="img" aria-label="Type mix">${D.types.map((t) => `<i style="flex:${Math.max(s.mix[t], 0.5)};background:${COL[t]}"></i>`).join("")}</div>`;
      html += `<table class="lr-tab"><thead><tr><th></th><th>Here</th><th>${esc(an)}</th></tr></thead><tbody>`;
      html += D.types.map((t) => `<tr><td><i style="background:${COL[t]}"></i>${esc(t)}</td><td>${s.mix[t]}%</td><td>${A.mix[t]}%</td></tr>`).join("");
      if (s.open8 != null) html += `<tr><td>Serving by 8am</td><td>${s.open8}%</td><td>${A.open8}%</td></tr>`;
      if (s.price != null) html += `<tr><td>Typical cost for two</td><td>${inr(s.price)}</td><td>${inr(A.price)}</td></tr>`;
      if (s.reviews != null) html += `<tr><td>Typical Google reviews</td><td>${s.reviews}</td><td>${A.reviews}</td></tr>`;
      html += "</tbody></table>";
      // gaps and signals, each against the area as a whole
      for (const t of D.types) {
        if (A.mix[t] >= 10 && s.mix[t] <= A.mix[t] / 2) notes.push(`<b>Few ${LBL[t]}.</b> ${s.mix[t]}% here against ${A.mix[t]}% across ${esc(an)}: room for one.`);
        if (s.mix[t] >= A.mix[t] + 15) notes.push(`<b>Crowded with ${LBL[t]}.</b> ${s.mix[t]}% here against ${A.mix[t]}% across ${esc(an)}: a new one would need to stand apart.`);
      }
      if (s.open8 != null && s.open8 <= A.open8 - 10) notes.push(`<b>The morning is open.</b> Only ${s.open8}% of cafés here serve by 8am, against ${A.open8}% across ${esc(an)}.`);
      if (s.price != null && s.price >= A.price * 1.25) notes.push(`<b>A pricier street.</b> The typical café here charges ${inr(s.price)} for two, against ${inr(A.price)} across ${esc(an)}.`);
      if (s.price != null && s.price <= A.price * 0.8) notes.push(`<b>A value street.</b> The typical café here charges ${inr(s.price)} for two, against ${inr(A.price)} across ${esc(an)}.`);
      if (s.reviews != null && s.reviews <= A.reviews * 0.6) notes.push(`<b>Attention is spread thin.</b> The typical café here has ${s.reviews} Google reviews, against ${A.reviews} across ${esc(an)}.`);
      if (s.reviews != null && s.reviews >= A.reviews * 1.6) notes.push(`<b>A street people review.</b> The typical café here has ${s.reviews} Google reviews, against ${A.reviews} across ${esc(an)}.`);
    } else if (s.n) {
      notes.push(`<b>Quiet ground.</b> Fewer than ${k} cafés stand within the walk, so I show the count only. Few rivals, but check that people pass by.`);
    } else {
      notes.push(`<b>Untested ground.</b> No café stands within the walk. That can be an opening or a sign of little footfall; walk it at different hours.`);
    }
    if (!notes.length && s.mix) notes.push(`<b>A typical ${esc(an)} street.</b> Nothing here stands far from the area as a whole, so the gap has to come from what you offer.`);
    if (notes.length) html += `<ul class="lr-notes">${notes.map((n) => `<li>${n}</li>`).join("")}</ul>`;
    // who is around to buy coffee
    if (D.groups.length) {
      const T = D.typ[area], dm = s.demand || {}, total = Object.values(dm).reduce((a, b) => a + b, 0);
      html += `<p class="lr-h">Who's around to buy coffee</p><table class="lr-tab"><thead><tr><th></th><th>Here</th><th>Typical spot</th></tr></thead><tbody>`;
      html += D.groups.map(([g, label]) => `<tr><td>${esc(label)}</td><td>${dm[g] || 0}</td><td>${T[g].mid}</td></tr>`).join("");
      html += "</tbody></table>";
      const dn = [];
      if (s.n >= 3 && T.perCafe > 0) {
        const r = total / s.n;
        if (r >= T.perCafe * 1.5 && total >= 15) dn.push(`<b>Plenty of demand, few cafés serving it.</b> ${r.toFixed(1)} of these places per café here, against ${T.perCafe.toFixed(1)} at a typical spot in ${esc(an)}.`);
        if (r <= T.perCafe * 0.6) dn.push(`<b>Many cafés for the demand around.</b> ${r.toFixed(1)} of these places per café here, against ${T.perCafe.toFixed(1)} at a typical spot in ${esc(an)}.`);
      } else if (!s.n && total >= 10) dn.push(`<b>Demand without a café.</b> ${total} of these places within the walk and no café yet.`);
      const crowd = { office: "An office crowd", college: "A student crowd", coaching: "A student crowd", gym: "A fitness crowd", hospital: "A hospital crowd", hotel: "A visitor crowd", coworking: "A remote-work crowd" };
      // only the two strongest crowds, so the useful signal isn't buried
      const said = new Set();
      D.groups.map(([g, label]) => ({ g, label, v: dm[g] || 0, lift: (dm[g] || 0) / Math.max(1, T[g].mid) }))
        .filter((c) => crowd[c.g] && c.v >= 3 && c.v >= T[c.g].high && c.v > T[c.g].mid)
        .sort((a, b) => b.lift - a.lift)
        .forEach((c) => {
          if (said.has(crowd[c.g]) || said.size >= 2) return;
          said.add(crowd[c.g]);
          dn.push(`<b>${crowd[c.g]}.</b> ${c.v} ${esc(c.label.toLowerCase())} within the walk, against ${T[c.g].mid} at a typical café spot in ${esc(an)}.`);
        });
      if (dn.length) html += `<ul class="lr-notes">${dn.map((n) => `<li>${n}</li>`).join("")}</ul>`;
    }
    const ctx2 = [];
    if (!D.groups.length) ctx2.push(`${s.hotels} ${s.hotels === 1 ? "hotel" : "hotels"}`);
    ctx2.push(`${s.stops} bus ${s.stops === 1 ? "stop" : "stops"}`);
    ctx2.push(s.metro_m != null && s.metro_m <= 1500 ? `${esc(s.metro)} metro ${s.metro_m >= 1000 ? (s.metro_m / 1000).toFixed(1) + " km" : s.metro_m + " m"} away` : "no metro within a 20-minute walk");
    html += `<p class="lr-ctx"><b>Also within the walk</b>, as mapped in OpenStreetMap: ${ctx2.join(", ")}.</p>`;
    report.innerHTML = html;
  }
})();
