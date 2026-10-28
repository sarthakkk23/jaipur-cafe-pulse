/* How the methods work: tap a method, read one plain sentence, and play with a small example.
   Every example uses invented numbers, labelled as such; none of them is data from the site.
   Shared by the Café Index (Method page) and the Jewellery Index (How I know). */
(() => {
  const root = document.querySelector("[data-explain]");
  if (!root) return;
  const tiles = [...root.querySelectorAll(".ex-tile")];
  const h = (tag, attrs = {}, kids = []) => {
    const e = document.createElement(tag);
    for (const k in attrs) k === "text" ? (e.textContent = attrs[k]) : e.setAttribute(k, attrs[k]);
    (Array.isArray(kids) ? kids : [kids]).forEach((c) => c && e.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return e;
  };
  const btn = (label, fn) => { const b = h("button", { type: "button", class: "btn ex-btn", text: label }); b.addEventListener("click", fn); return b; };
  const say = () => h("p", { class: "ex-out", "aria-live": "polite" });
  const tag = () => h("p", { class: "ex-tag", text: "Example: invented numbers, only to show the method." });
  const row = (label, value, max, hot) => {
    const r = h("div", { class: "ex-row" + (hot ? " hot" : "") });
    r.append(h("span", { class: "ex-l", text: label }));
    const t = h("span", { class: "ex-t" }); const b = h("i"); b.style.width = (100 * Math.max(0, value) / max) + "%"; t.append(b); r.append(t);
    r.append(h("b", { class: "ex-v", text: String(value) }));
    return r;
  };
  const median = (a) => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

  const demos = {
    median(box) {
      const base = [40, 55, 60, 72, 80, 95, 110, 120, 140];
      let data = [...base];
      const bars = h("div", { class: "ex-bars" }), out = say();
      const draw = () => {
        bars.textContent = "";
        const max = Math.max(...data);
        data.forEach((v, i) => bars.append(row(`Café ${i + 1}`, v, max, v === max && data.length > base.length)));
        out.innerHTML = `Average: <b>${Math.round(mean(data))}</b> reviews · Median: <b>${median(data)}</b> reviews`;
      };
      box.append(h("p", { text: "Nine cafés and their reviews. Add one very busy café and watch which number jumps." }), bars, out,
        h("p", { class: "ex-acts" }, [btn("Add a café with 2,000 reviews", () => { if (data.length === base.length) data.push(2000); draw(); }), btn("Reset", () => { data = [...base]; draw(); })]), tag());
      draw();
    },
    share(box) {
      const grid = h("div", { class: "ex-grid" }), out = say(), range = h("input", { type: "range", min: "0", max: "100", value: "67", "aria-label": "How many of 100" });
      const draw = () => {
        grid.textContent = "";
        for (let i = 0; i < 100; i++) grid.append(h("i", { class: i < +range.value ? "on" : "" }));
        out.innerHTML = `<b>${range.value}</b> of every 100 is <b>${range.value}%</b>. That's a share.`;
      };
      range.addEventListener("input", draw);
      box.append(h("p", { text: "A hundred squares, one for each of a hundred cafés or a hundred rupees of exports. Drag to colour some in." }), grid, range, out, tag());
      draw();
    },
    change(box) {
      const a = h("input", { type: "range", min: "50", max: "200", value: "100", "aria-label": "Last year" }), b = h("input", { type: "range", min: "50", max: "200", value: "131", "aria-label": "This year" });
      const bars = h("div", { class: "ex-bars" }), out = say();
      const draw = () => {
        bars.textContent = "";
        bars.append(row("Last year", +a.value, 200), row("This year", +b.value, 200, true));
        const c = 100 * (+b.value / +a.value - 1);
        out.innerHTML = `Change: (${b.value} ÷ ${a.value}) − 1 = <b>${c >= 0 ? "+" : "−"}${Math.abs(c).toFixed(1)}%</b>`;
      };
      [a, b].forEach((x) => x.addEventListener("input", draw));
      box.append(h("p", { text: "Same months, two years. Drag either bar." }), h("label", { class: "ex-lab" }, ["Last year ", a]), h("label", { class: "ex-lab" }, ["This year ", b]), bars, out, tag());
      draw();
    },
    window(box) {
      const m = [22, 31, 18, 27, 24, 4, 3, 5, 4, 11];
      const names = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"];
      const bars = h("div", { class: "ex-bars" }), out = say();
      let pick = "one";
      const draw = () => {
        bars.textContent = "";
        m.forEach((v, i) => bars.append(row(names[i], v, 35, pick === "one" ? i === 2 : i < 5)));
        out.innerHTML = pick === "one" ? `One month (Nov): <b>${m[2]}%</b>. A single month can swing.` : `Five months together (Sep–Jan): <b>${mean(m.slice(0, 5)).toFixed(1)}%</b>. Steadier.`;
      };
      box.append(h("p", { text: "A share that moves month to month. Compare one month with five together." }), bars, out,
        h("p", { class: "ex-acts" }, [btn("One month", () => { pick = "one"; draw(); }), btn("Five months together", () => { pick = "five"; draw(); })]), tag());
      draw();
    },
    rounding(box) {
      const parts = [46.4, 8.2, 38.3, 7.1];
      const out = say();
      const t = h("table", { class: "ex-table" });
      t.innerHTML = "<tr><th>Part</th><th>Exact</th><th>Rounded</th></tr>" + parts.map((p, i) => `<tr><td>Part ${i + 1}</td><td>${p.toFixed(1)}%</td><td>${Math.round(p)}%</td></tr>`).join("")
        + `<tr><th>Total</th><th>${parts.reduce((a, b) => a + b, 0).toFixed(1)}%</th><th>${parts.reduce((a, b) => a + Math.round(b), 0)}%</th></tr>`;
      out.innerHTML = "Each part is rounded on its own, so the rounded parts add to 99%, not 100%. Nothing is missing.";
      box.append(t, out, tag());
    },
    checked(box) {
      const steps = ["The figure is computed from the cleaned data.", "Separate code goes back to the raw tables and computes it again.", "The two must agree, or nothing is published.", "The source, period and caveat travel with the figure."];
      let i = 0;
      const list = h("ol", { class: "ex-steps" }), out = say();
      const draw = () => { list.textContent = ""; steps.slice(0, i + 1).forEach((s) => list.append(h("li", { text: s }))); out.textContent = i < steps.length - 1 ? "" : "Every number on the site has been through these four steps."; };
      box.append(list, out, h("p", { class: "ex-acts" }, [btn("Next step", () => { i = Math.min(steps.length - 1, i + 1); draw(); }), btn("Start again", () => { i = 0; draw(); })]));
      draw();
    },
    interval(box) {
      const data = [3, 5, 2, 8, 4, 6, 7, 3, 9, 5, 4, 6, 2, 7, 5, 8, 3, 6, 4, 5];
      const marks = h("div", { class: "ex-strip" }), out = say();
      const got = [];
      const draw = () => {
        marks.textContent = "";
        got.forEach((v) => { const d = h("i"); d.style.left = (100 * (v - 3) / 4) + "%"; marks.append(d); });
        if (got.length >= 20) {
          const s = [...got].sort((a, b) => a - b), lo = s[Math.floor(0.025 * s.length)], hi = s[Math.ceil(0.975 * s.length) - 1];
          out.innerHTML = `After ${got.length} resamples, 95% of averages fall between <b>${lo.toFixed(1)}</b> and <b>${hi.toFixed(1)}</b>. That's the interval.`;
        } else out.innerHTML = `${got.length} resamples so far. Each dot is one re-drawn average. Keep going.`;
      };
      const one = () => { const r = Array.from({ length: data.length }, () => data[Math.floor(rnd() * data.length)]); got.push(mean(r)); };
      box.append(h("p", { text: "Twenty cafés. Draw them again at random, with repeats, and take the average. Do it many times." }), marks,
        h("p", { class: "ex-axis" }, [h("span", { text: "3" }), h("span", { text: "5" }), h("span", { text: "7" })]), out,
        h("p", { class: "ex-acts" }, [btn("Resample once", () => { one(); draw(); }), btn("Resample 50 times", () => { for (let i = 0; i < 50; i++) one(); draw(); })]), tag());
      draw();
    },
    shuffle(box) {
      const a = [9, 7, 8, 10, 6, 9], b = [5, 6, 4, 7, 5, 6];
      const real = mean(a) - mean(b);
      let tries = 0, hits = 0;
      const out = say();
      const run = (n) => {
        for (let k = 0; k < n; k++) {
          const pool = [...a, ...b];
          for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
          const g = mean(pool.slice(0, 6)) - mean(pool.slice(6));
          tries++; if (Math.abs(g) >= Math.abs(real)) hits++;
        }
        out.innerHTML = `Real gap: <b>${real.toFixed(1)}</b>. Shuffled ${tries} times; luck alone matched it <b>${hits}</b> times (${(100 * hits / tries).toFixed(1)}%). Rarely by luck means the gap is likely real.`;
      };
      box.append(h("p", { text: "Two groups of six cafés with a gap between them. Shuffle the labels and see how often chance alone makes a gap this big." }), out,
        h("p", { class: "ex-acts" }, [btn("Shuffle once", () => run(1)), btn("Shuffle 1,000 times", () => run(1000))]), tag());
      out.innerHTML = `Real gap between the groups: <b>${real.toFixed(1)}</b>.`;
    },
    rank(box) {
      const xs = [1, 2, 3, 4, 5, 6, 7, 8];
      const sets = { "A clear link": [2, 1, 4, 3, 6, 5, 8, 7], "No link": [5, 2, 8, 1, 7, 3, 4, 6], "The opposite": [8, 7, 6, 5, 4, 3, 2, 1] };
      const svgNS = "http://www.w3.org/2000/svg", svg = document.createElementNS(svgNS, "svg"), out = say();
      svg.setAttribute("viewBox", "0 0 240 160"); svg.setAttribute("class", "ex-svg");
      const rho = (y) => 1 - 6 * xs.reduce((s, x, i) => s + (x - y[i]) ** 2, 0) / (8 * 63);
      const draw = (k) => {
        svg.textContent = "";
        sets[k].forEach((y, i) => { const c = document.createElementNS(svgNS, "circle"); c.setAttribute("cx", 20 + i * 28); c.setAttribute("cy", 150 - y * 17); c.setAttribute("r", 6); svg.append(c); });
        out.innerHTML = `${k}: rank correlation <b>${rho(sets[k]).toFixed(2)}</b>. +1 rises together, 0 no link, −1 opposite.`;
      };
      box.append(h("p", { text: "Eight cafés, ranked on two things. Pick a pattern." }), svg, out,
        h("p", { class: "ex-acts" }, Object.keys(sets).map((k) => btn(k, () => draw(k)))), tag());
      draw("A clear link");
    },
    likeforlike(box) {
      const bars = h("div", { class: "ex-bars" }), out = say();
      const draw = (k) => {
        bars.textContent = "";
        if (k === "all") { bars.append(row("With the feature", 300, 300, true), row("Without", 100, 300)); out.innerHTML = "Against all cafés the feature looks huge: <b>3×</b>. But cafés with it tend to be bigger and pricier too."; }
        else { bars.append(row("With the feature", 110, 300, true), row("Without", 100, 300)); out.innerHTML = "Against cafés of the same area, type and price, the gap shrinks to <b>+10%</b>. That's like for like."; }
      };
      box.append(h("p", { text: "Does a feature bring more reviews, or does it just come with bigger cafés?" }), bars, out,
        h("p", { class: "ex-acts" }, [btn("Against all cafés", () => draw("all")), btn("Against similar cafés", () => draw("like"))]), tag());
      draw("all");
    },
    cluster(box) {
      const svgNS = "http://www.w3.org/2000/svg", svg = document.createElementNS(svgNS, "svg"), out = say();
      svg.setAttribute("viewBox", "0 0 240 160"); svg.setAttribute("class", "ex-svg");
      const near = (p) => mean(p.map((a, i) => Math.min(...p.filter((_, j) => j !== i).map((b) => Math.hypot(a[0] - b[0], a[1] - b[1])))));
      const real = [[60, 50], [70, 58], [64, 66], [80, 52], [150, 100], [160, 92], [156, 110], [170, 104], [110, 40], [118, 46], [40, 120], [48, 126]];
      const draw = (p, label) => {
        svg.textContent = "";
        p.forEach(([x, y]) => { const c = document.createElementNS(svgNS, "circle"); c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", 5); svg.append(c); });
        out.innerHTML = `${label}: average distance to the nearest café <b>${near(p).toFixed(0)}</b> (units of the square).`;
      };
      box.append(h("p", { text: "Twelve cafés on a street map. Are they closer together than chance?" }), svg, out,
        h("p", { class: "ex-acts" }, [btn("The cafés as they are", () => draw(real, "As they are")),
          btn("Scatter them at random", () => draw(real.map(() => [10 + rnd() * 220, 10 + rnd() * 140]), "At random"))]), tag());
      draw(real, "As they are");
    },
    gini(box) {
      const range = h("input", { type: "range", min: "0", max: "100", value: "60", "aria-label": "How uneven" });
      const bars = h("div", { class: "ex-bars" }), out = say();
      const draw = () => {
        const t = +range.value / 100;
        const raw = Array.from({ length: 10 }, (_, i) => Math.pow(i + 1, 1 + 4 * t));
        const tot = raw.reduce((a, b) => a + b, 0), sh = raw.map((v) => 100 * v / tot);
        bars.textContent = ""; sh.slice().reverse().forEach((v, i) => bars.append(row(`Café ${i + 1}`, Math.round(v), Math.max(...sh), i === 0)));
        let g = 0; sh.forEach((a) => sh.forEach((b) => { g += Math.abs(a - b); })); g = g / (2 * 10 * 10 * mean(sh));
        out.innerHTML = `Gini: <b>${g.toFixed(2)}</b>. 0 means every café has the same share; near 1, one café has almost everything.`;
      };
      range.addEventListener("input", draw);
      box.append(h("p", { text: "Ten cafés sharing all the reviews. Drag from even to uneven." }), range, bars, out, tag());
      draw();
    },
  };

  tiles.forEach((t) => t.addEventListener("click", () => {
    const key = t.dataset.demo, open = t.getAttribute("aria-expanded") === "true";
    tiles.forEach((o) => o.setAttribute("aria-expanded", "false"));
    root.querySelectorAll(".ex-panel").forEach((p) => { p.hidden = true; });
    if (open) return;
    t.setAttribute("aria-expanded", "true");
    const panel = root.querySelector(`.ex-panel[data-for="${key}"]`);
    panel.hidden = false;
    const box = panel.querySelector(".ex-demo");
    if (!box.dataset.done && demos[key]) { demos[key](box); box.dataset.done = "1"; }
    panel.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }));
})();
