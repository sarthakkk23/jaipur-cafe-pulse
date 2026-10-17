// Benchmark tool. Runs entirely in the browser on the published aggregates embedded in the page.
// Nothing the visitor types is stored or sent anywhere.
(() => {
  const root = document.getElementById("benchmark");
  const dataEl = document.getElementById("pulse-data");
  if (!root || !dataEl) return;
  const D = JSON.parse(dataEl.textContent);
  const form = root.querySelector(".tool-form");
  const out = root.querySelector(".tool-results");
  const segs = [...root.querySelectorAll(".seg-btn")];
  let mode = "owner";

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const inr = (v) => "₹" + Math.round(v).toLocaleString("en-IN");
  const num = (v) => Math.round(v).toLocaleString("en-IN");
  const round5 = (p) => Math.min(95, Math.max(5, Math.round(p / 5) * 5));
  const clock = (m) => { const h = Math.floor(m / 60) % 24, mi = m % 60; return `${h % 12 || 12}${mi ? ":" + String(mi).padStart(2, "0") : ""}${h < 12 ? "am" : "pm"}`; };
  const typeWord = (t) => (t === "All-day café" ? "all-day cafés" : t === "Tea & chai" ? "tea & chai cafés" : `${t.toLowerCase()} cafés`);

  // position of x within a distribution given its 10th..90th percentiles
  function pctFromDeciles(x, dec) {
    if (!dec) return null;
    if (x < dec[0]) return 5;
    if (x >= dec[8]) return x === dec[8] ? 90 : 95;
    const lo = dec.findIndex((d) => d >= x), hi = dec.lastIndexOf(dec[lo]);
    if (dec[lo] === x) return round5(((lo + hi) / 2 + 1) * 10);
    const i = lo - 1;
    return round5((i + 1) * 10 + (10 * (x - dec[i])) / (dec[lo] - dec[i]));
  }

  const strip = (p, label, ends = ["fewer", "more"]) => `
    <div class="strip" role="img" aria-label="${esc(label)}">
      <span class="strip-mid"></span><span class="strip-dot" style="--x:${p}%"></span>
    </div><div class="strip-axis"><span>${ends[0]}</span><span>typical</span><span>${ends[1]}</span></div>`;

  const card = (kicker, big, body, extra = "") =>
    `<article class="res"><p class="res-k">${esc(kicker)}</p><p class="res-big">${big}</p><p class="res-body">${body}</p>${extra}</article>`;

  function values() {
    const f = new FormData(form);
    const n = (k) => { const v = parseFloat(f.get(k)); return Number.isFinite(v) ? v : null; };
    return { area: f.get("area"), type: f.get("type"), price: n("price"), reviews: n("reviews"),
             rating: n("rating"), open: n("open"), am: f.getAll("am") };
  }

  function priceCell(area, type) {
    return D.price.cells.find((c) => c.area === area && c.type === type);
  }

  function owner(v) {
    const cards = [];
    const cell = priceCell(v.area, v.type);

    if (v.price) {
      const dec = cell?.deciles || D.price.by_area[v.area]?.deciles;
      const scope = cell?.deciles ? `${typeWord(v.type)} in ${v.area}` : `cafés in ${v.area}`;
      const p = pctFromDeciles(v.price, dec);
      if (p != null) {
        const line = p >= 50 ? `${inr(v.price)} for two is above about <b>${p}%</b> of ${scope} on Zomato.`
                             : `${inr(v.price)} for two sits on the accessible side: about <b>${100 - p}%</b> of ${scope} charge more.`;
        const band = cell?.p25 != null ? ` Most charge ${inr(cell.p25)}–${inr(cell.p75)}.` : "";
        cards.push(card("Price", `${p}<small>th</small>`, line + band, strip(p, `Price position: ${p}th percentile`, ["lower", "higher"])));
      }
    }

    if (v.reviews != null) {
      const a = D.attention[v.area];
      const p = pctFromDeciles(v.reviews, a?.review_deciles);
      if (p != null) {
        const line = p >= 50 ? `${num(v.reviews)} Google reviews puts you ahead of about <b>${p}%</b> of cafés in ${v.area}.`
          : `Like most cafés, you're in the long tail: the typical café in ${v.area} has ${num(a.median_reviews)} reviews. Every new review moves you further here than it would at the top.`;
        cards.push(card("Attention", `${p}<small>th</small>`, line, strip(p, `Review count position: ${p}th percentile`)));
      }
    }

    if (v.rating != null && v.rating >= 1 && v.rating <= 5) {
      const r = v.reviews ?? 0;
      const b = D.ratings.find((x) => x.lo != null && r >= x.lo && r < x.hi);
      if (b && b.median_rating != null) {
        const med = b.median_rating.toFixed(1);
        const line = v.rating >= b.median_rating
          ? `Cafés with a similar number of reviews typically sit at <b>${med}</b>. You're at or above that.`
          : `Cafés with a similar number of reviews typically sit at <b>${med}</b>. Ratings move most in the first few hundred reviews, so there's room to grow.`;
        cards.push(card("Rating", v.rating.toFixed(1), line + (v.reviews == null ? " Add your review count for a closer comparison." : "")));
      }
    }

    if (v.open != null) {
      const cdf = D.open_cdf[v.type] || D.open_cdf.all;
      const i = D.open_cdf.slots.indexOf(v.open);
      if (i >= 0) {
        const s = cdf[i];
        const scope = D.open_cdf[v.type] ? typeWord(v.type) : "cafés";
        const line = s <= 50 ? `Only <b>${s}%</b> of ${scope} are open by ${clock(v.open)}. You're serving while most are still shut.`
                             : `About <b>${s}%</b> of ${scope} are open by ${clock(v.open)}. Before that, the field is thinner.`;
        cards.push(card("Mornings", clock(v.open), line));
      }
    }

    if (v.am.length) {
      const rows = v.am.map((k) => D.amenities.find((a) => a.key === k)).filter(Boolean).map((a) =>
        a.share == null ? `<li><b>${esc(a.label)}</b> listed by fewer than ${D.k} cafés. Rare: say it loudly.</li>`
          : `<li><b>${esc(a.label)}</b> listed by ${a.share}% of cafés on Zomato${a.share < 20 ? ". Uncommon: make sure your listings say it." : "."}</li>`).join("");
      cards.push(card("What you offer", `${v.am.length}`, `<ul class="res-list">${rows}</ul>`));
    }

    if (!cards.length) {
      return `<p class="tool-empty">Add a price, review count, rating or opening time to see where you sit.</p>`;
    }
    return cards.join("") + cta(v);
  }

  function planner(v) {
    const cards = [];
    const key = `${v.area}|${v.type}`;
    const n = D.counts[key];
    cards.push(card("The field", n == null ? `<${D.k}` : `${n}`,
      n == null ? `Fewer than ${D.k} ${typeWord(v.type)} operate in ${v.area}: an open lane.`
                : `${typeWord(v.type)[0].toUpperCase() + typeWord(v.type).slice(1)} already operating in ${v.area}.`));

    const cell = priceCell(v.area, v.type);
    if (cell?.median != null) {
      cards.push(card("Price band", inr(cell.median), `Typical cost for two. The middle half charge ${inr(cell.p25)}–${inr(cell.p75)}.`));
    } else {
      const ad = D.price.by_area[v.area];
      if (ad?.deciles) cards.push(card("Price band", inr(ad.deciles[4]), `Typical cost for two across all café types in ${v.area}; too few ${typeWord(v.type)} list a price to show their own band.`));
    }

    const cdf = D.open_cdf[v.type] || D.open_cdf.all;
    const at8 = cdf[D.open_cdf.slots.indexOf(480)], at9 = cdf[D.open_cdf.slots.indexOf(540)];
    cards.push(card("Mornings", `${at8}%`, `of ${D.open_cdf[v.type] ? typeWord(v.type) : "cafés"} are open by 8am, and ${at9}% by 9am. An early opening starts with less competition.`));

    const rare = [...D.amenities].sort((a, b) => (a.share ?? -1) - (b.share ?? -1)).slice(0, 4)
      .map((a) => `<li><b>${esc(a.label)}</b> ${a.share == null ? `fewer than ${D.k} cafés` : `${a.share}% of cafés`}</li>`).join("");
    cards.push(card("Rare on Zomato", "Gaps", `Features few cafés list:<ul class="res-list">${rare}</ul>`));

    if (D.demand.matcha) cards.push(card("Demand", `${D.demand.matcha}×`, `Rajasthan's search interest in matcha, 2025 against 2019. "Coffee" is at ${D.demand.coffee}×.`));
    return cards.join("") + cta(v);
  }

  function cta(v) {
    if (!D.email) return "";
    const lines = [`Area: ${v.area}`, `Type: ${v.type}`];
    if (mode === "owner") {
      if (v.price) lines.push(`Cost for two: ${inr(v.price)}`);
      if (v.reviews != null) lines.push(`Google reviews: ${num(v.reviews)}`);
      if (v.rating != null) lines.push(`Google rating: ${v.rating}`);
      if (v.open != null) lines.push(`Opens at: ${clock(v.open)}`);
    }
    const body = `Hi Sarthak,\n\nI used the benchmark on Jaipur Café Pulse.\n${lines.join("\n")}\n\n`;
    const href = `mailto:${D.email}?subject=${encodeURIComponent(D.subject + " — benchmark")}&body=${encodeURIComponent(body)}`;
    const head = mode === "owner" ? "Want the full picture, privately?" : "Opening soon?";
    const text = mode === "owner" ? "I'll put together a free private report on your café against your street. It isn't shared with anyone else."
                                  : "I'd love to hear what you're planning and what you'd want measured.";
    return `<article class="res res-cta"><p class="res-k">Next step</p><p class="res-head">${head}</p><p class="res-body">${text}</p>
      <a class="cta" href="${esc(href)}">Email me your numbers</a></article>`;
  }

  function render() {
    const v = values();
    out.innerHTML = mode === "owner" ? owner(v) : planner(v);
  }

  segs.forEach((b) => b.addEventListener("click", () => {
    mode = b.dataset.mode;
    segs.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    root.classList.toggle("planner", mode === "planner");
    render();
  }));
  form.addEventListener("input", render);
  form.addEventListener("change", render);
  form.addEventListener("submit", (e) => e.preventDefault());
  render();
})();
