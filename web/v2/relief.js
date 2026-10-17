// The landing object: café density across both areas, sculpted as a stone relief on a dark plinth, with the
// streets draped over it and the busiest ground in Pink City red. It turns slowly; drag to turn it yourself.
// Counts only: height is how many cafés stand close by, smoothed over about 200 metres.
import * as THREE from "three";

const host = document.querySelector(".hero-obj");
const dataEl = document.getElementById("relief-data");
if (host && dataEl) init().catch((e) => { console.error("relief:", e); host.classList.add("no-webgl"); });

async function init() {
  const probe = document.createElement("canvas");
  if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) { host.classList.add("no-webgl"); return; }
  const D = JSON.parse(dataEl.textContent);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canvas = host.querySelector(".relief"), labelsEl = host.querySelector(".relief-labels");
  const [rows, cols] = D.grid;
  const roads = await (await fetch("data/roads.json")).json();
  const [Wm, Hm] = roads.size_m, U = 1000;                          // one unit = 1 km
  const W = Wm / U, H = Hm / U, PEAK = 2.3, BASE = 0.55;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 200);

  // height field: lightly blurred, then sampled with a cubic so the slopes have no creases
  let v = D.all.map((x) => x / 255);
  const K = [1, 4, 6, 4, 1].map((x) => x / 16);
  const blur = (src, dx, dy) => src.map((_, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    return K.reduce((s, w, j) => { const rr = Math.min(rows - 1, Math.max(0, r + (j - 2) * dy)), cc = Math.min(cols - 1, Math.max(0, c + (j - 2) * dx)); return s + w * src[rr * cols + cc]; }, 0);
  });
  for (let k = 0; k < 2; k++) v = blur(blur(v, 1, 0), 0, 1);       // two passes: broad hills, not needles
  const peak = Math.max(...v); v = v.map((x) => x / peak);
  const cell = (c, r) => v[Math.min(rows - 1, Math.max(0, r)) * cols + Math.min(cols - 1, Math.max(0, c))];
  const cr = (p0, p1, p2, p3, t) => p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));
  const at = (gx, gz) => {                                          // gx 0..cols-1 west to east, gz 0..rows-1 north to south
    const x0 = Math.floor(gx), z0 = Math.floor(gz), fx = gx - x0, fz = gz - z0;
    const row = (r) => cr(cell(x0 - 1, r), cell(x0, r), cell(x0 + 1, r), cell(x0 + 2, r), fx);
    return Math.max(0, cr(row(z0 - 1), row(z0), row(z0 + 1), row(z0 + 2), fz));
  };
  const hAt = (x, z) => at((x / W + 0.5) * (cols - 1), (z / H + 0.5) * (rows - 1));

  // the relief: a finer mesh than the grid, so slopes read smooth
  const SX = 160, SZ = 330;
  const geo = new THREE.PlaneGeometry(W, H, SX, SZ); geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position, col = new Float32Array(pos.count * 3);
  const stone = new THREE.Color(0xe9e8e4), pink = new THREE.Color(0xe3ad9f), red = new THREE.Color(0xb0533d), tmp = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const h = hAt(pos.getX(i), pos.getZ(i));
    pos.setY(i, Math.pow(h, 0.75) * PEAK);
    if (h < 0.45) tmp.copy(stone).lerp(pink, h / 0.45); else tmp.copy(pink).lerp(red, Math.min(1, (h - 0.45) / 0.45));
    col.set([tmp.r, tmp.g, tmp.b], i * 3);
  }
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3)); geo.computeVertexNormals();
  const relief = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 }));

  // the plinth: a dark slab under the ground plane
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(W + 0.24, BASE, H + 0.24), new THREE.MeshStandardMaterial({ color: 0x161616, roughness: 0.7 }));
  plinth.position.y = -BASE / 2 - 0.002;

  // streets, draped on the relief
  const lp = [];
  roads.ways.slice(0, 2).forEach((list) => list.forEach((w) => {
    for (let i = 0; i + 3 < w.length; i += 2) {
      const x1 = w[i] / U - W / 2, z1 = w[i + 1] / U - H / 2, x2 = w[i + 2] / U - W / 2, z2 = w[i + 3] / U - H / 2;
      if (Math.max(Math.abs(x1), Math.abs(x2)) > W / 2 || Math.max(Math.abs(z1), Math.abs(z2)) > H / 2) continue;   // stay on the plinth
      lp.push(x1, Math.pow(hAt(x1, z1), 0.75) * PEAK + 0.012, z1, x2, Math.pow(hAt(x2, z2), 0.75) * PEAK + 0.012, z2);
    }
  }));
  const lg = new THREE.BufferGeometry(); lg.setAttribute("position", new THREE.Float32BufferAttribute(lp, 3));
  const streets = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0x161616, transparent: true, opacity: 0.32 }));

  const obj = new THREE.Group(); obj.add(relief, plinth, streets); scene.add(obj);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xf1ece6, 1.9));
  const sun = new THREE.DirectionalLight(0xfff6ee, 1.15);
  sun.position.set(-5, 10, 4);                                         // raking light shades the slopes; no cast shadows, which smeared
  scene.add(sun);

  // two quiet labels that ride with the object
  const toXZ = (lat, lon) => [((lon - D.bbox.lon[0]) / (D.bbox.lon[1] - D.bbox.lon[0]) - 0.5) * W, ((D.bbox.lat[1] - lat) / (D.bbox.lat[1] - D.bbox.lat[0]) - 0.5) * H];
  const labels = [["C-Scheme", 26.905, 75.806], ["Malviya Nagar", 26.853, 75.812], ["Jantar Mantar", 26.9247, 75.8245]].map(([name, la, lo]) => {
    const [x, z] = toXZ(la, lo); const n = document.createElement("span"); n.className = "relief-label"; n.textContent = name; labelsEl.appendChild(n);
    return { n, p: new THREE.Vector3(x, Math.pow(hAt(x, z), 0.75) * PEAK + 0.25, z) };
  });

  // turning: slow by itself, by hand when dragged, with a little inertia
  let yaw = -0.6, vel = reduce ? 0 : 0.0025, dragging = false, lastX = 0, visible = true, raf = 0;
  const pitch = 0.5, dist = 17;
  canvas.addEventListener("pointerdown", (e) => { dragging = true; lastX = e.clientX; canvas.setPointerCapture(e.pointerId); host.classList.add("touched"); });
  canvas.addEventListener("pointermove", (e) => { if (!dragging) return; const dx = e.clientX - lastX; lastX = e.clientX; yaw += dx * 0.008; vel = dx * 0.0008; kick(); });
  const up = () => { dragging = false; };
  canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h;
    camera.fov = w / h < 0.9 ? 34 : 26; camera.updateProjectionMatrix();
  }
  // scrolling past the hero turns the city a little further, so it answers the reader's first movement
  let scrollTurn = 0;
  addEventListener("scroll", () => { if (reduce) return; scrollTurn = Math.min(1.2, scrollY / 900); if (visible) kick(); }, { passive: true });
  function draw() {
    obj.rotation.y = yaw + scrollTurn;
    // keep the whole object in frame as it turns: its long side must fit the narrower field of view
    // fit the object's turning radius inside the narrower field of view, so no corner leaves the frame
    const half = Math.tan((camera.fov * Math.PI) / 360) * Math.min(1, camera.aspect), d = Math.max(dist, (1.0 * Math.hypot(W, H) / 2) / half);
    camera.position.set(0, Math.sin(pitch) * d, Math.cos(pitch) * d);
    camera.lookAt(0, -0.2, 0);
    renderer.render(scene, camera);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const l of labels) {
      const p = l.p.clone().applyMatrix4(obj.matrixWorld).project(camera);
      l.n.style.transform = `translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px) translate(-50%, -100%)`;
    }
  }
  function tick() {
    raf = 0;
    if (!dragging) { yaw += vel; vel += ((reduce ? 0 : 0.0025) - vel) * 0.03; }
    draw();
    if (visible && (vel !== 0 || dragging)) raf = requestAnimationFrame(tick);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(tick); };
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); }).observe(canvas);
  new ResizeObserver(() => { resize(); draw(); }).observe(canvas);
  resize(); draw(); host.classList.add("ready"); kick();
}
