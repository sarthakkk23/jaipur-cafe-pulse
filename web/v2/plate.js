// The survey plate: OpenStreetMap streets engraved in ink, café density rising as red contour terraces,
// and a scroll-driven camera from Jantar Mantar to C-Scheme to Malviya Nagar. Counts only.
import * as THREE from "three";

const section = document.getElementById("map");
const tEl = document.getElementById("terrain-data");
if (section && tEl) init().catch(() => section.classList.add("no-webgl"));

async function init() {
  const probe = document.createElement("canvas");
  if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) { section.classList.add("no-webgl"); return; }
  const D = JSON.parse(tEl.textContent);
  const roads = await (await fetch("data/roads.json")).json();
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canvas = section.querySelector(".plate-canvas"), labelsEl = section.querySelector(".plate-labels");
  const stops = [...section.querySelectorAll(".stops li")];

  const [Wm, Hm] = roads.size_m, U = 100;                     // one world unit = 100 m
  const W = Wm / U, H = Hm / U;
  const toXZ = (lat, lon) => [((lon - roads.bbox.lon[0]) / (roads.bbox.lon[1] - roads.bbox.lon[0]) - 0.5) * W,
                              ((roads.bbox.lat[1] - lat) / (roads.bbox.lat[1] - roads.bbox.lat[0]) - 0.5) * H];

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0xe9e8e4);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xe9e8e4, 40, 140);
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 500);

  // streets, engraved: three weights by class, all ink
  const ink = [0.62, 0.42, 0.2];
  roads.ways.forEach((list, cls) => {
    const pos = [];
    for (const w of list) for (let i = 0; i + 3 < w.length; i += 2)
      pos.push(w[i] / U - W / 2, 0, w[i + 1] / U - H / 2, w[i + 2] / U - W / 2, 0, w[i + 3] / U - H / 2);
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    scene.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x161616, transparent: true, opacity: ink[cls] })));
  });

  // density contours by marching squares, lifted to their level: a terraced relief
  const [rows, cols] = D.grid, PEAK = 7;
  const LEVELS = [18, 40, 70, 105, 145, 190, 235];
  function contours(vals) {
    const pos = [];
    const gx = (c) => (c / (cols - 1) - 0.5) * W, gz = (r) => (r / (rows - 1) - 0.5) * H;
    for (const L of LEVELS) {
      const y = (L / 255) * PEAK;
      for (let r = 0; r < rows - 1; r++) for (let c = 0; c < cols - 1; c++) {
        const a = vals[r * cols + c], b = vals[r * cols + c + 1], d = vals[(r + 1) * cols + c], e = vals[(r + 1) * cols + c + 1];
        const idx = (a >= L) | ((b >= L) << 1) | ((e >= L) << 2) | ((d >= L) << 3);
        if (idx === 0 || idx === 15) continue;
        const t = (p, q) => (L - p) / ((q - p) || 1e-6);
        const top = [gx(c + t(a, b)), gz(r)], right = [gx(c + 1), gz(r + t(b, e))];
        const bottom = [gx(c + t(d, e)), gz(r + 1)], left = [gx(c), gz(r + t(a, d))];
        const segs = { 1: [[left, top]], 2: [[top, right]], 3: [[left, right]], 4: [[right, bottom]], 5: [[left, top], [right, bottom]],
          6: [[top, bottom]], 7: [[left, bottom]], 8: [[left, bottom]], 9: [[top, bottom]], 10: [[left, bottom], [top, right]],
          11: [[right, bottom]], 12: [[left, right]], 13: [[top, right]], 14: [[left, top]] }[idx];
        for (const [p, q] of segs) pos.push(p[0], y, p[1], q[0], y, q[1]);
      }
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    const lines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0xb0533d, transparent: true, opacity: 0 }));
    lines.add(surface(vals));
    return lines;
  }
  // the same density as a translucent pink relief under the terraces, so the hills read before the lines do
  function surface(vals) {
    const geo = new THREE.PlaneGeometry(W, H, cols - 1, rows - 1); geo.rotateX(-Math.PI / 2);
    const p = geo.attributes.position, col = new Float32Array(p.count * 4);
    const pink = new THREE.Color(0xe3ad9f), ground = new THREE.Color(0xe9e8e4);
    for (let i = 0; i < p.count; i++) {
      const v = vals[i] / 255;                                   // PlaneGeometry runs row by row from the north edge, as the grid does
      p.setY(i, v * PEAK - 0.04);
      const c = ground.clone().lerp(pink, Math.min(1, v * 1.6));
      col.set([c.r, c.g, c.b, Math.min(0.85, v * 2.2)], i * 4);
    }
    geo.setAttribute("color", new THREE.BufferAttribute(col, 4)); geo.computeVertexNormals();
    const m = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
    return new THREE.Mesh(geo, m);
  }
  const setOpacity = (obj, o) => { obj.material.opacity = o; obj.children.forEach((c) => (c.material.opacity = o)); };
  let current = null;
  const fades = [];
  function show(label) {
    const vals = D.frames[label]?.all;
    if (!vals) return;
    const next = contours(vals); scene.add(next);
    if (current) fades.push({ obj: current, from: current.material.opacity, to: 0, t: 0, drop: true });
    fades.push({ obj: next, from: 0, to: 1, t: 0 });
    current = next;
    if (reduce) { fades.forEach((f) => { setOpacity(f.obj, f.to); f.drop && scene.remove(f.obj); }); fades.length = 0; }
    draw();
  }

  // landmarks
  const marks = [["Jantar Mantar", 26.9247, 75.8247], ["Statue Circle", 26.9076, 75.8040], ["World Trade Park", 26.8537, 75.8050], ["MNIT", 26.8640, 75.8110]]
    .map(([name, la, lo]) => { const [x, z] = toXZ(la, lo); const n = document.createElement("span"); n.className = "plate-label"; n.textContent = name; labelsEl.appendChild(n);
      const dot = new THREE.Mesh(new THREE.CircleGeometry(0.28, 24), new THREE.MeshBasicMaterial({ color: 0x161616 })); dot.rotation.x = -Math.PI / 2; dot.position.set(x, 0.02, z); scene.add(dot);
      return { n, v: new THREE.Vector3(x, 0.6, z) }; });

  // camera stops: the instrument, then the two neighbourhoods
  const S = [toXZ(26.9190, 75.8200), toXZ(26.9119, 75.8040), toXZ(26.8540, 75.8130)];
  const VIEWS = [{ t: S[0], dist: 30, tilt: 0.45, turn: -0.35 },          // first from almost overhead, like a plate on a table; then it tilts into relief
                  { t: S[1], dist: 26, tilt: 0.9, turn: 0.1 }, { t: S[2], dist: 30, tilt: 0.85, turn: 0.45 }];
  const ease = (x) => x * x * (3 - 2 * x);
  let progress = reduce ? 0.5 : 0;
  function place() {
    const seg = Math.min(VIEWS.length - 2, Math.floor(progress * (VIEWS.length - 1)));
    const f = ease(clamp(progress * (VIEWS.length - 1) - seg));
    const a = VIEWS[seg], b = VIEWS[seg + 1];
    const lerp = (p, q) => p + (q - p) * f;
    const tx = lerp(a.t[0], b.t[0]), tz = lerp(a.t[1], b.t[1]);
    const dist = lerp(a.dist, b.dist), tilt = lerp(a.tilt, b.tilt), turn = lerp(a.turn, b.turn);
    camera.position.set(tx + Math.sin(turn) * Math.sin(tilt) * dist, Math.cos(tilt) * dist, tz + Math.cos(turn) * Math.sin(tilt) * dist);
    camera.lookAt(tx, 0, tz);
    const active = Math.round(progress * (VIEWS.length - 1));
    stops.forEach((s, i) => s.classList.toggle("on", i === active));
  }
  function clamp(v) { return Math.min(1, Math.max(0, v)); }
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  function draw() {
    place();
    renderer.render(scene, camera);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const m of marks) {
      const p = m.v.clone().project(camera);
      const vis = p.z < 1 && Math.abs(p.x) < 0.82 && p.y < 0.9 && p.y > -0.95;   // keep whole labels inside the plate
      m.n.style.transform = `translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px) translate(-50%, -140%)`;
      m.n.style.opacity = vis ? 1 : 0;
    }
  }
  let raf = 0;
  function tick() {
    raf = 0;
    let moving = false;
    for (let i = fades.length - 1; i >= 0; i--) {
      const f = fades[i]; f.t = Math.min(1, f.t + 0.06); setOpacity(f.obj, f.from + (f.to - f.from) * ease(f.t));
      if (f.t >= 1) { if (f.drop) { scene.remove(f.obj); f.obj.geometry.dispose(); f.obj.children.forEach((c) => c.geometry.dispose()); } fades.splice(i, 1); } else moving = true;
    }
    draw();
    if (moving) raf = requestAnimationFrame(tick);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(tick); };
  addEventListener("scroll", () => {
    if (reduce || !document.documentElement.classList.contains("motion")) return;
    const r = section.getBoundingClientRect(), bar = 64;               // matches --bar-h
    progress = clamp((bar - r.top) / Math.max(1, r.height - (innerHeight - bar)));
    kick();
  }, { passive: true });
  new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
  section.querySelectorAll("[data-snap]").forEach((b) => b.addEventListener("click", () => {
    section.querySelectorAll("[data-snap]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    show(b.dataset.snap); kick();
  }));
  resize();
  show(section.querySelector('[data-snap][aria-pressed="true"]')?.dataset.snap || Object.keys(D.frames).at(-1));
  kick();
}
