/* The playbook's calculators. Same formulas as pipeline/playbook_v2.py, which writes the default answer into each page,
   so the page reads correctly before (or without) this script. Nothing typed here leaves the browser. */
(() => {
  const inr = (n) => Math.round(n).toLocaleString("en-IN");
  const GST_FOOD = 5, GST_COMMISSION = 18;
  const calcs = {
    early: ({ cost, price, ingredients }) => {
      const keep = price / (1 + GST_FOOD / 100) - ingredients;
      if (keep <= 0) return "At this price each coffee loses money before staff and power. Check the price and the ingredient cost.";
      const n = Math.ceil(cost / keep);
      return `Each coffee keeps ₹${inr(keep)} after GST and ingredients, so you need <b>${n} ${n === 1 ? "coffee" : "coffees"} ` +
        `in the extra hours</b> to cover ₹${inr(cost)}. Every one after that is profit.`;
    },
    delivery: ({ price, commission, discount, packaging, ingredients }) => {
      const sale = price * (1 - discount / 100);
      const keep = sale - sale * commission / 100 * (1 + GST_COMMISSION / 100) - packaging - ingredients;
      const table = price - ingredients;
      const pct = (x) => (price ? Math.round(100 * x / price) : 0);
      return `On the app this item keeps <b>₹${inr(keep)} (${pct(keep)}% of its price)</b>. At a table it keeps ₹${inr(table)} (${pct(table)}%).`;
    },
    price: ({ old, new: next, ingredients }) => {
      const a = old - ingredients, b = next - ingredients;
      if (a <= 0 || b <= 0 || next <= old) return "Enter a new price above the current one, and both above the ingredient cost.";
      return `Each sale keeps ₹${inr(a)} now and ₹${inr(b)} after the rise. You can lose <b>${100 - Math.ceil(100 * a / b)} of every 100 sales</b> ` +
        `and still earn as much as before.`;
    },
    rent: ({ rent, share, bill, days }) => {
      const month = share ? rent / (share / 100) : 0;
      const day = days ? month / days : 0;
      const n = bill ? Math.ceil(day / bill) : 0;
      return `At ${share}% of sales, this rent needs <b>₹${inr(month)} a month</b>: ₹${inr(day)} a day, or <b>${n} tables a day</b> at ₹${inr(bill)}.`;
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
