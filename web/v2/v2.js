// Jaipur Café Pulse v2. Progressive enhancement only: the page is complete without this file.
(() => {
  window.__pulse = true;
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const motion = !reduce && "IntersectionObserver" in window;
  if (motion) root.classList.add("motion");
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); parent && parent.appendChild(n); return n; };

  // ---------- entrances: heading, then text, then picture; once; never a gate ----------
  const reveals = [...document.querySelectorAll(".reveal")];
  const showAll = () => { reveals.forEach((r) => r.classList.add("is-in")); document.querySelector(".board")?.classList.add("is-in"); };
  if (motion) {
    let alive = false;
    setTimeout(() => { if (!alive) { root.classList.remove("motion", "js"); showAll(); } }, 2000);
    const io = new IntersectionObserver((es) => {
      alive = true;
      es.forEach((e) => {
        if (!e.isIntersecting) return;
        const sib = [...(e.target.parentElement?.querySelectorAll(":scope > .reveal") || [])];
        e.target.style.transitionDelay = `${Math.max(0, sib.indexOf(e.target)) * 75}ms`;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    reveals.forEach((r) => io.observe(r));
    requestAnimationFrame(() => requestAnimationFrame(() => document.querySelector(".board")?.classList.add("is-in")));
  } else showAll();

  // ---------- the sundial ----------
  const dataEl = document.getElementById("dial-data");
  const dial = document.querySelector(".dial");
  let setHour = null;
  if (dataEl && dial) {
    const D = JSON.parse(dataEl.textContent);
    const pts = new Map(D.all.map(([m, p]) => [m % 1440, p]));
    const areaPts = Object.fromEntries(Object.entries(D.areas).map(([a, ps]) => [a, new Map(ps.map(([m, p]) => [m % 1440, p]))]));
    const at = (map, m) => { const lo = Math.floor(m / 30) * 30 % 1440, hi = (lo + 30) % 1440; const a = map.get(lo), b = map.get(hi); if (a == null) return null; if (b == null) return a; return a + (b - a) * ((m % 30) / 30); };
    const R0 = 46, R = 200;
    const ang = (h) => ((h / 24) * 360 + 180) * Math.PI / 180;           // midnight at the foot, noon at the crown
    const P = (h, r) => [Math.sin(ang(h)) * r, -Math.cos(ang(h)) * r];
    const wedges = dial.querySelector(".wedges"), marks = dial.querySelector(".marks");
    const fills = [];
    for (let h = 0; h < 24; h++) {
      const a0 = h + 0.04, a1 = h + 0.96;
      const arc = (r) => { const [x0, y0] = P(a0, r), [x1, y1] = P(a1, r); return [x0, y0, x1, y1]; };
      const wedge = (r) => { const [x0, y0, x1, y1] = arc(r), [u0, v0, u1, v1] = arc(R0);
        return `M${u0},${v0} L${x0},${y0} A${r},${r} 0 0 1 ${x1},${y1} L${u1},${v1} A${R0},${R0} 0 0 0 ${u0},${v0} Z`; };
      el("path", { d: wedge(R), class: "w-bg" }, wedges);
      const share = pts.get(h * 60);
      const f = el("path", { d: wedge(R0 + (R - R0) * ((share ?? 0) / 100)), class: "w-fill later" }, wedges);
      fills.push(f);
    }
    for (const [h, lab] of [[6, "6am"], [12, "noon"], [18, "6pm"], [0, "midnight"]]) {
      const [x, y] = P(h, R + 20);
      el("text", { x, y: y + 5, "text-anchor": h === 6 ? "end" : h === 18 ? "start" : "middle" }, marks).textContent = lab;
    }
    const gnomon = dial.querySelector(".gnomon");
    const tEl = document.querySelector(".sd-time"), sEl = document.querySelector(".sd-share"), aEl = document.querySelector(".sd-areas");
    const fmt = (m) => { const h = Math.floor(m / 60) % 24, mi = Math.round(m % 60 / 15) * 15 % 60; if (h === 0 && mi === 0) return "midnight"; if (h === 12 && mi === 0) return "noon";
      return `${h % 12 || 12}${mi ? ":" + String(mi).padStart(2, "0") : ""}${h < 12 ? "am" : "pm"}`; };  // clock minutes, taste-skill-ignore
    setHour = (m) => {
      const mm = ((m % 1440) + 1440) % 1440, h = mm / 60;
      const deg = (h / 24) * 360 + 180;
      gnomon.setAttribute("transform", `rotate(${deg})`);
      fills.forEach((f, i) => { const passed = ((i * 60 - 300 + 1440) % 1440) <= ((mm - 300 + 1440) % 1440); f.classList.toggle("later", !passed); });
      const s = at(pts, mm);
      tEl.textContent = fmt(mm);
      sEl.textContent = s == null ? "Few cafés list these hours" : `${Math.round(s)}% of cafés open`;
      aEl.textContent = Object.entries(areaPts).map(([a, mp]) => { const v = at(mp, mm); return v == null ? "" : `${a} ${Math.round(v)}%`; }).filter(Boolean).join(" · ");
    };
    setHour(480);
    if (reduce) fills.forEach((f) => f.classList.remove("later"));
  }

  // ---------- many into one ----------
  const many = document.querySelector(".many");
  if (many) {
    const nL = Math.min(170, Math.round((+many.dataset.listings || 2800) / 20));
    const nV = Math.round((+many.dataset.venues || 1100) / 20);
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const S = 11, G = 4;
    const ordered = [];
    for (let i = 0; i < nL; i++) {
      const x = 10 + rnd() * 360, y = 10 + rnd() * 240;
      el("rect", { x, y, width: S, height: S, fill: i % 3 ? "#cfcec9" : "#dddcd7" }, many);
    }
    for (let i = 0; i < 60; i++) {
      const col = Math.floor(i / 3), row = i % 3;
      el("rect", { x: 420 + col * (S + 3), y: 112 + row * (S + 3), width: S, height: S, fill: "#a3a29d" }, many);
    }
    const perRow = 12;
    for (let i = 0; i < nV; i++) {
      const col = i % perRow, row = Math.floor(i / perRow);
      const r = el("rect", { x: 900 + col * (S + G + 5), y: 30 + row * (S + G + 14), width: S, height: S, fill: "#b0533d" }, many);
      ordered.push(r);
    }
    if (motion) {
      ordered.forEach((r, i) => { r.style.transform = `translate(${-(+r.getAttribute("x") - 600)}px, ${130 - +r.getAttribute("y")}px)`; r.style.opacity = 0; r.style.transitionDelay = `${i * 14}ms`; });
      new IntersectionObserver(([e], o) => { if (!e.isIntersecting) return; ordered.forEach((r) => { r.style.transform = "none"; r.style.opacity = 1; }); o.disconnect(); },
        { rootMargin: "0px 0px -20% 0px" }).observe(many);
    }
  }

  // ---------- scroll-linked: sundial needle, photo drift ----------
  const sundial = document.querySelector(".sundial");
  const photo = document.querySelector(".mosaic .m-photo img");
  const bar = parseFloat(getComputedStyle(root).getPropertyValue("--bar-h")) || 64;
  let ticking = false;
  const frame = () => {
    ticking = false;
    if (sundial && setHour && root.classList.contains("motion")) {
      const r = sundial.getBoundingClientRect();
      const p = clamp((bar - r.top) / Math.max(1, r.height - (innerHeight - bar)));
      setHour(300 + p * 1320);                       // 5am to 3am
    }
    if (photo && root.classList.contains("motion")) {
      const r = photo.parentElement.getBoundingClientRect();
      const p = clamp((innerHeight - r.top) / (innerHeight + r.height));
      photo.style.setProperty("--drift", `${(0.5 - p) * 8}%`);
    }
  };
  const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
  addEventListener("scroll", request, { passive: true });
  addEventListener("resize", request);
  request();

  // ---------- what moved: tabs ----------
  const tabs = [...document.querySelectorAll(".tab")];
  tabs.forEach((t) => t.addEventListener("click", () => {
    tabs.forEach((x) => { const on = x === t; x.setAttribute("aria-selected", String(on)); document.getElementById(x.getAttribute("aria-controls")).hidden = !on; });
  }));

  // ---------- bar: mark the section in view ----------
  const links = [...document.querySelectorAll(".bar-links a")];
  if ("IntersectionObserver" in window && links.length) {
    const by = new Map(links.map((l) => [l.hash.slice(1), l]));
    const so = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((l) => l.removeAttribute("aria-current"));
      by.get(e.target.id)?.setAttribute("aria-current", "true");
    }), { rootMargin: "-45% 0px -50% 0px" });
    by.forEach((_, id) => { const s = document.getElementById(id); s && so.observe(s); });
  }
})();
