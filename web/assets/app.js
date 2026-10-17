// Jaipur Café Pulse — progressive enhancement only. The page reads fine without this file.
(() => {
  window.__pulse = true;          // tells the head guard the script arrived
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const motion = !reduce && "IntersectionObserver" in window;
  if (motion) root.classList.add("motion");
  const clamp = (v) => Math.min(1, Math.max(0, v));

  // ---------- one-shot reveals (fade-ups, masked words, chart draw-in) ----------
  document.querySelectorAll(".chart.draw").forEach((fig) => {
    fig.querySelectorAll(".ln, .rng").forEach((el) => {
      const len = Math.ceil(el.getTotalLength ? el.getTotalLength() : 2000);
      el.style.setProperty("--len", len);
    });
    fig.querySelectorAll(".bar, .dot, .pt, .val").forEach((el, i) => el.style.setProperty("--i", i));
  });

  const once = [...document.querySelectorAll(".reveal, .split, .rise")];
  const revealAll = () => once.forEach((el) => el.classList.add("is-in"));
  if (motion) {
    // Safety net: some in-app browsers, background tabs and capture tools never run the observer.
    // If it hasn't reported within 2 s, show everything; the animation is a bonus, never a gate.
    let alive = false;
    setTimeout(() => { if (!alive) { root.classList.remove("motion", "js"); revealAll(); } }, 2000);
    const io = new IntersectionObserver((entries) => {
      alive = true;
      entries.filter((e) => e.isIntersecting).forEach((e, i) => {
        if (e.target.classList.contains("reveal")) e.target.style.transitionDelay = `${i * 90}ms`;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    once.forEach((el) => io.observe(el));
  } else {
    revealAll();
  }

  // ---------- scroll scenes: write --p on each [data-scene] ----------
  const scenes = [...document.querySelectorAll("[data-scene]")];
  const gallery = document.querySelector(".highlights .gallery");
  const pin = document.querySelector(".highlights .pin");
  const cards = gallery ? [...gallery.querySelectorAll(".hl-card")] : [];
  let ticking = false;

  const nav = document.querySelector(".localnav");
  function frame() {
    ticking = false;
    const vh = innerHeight, vw = innerWidth;
    const navH = nav ? nav.offsetHeight : 0;
    root.style.setProperty("--nav-h", `${navH}px`);
    for (const s of scenes) {
      const r = s.getBoundingClientRect();
      if (r.bottom < -vh || r.top > vh * 2) continue;
      const mode = s.dataset.scene;
      let p;
      if (mode === "pin") p = clamp((navH - r.top) / Math.max(1, r.height - (vh - navH)));
      else if (mode === "enter") p = clamp((vh - r.top) / (vh * 0.55));
      else p = clamp((vh - r.top) / (vh + r.height));
      s.style.setProperty("--p", p.toFixed(4));
      if (mode === "pin" && gallery && pin && s.contains(gallery)) {
        // travel until the last card sits as far from the right edge as the first sat from the left
        const last = cards.length ? cards[cards.length - 1].parentElement : null;
        const pad = parseFloat(getComputedStyle(gallery).paddingLeft) || 0;
        const dist = last ? Math.max(0, last.offsetLeft + last.offsetWidth + pad - pin.clientWidth) : 0;
        gallery.style.setProperty("--tx", `${(-p * dist).toFixed(1)}px`);
        for (const c of cards) {
          const b = c.getBoundingClientRect();
          const off = (b.left + b.width / 2 - vw / 2) / vw;        // -1..1 across the screen
          c.style.setProperty("--rot", `${(off * -9).toFixed(2)}deg`);
          c.style.setProperty("--sc", (1 - Math.min(Math.abs(off), 1) * 0.08).toFixed(3));
        }
      }
    }
  }
  const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
  if (motion) {
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", request);
    frame();
  }

  // ---------- copy the email address ----------
  document.querySelectorAll(".copy-btn[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "Copied";
      } catch {
        const sel = getSelection(), range = document.createRange();
        range.selectNodeContents(btn.previousElementSibling);
        sel.removeAllRanges(); sel.addRange(range);
        btn.textContent = "Selected, press Copy";
      }
      setTimeout(() => (btn.textContent = "Copy address"), 2200);
    });
  });

  // ---------- time machine ----------
  const tmData = document.getElementById("tm-data");
  if (tmData) {
    const H = JSON.parse(tmData.textContent);
    const now = document.querySelector(".tm-now");
    const stopsEl = [...document.querySelectorAll(".tm-stop")];
    const fmt = (v) => (v == null ? "—" : Math.round(v).toLocaleString("en-IN"));
    const delta = (a, b, money) => {
      if (a == null || b == null || a === b) return "";
      const d = b - a;
      return `<span class="tm-d ${d > 0 ? "up" : "down"}">${d > 0 ? "▲" : "▼"} ${money ? "₹" : ""}${fmt(Math.abs(d))}</span>`;
    };
    const show = (i) => {
      const h = H[i], p = H[i - 1];
      stopsEl.forEach((b, j) => b.setAttribute("aria-pressed", String(j === i)));
      const cell = (k, v, d) => `<div class="tm-stat"><span class="tm-sk">${k}</span><span class="tm-sv">${v}${d || ""}</span></div>`;
      const conf = h.core_confirmed ?? h.core, pconf = p ? (p.core_confirmed ?? p.core) : null;
      const rows = [cell("Confirmed cafés", fmt(conf), p && delta(pconf, conf))];
      for (const a of Object.keys(h.by_area)) rows.push(cell(`Confirmed · ${a}`, fmt(h.by_area[a]), p && delta(p.by_area[a], h.by_area[a])));
      rows.push(cell("All cafés seen (incl. single searches)", fmt(h.core)));
      if (h.median_reviews) for (const a of Object.keys(h.median_reviews))
        rows.push(cell(`Typical Google reviews · ${a}`, fmt(h.median_reviews[a]), p?.median_reviews && delta(p.median_reviews[a], h.median_reviews[a])));
      if (h.median_price) for (const a of Object.keys(h.median_price))
        rows.push(cell(`Typical cost for two · ${a}`, h.median_price[a] == null ? "—" : "₹" + fmt(h.median_price[a]), p?.median_price && delta(p.median_price[a], h.median_price[a], true)));
      now.innerHTML = `<p class="tm-when">Snapshot of ${new Date(h.captured_on).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}${p ? ", against the one before" : ""}</p><div class="tm-grid">${rows.join("")}</div>`;
      const snap = document.querySelector(`input[name="tr-snap"][value="${h.label}"]`);
      if (snap && !snap.checked) { snap.checked = true; snap.dispatchEvent(new Event("change", { bubbles: true })); }
    };
    stopsEl.forEach((b) => b.addEventListener("click", () => show(+b.dataset.i)));
    if (H.length) show(H.length - 1);
  }

  // ---------- share a section ----------
  document.querySelectorAll(".share[data-share]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = location.origin + location.pathname + btn.dataset.share;
      const title = btn.closest(".sec-head")?.querySelector(".eyebrow")?.textContent || document.title;
      try {
        if (navigator.share && matchMedia("(pointer: coarse)").matches) await navigator.share({ title: `${title} · ${document.title}`, url });
        else { await navigator.clipboard.writeText(url); btn.textContent = "Link copied"; }
      } catch { /* dismissed */ }
      setTimeout(() => (btn.textContent = "Share"), 2000);
    });
  });

  // ---------- buttons lean toward the pointer ----------
  if (motion && matchMedia("(pointer: fine)").matches) {
    document.querySelectorAll(".cta, .nav-cta").forEach((b) => {
      b.addEventListener("pointermove", (e) => {
        const r = b.getBoundingClientRect();
        b.style.transform = `translate(${((e.clientX - r.left) / r.width - 0.5) * 8}px, ${((e.clientY - r.top) / r.height - 0.5) * 6}px)`;
      });
      b.addEventListener("pointerleave", () => (b.style.transform = ""));
    });
  }

  // ---------- top nav: sliding active pill + reading progress ----------
  const links = [...document.querySelectorAll(".nav-links .nl[data-for]")];
  const navEl = document.querySelector(".nav-links");
  const ind = document.querySelector(".nl-ind");
  const prog = document.querySelector(".nav-progress i");
  const owner = new Map();
  links.forEach((l) => l.dataset.for.split(" ").forEach((id) => owner.set(id, l)));
  const moveInd = (l) => {
    links.forEach((x) => x.toggleAttribute("aria-current", x === l));
    if (!ind) return;
    if (!l) { ind.style.opacity = 0; return; }
    ind.style.opacity = 1;
    ind.style.transform = `translateX(${l.offsetLeft}px)`;
    ind.style.width = `${l.offsetWidth}px`;
    // keep the active link in view on narrow screens (scroll only the link row)
    if (navEl.scrollWidth > navEl.clientWidth)
      navEl.scrollTo({ left: l.offsetLeft - (navEl.clientWidth - l.offsetWidth) / 2, behavior: reduce ? "auto" : "smooth" });
  };
  if ("IntersectionObserver" in window && links.length) {
    let current = null;
    const so = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const l = e.target.id === "overview" ? null : owner.get(e.target.id) || current;
        if (l !== current) { current = l; moveInd(l); }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    ["overview", ...owner.keys()].forEach((id) => { const el = document.getElementById(id); if (el) so.observe(el); });
    addEventListener("resize", () => current && moveInd(current));
  }
  if (prog) {
    let pt = false;
    const progress = () => { pt = false; const max = document.documentElement.scrollHeight - innerHeight; prog.style.transform = `scaleX(${max > 0 ? Math.min(1, scrollY / max) : 0})`; };
    addEventListener("scroll", () => { if (!pt) { pt = true; requestAnimationFrame(progress); } }, { passive: true });
    progress();
  }

  // ---------- tooltips: enhance, never gate (every value is also in the table view) ----------
  const tip = document.querySelector(".tip");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const place = (x, y) => {
    const r = tip.getBoundingClientRect();
    tip.style.left = `${Math.min(Math.max(8, x + 14), innerWidth - r.width - 8)}px`;
    tip.style.top = `${Math.max(8, y - r.height - 14)}px`;
  };
  const show = (html, x, y) => { tip.innerHTML = html; tip.hidden = false; place(x, y); };
  const hide = () => { tip.hidden = true; };

  document.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("pointermove", (e) => show(esc(el.dataset.tip), e.clientX, e.clientY));
    el.addEventListener("pointerleave", hide);
    el.addEventListener("focus", () => { const r = el.getBoundingClientRect(); show(esc(el.dataset.tip), r.left + r.width / 2, r.top); });
    el.addEventListener("blur", hide);
  });

  // line charts: crosshair + all-series readout at the nearest time
  document.querySelectorAll("rect.hit[data-line]").forEach((hit) => {
    const svg = hit.ownerSVGElement;
    const cross = svg.querySelector(".cross");
    const d = JSON.parse(hit.dataset.line);
    let idx = -1;
    const render = (i, cx, cy) => {
      idx = i;
      cross.setAttribute("x1", d.x[i]); cross.setAttribute("x2", d.x[i]); cross.classList.add("on");
      const rows = d.series.map((s) =>
        `<div class="row"><i style="background:var(--series-${s.cls === "s1" ? 1 : 2})"></i>${esc(s.name)}: <b>${s.values[i]}%</b></div>`).join("");
      show(`<div>${esc(d.labels[i])}, share of cafés open</div>${rows}`, cx, cy);
    };
    const nearest = (x) => d.x.reduce((b, v, i) => (Math.abs(v - x) < Math.abs(d.x[b] - x) ? i : b), 0);
    hit.addEventListener("pointermove", (e) => {
      const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(svg.getScreenCTM().inverse());
      render(nearest(pt.x), e.clientX, e.clientY);
    });
    hit.addEventListener("pointerleave", () => { cross.classList.remove("on"); hide(); });
    hit.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const i = Math.min(d.x.length - 1, Math.max(0, (idx < 0 ? 0 : idx) + (e.key === "ArrowRight" ? 1 : -1)));
      const r = hit.getBoundingClientRect();
      render(i, r.left + (i / (d.x.length - 1)) * r.width, r.top);
    });
    hit.addEventListener("blur", () => { cross.classList.remove("on"); hide(); });
  });
})();
