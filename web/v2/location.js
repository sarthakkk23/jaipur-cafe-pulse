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
    const p0 = a.places[0]; choose(p0[1], p0[2], p0[0]);
    placesEl.querySelector("[data-place]")?.setAttribute("aria-pressed", "true");
  }
  document.querySelectorAll("[data-area]").forEach((b) => b.addEventListener("click", () => setArea(+b.dataset.area)));

  // map projection: the area box, padded, fitted to the canvas
  function frame() {
    const w = canvas.clientWidth, h = canvas.clientHeight, dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const [la0, la1, lo0, lo1] = D.areas[D.names[area]].box, pad = 0.004;
    const kx = Math.cos(26.88 * Math.PI / 180);
    const spanX = (lo1 - lo0 + 2 * pad) * kx, spanY = la1 - la0 + 2 * pad;
    const s = Math.min(w / spanX, h / spanY);
    const cx = (lo0 + lo1) / 2, cy = (la0 + la1) / 2;
    view = { w, h, X: (lon) => w / 2 + (lon - cx) * kx * s, Y: (lat) => h / 2 - (lat - cy) * s, s, kx, cx, cy };
  }
  const roadLL = (x, z) => [R.bbox.lat[1] - (z / R.size_m[1]) * (R.bbox.lat[1] - R.bbox.lat[0]), R.bbox.lon[0] + (x / R.size_m[0]) * (R.bbox.lon[1] - R.bbox.lon[0])];

  function draw() {
    if (!D) return;
    frame();
    const { w, h, X, Y } = view;
    ctx.fillStyle = "#e9e8e4"; ctx.fillRect(0, 0, w, h);
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
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
    ctx.drawImage(off, X(lons[0]) - half, Y(lats[0]) - half, X(lons[lons.length - 1]) - X(lons[0]) + 2 * half, Y(lats[lats.length - 1]) - Y(lats[0]) + 2 * half);
    // streets on top, in three weights
    [0.7, 0.45, 0.22].forEach((alpha, cls) => {
      ctx.strokeStyle = `rgba(22, 22, 22, ${alpha})`; ctx.lineWidth = cls === 0 ? 1.6 : cls === 1 ? 1.1 : 0.7;
      ctx.beginPath();
      for (const wy of R.ways[cls] || []) {
        for (let i = 0; i + 1 < wy.length; i += 2) {
          const [la, lo] = roadLL(wy[i], wy[i + 1]);
          i === 0 ? ctx.moveTo(X(lo), Y(la)) : ctx.lineTo(X(lo), Y(la));
        }
      }
      ctx.stroke();
    });
    if (pick) {
      const r = (D.radius_m / 111320) * view.s;
      ctx.fillStyle = "rgba(245, 228, 221, .35)"; ctx.strokeStyle = "#161616"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(X(pick.lon), Y(pick.lat), r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#161616"; ctx.beginPath(); ctx.arc(X(pick.lon), Y(pick.lat), 6, 0, Math.PI * 2); ctx.fill();
    }
  }

  canvas.addEventListener("click", (e) => {
    if (!view) return;
    const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    const lon = view.cx + (x - view.w / 2) / (view.kx * view.s), lat = view.cy - (y - view.h / 2) / view.s;
    placesEl.querySelectorAll("[data-place]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    choose(lat, lon, null);
  });

  function choose(lat, lon, name) {
    // the nearest grid spot in this area
    let best = null, bd = Infinity;
    for (const s of D.byArea[area]) { const d = (s[0] - lat) ** 2 + ((s[1] - lon) * 0.89) ** 2; if (d < bd) { bd = d; best = s; } }
    if (!best || Math.sqrt(bd) * 111320 > 400) { report.innerHTML = '<p class="lr-k">That spot is outside the area I read. Pick a spot inside the map.</p>'; return; }
    pick = { lat: best[0], lon: best[1] };
    draw();
    read(best[3], name);
  }

  // the report, in plain words
  function read(s, name) {
    const an = D.names[area], A = D.areas[an].cafes, k = D.k;
    const where = name ? `around ${esc(name)}` : "around this spot";
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
    const ctx2 = [`${s.hotels} ${s.hotels === 1 ? "hotel" : "hotels"}`, `${s.stops} bus ${s.stops === 1 ? "stop" : "stops"}`];
    ctx2.push(s.metro_m != null && s.metro_m <= 1500 ? `${esc(s.metro)} metro ${s.metro_m >= 1000 ? (s.metro_m / 1000).toFixed(1) + " km" : s.metro_m + " m"} away` : "no metro within a 20-minute walk");
    html += `<p class="lr-ctx"><b>Also within the walk</b>, as mapped in OpenStreetMap: ${ctx2.join(", ")}.</p>`;
    report.innerHTML = html;
  }
})();
