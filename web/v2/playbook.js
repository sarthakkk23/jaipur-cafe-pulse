/* The playbook's three calculators. Same formulas as pipeline/playbook_v2.py, which writes the default answer into the page,
   so the page reads correctly before (or without) this script. Nothing typed here leaves the browser. */
(() => {
  const inr = (n) => Math.round(n).toLocaleString("en-IN");
  const GST = 18;
  const calcs = {
    early: ({ cost, bill, keep }) => {
      const per = bill * keep / 100;
      const n = per > 0 ? Math.ceil(cost / per) : 0;
      return `You'd need about <b>${n} extra ${n === 1 ? "bill" : "bills"} a day</b> in those hours to cover the cost. Every bill after that is profit.`;
    },
    delivery: ({ order, commission, discount, packaging, food }) => {
      const base = order - discount;
      const fee = base * commission / 100 * (1 + GST / 100);
      const foodCost = order * food / 100;
      const left = base - fee - packaging - foodCost;
      const dine = order - foodCost;
      const pct = (x) => (order ? Math.round(100 * x / order) : 0);
      return `A ₹${inr(order)} order leaves you <b>₹${inr(left)} (${pct(left)}%)</b> after commission, its GST, your discount, packaging ` +
        `and ingredients. The same order eaten in leaves ₹${inr(dine)} (${pct(dine)}%), before rent and staff in both cases.`;
    },
    rent: ({ rent, share, bill, days }) => {
      const month = share ? rent / (share / 100) : 0;
      const day = days ? month / days : 0;
      const bills = bill ? Math.ceil(day / bill) : 0;
      return `To keep rent at ${share}% of sales, the spot has to sell <b>₹${inr(month)} a month</b>: about ₹${inr(day)} a day, ` +
        `or ${bills} bills a day at ₹${inr(bill)}.`;
    },
  };
  document.querySelectorAll("form.calc[data-calc]").forEach((form) => {
    const fn = calcs[form.dataset.calc];
    const out = form.querySelector(".calc-out");
    if (!fn || !out) return;
    const run = () => {
      const v = {};
      for (const i of form.querySelectorAll("input[name]")) {
        const x = parseFloat(i.value);
        if (!Number.isFinite(x) || x < 0) { out.textContent = "Enter a number of zero or more in each box."; return; }
        v[i.name] = x;
      }
      out.innerHTML = fn(v);
    };
    form.addEventListener("input", run);
    run();                                         // the browser may have refilled the boxes on a return visit
    window.addEventListener("pageshow", run);
  });
})();
