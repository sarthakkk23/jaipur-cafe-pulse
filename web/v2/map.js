// The map: OpenStreetMap streets, parks and water engraved on a stone plate, with a hexagonal column for every
// 300-metre cell. Height is the number of cafés inside. Hover or tap a column for what that cell's cafés have in
// common (shares only where a cell holds k cafés or more). Drag to orbit; Ctrl/⌘ + scroll or the buttons to zoom.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const section = document.getElementById("map");
const dataEl = document.getElementById("map-data");
if (section && dataEl) init().catch((e) => { console.error("map:", e); section.classList.add("no-webgl"); });

async function init() {
  const probe = document.createElement("canvas");
  if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) { section.classList.add("no-webgl"); return; }
  const D = JSON.parse(dataEl.textContent);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stage = section.querySelector(".stage"), canvas = section.querySelector(".stage-canvas"), labelsEl = section.querySelector(".stage-labels");
  const ro = section.querySelector(".readout");
  const [roads, parks] = await Promise.all([fetch("data/roads.json").then((r) => r.json()), fetch("data/parks.json").then((r) => r.json())]);
  const [Wm, Hm] = roads.size_m, U = 100;                           // one unit = 100 m
  const W = Wm / U, H = Hm / U;
  const bb = roads.bbox;
  const toXZ = (lat, lon) => [((lon - bb.lon[0]) / (bb.lon[1] - bb.lon[0]) - 0.5) * W, ((bb.lat[1] - lat) / (bb.lat[1] - bb.lat[0]) - 0.5) * H];

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0xe9e8e4);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xe9e8e4, 120, 260);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 600);

  // ground, parks and water
  // the ground matches the clear colour exactly; a separate catcher takes the columns' shadows
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(W * 4, H * 3), new THREE.MeshBasicMaterial({ color: 0xe9e8e4 }));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  const catcher = new THREE.Mesh(new THREE.PlaneGeometry(W * 4, H * 3), new THREE.ShadowMaterial({ opacity: 0.16 }));
  catcher.rotation.x = -Math.PI / 2; catcher.position.y = 0.025; catcher.receiveShadow = true; scene.add(catcher);
  const poly = (flat, color, y) => {
    const s = new THREE.Shape();
    for (let i = 0; i < flat.length; i += 2) { const x = flat[i] / U - W / 2, z = flat[i + 1] / U - H / 2; i ? s.lineTo(x, -z) : s.moveTo(x, -z); }
    const g = new THREE.ShapeGeometry(s); g.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color })); m.position.y = y; scene.add(m);
  };
  parks.parks.forEach((p) => poly(p, 0xdcdcd3, 0.01));
  parks.water.forEach((p) => poly(p, 0xc9d5e2, 0.015));

  // streets in three weights
  const ink = [0.55, 0.36, 0.17];
  roads.ways.forEach((list, cls) => {
    const p = [];
    for (const w of list) for (let i = 0; i + 3 < w.length; i += 2) p.push(w[i] / U - W / 2, 0.03, w[i + 1] / U - H / 2, w[i + 2] / U - W / 2, 0.03, w[i + 3] / U - H / 2);
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(p, 3));
    scene.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x161616, transparent: true, opacity: ink[cls] })));
  });

  // hex columns
  const cells = D.hexes.cells, R = (D.hexes.size_m / U) * 0.9;
  const colGeo = new THREE.CylinderGeometry(R, R, 1, 6); colGeo.translate(0, 0.5, 0);
  const colMat = new THREE.MeshStandardMaterial({ roughness: 0.8, metalness: 0 });
  const cols = new THREE.InstancedMesh(colGeo, colMat, cells.length);
  cols.castShadow = true; cols.receiveShadow = true;
  const PER = 0.42;                                               // world units of height per café
  const stone = new THREE.Color(0xdddcd7), pink = new THREE.Color(0xe3ad9f), red = new THREE.Color(0xb0533d), hot = new THREE.Color(0x161616);
  const xz = cells.map((c) => toXZ(c.lat, c.lon));
  let type = "All", cur = cells.map(() => 0), target = cells.map((c) => c.n), hover = -1;
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3(), cc = new THREE.Color();
  function paint() {
    const mx = Math.max(1, ...target);
    cells.forEach((c, i) => {
      const h = Math.max(0.05, cur[i] * PER);
      ps.set(xz[i][0], 0.04, xz[i][1]); sc.set(1, h, 1); m4.compose(ps, q, sc); cols.setMatrixAt(i, m4);
      const t = target[i] / mx;
      if (i === hover) cc.copy(hot); else if (t < 0.4) cc.copy(stone).lerp(pink, t / 0.4); else cc.copy(pink).lerp(red, (t - 0.4) / 0.6);
      cols.setColorAt(i, cc);
    });
    cols.instanceMatrix.needsUpdate = true; cols.instanceColor.needsUpdate = true;
    cols.computeBoundingSphere();
  }
  scene.add(cols);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xd6d1c8, 1.2));
  const sun = new THREE.DirectionalLight(0xfff3e6, 2.2);
  sun.position.set(-40, 70, 30); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, near: 1, far: 220 });
  sun.shadow.bias = -0.0005; scene.add(sun);

  // landmarks
  const marks = D.marks.map(([name, la, lo]) => {
    const [x, z] = toXZ(la, lo); const n = document.createElement("span"); n.className = "stage-label"; n.textContent = name; labelsEl.appendChild(n);
    return { name, n, v: new THREE.Vector3(x, 0.4, z) };
  });

  let raf = 0, visible = false;
  function kick() { if (!raf) raf = requestAnimationFrame(frame); }

  // camera and controls
  const controls = new OrbitControls(camera, renderer.domElement);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, enableZoom: false, maxPolarAngle: 1.3, minPolarAngle: 0.2, minDistance: 18, maxDistance: 170, screenSpacePanning: false });
  controls.touches = { ONE: null, TWO: THREE.TOUCH.DOLLY_ROTATE };
  renderer.domElement.style.touchAction = "pan-y";
  const center = (la, lo) => { const [x, z] = toXZ(la, lo); return new THREE.Vector3(x, 0, z); };
  const VIEWS = [
    { t: center(26.884, 75.810), d: 128, polar: 0.82, az: -0.3 },
    { t: center(26.905, 75.807), d: 50, polar: 0.95, az: 0.35 },
    { t: center(26.855, 75.810), d: 66, polar: 0.9, az: -0.45 },
  ];
  const place = (v) => { camera.position.copy(v.t).add(new THREE.Vector3(Math.sin(v.polar) * Math.sin(v.az), Math.cos(v.polar), Math.sin(v.polar) * Math.cos(v.az)).multiplyScalar(v.d)); controls.target.copy(v.t); };
  place(VIEWS[0]);
  let fly = null;
  function flyTo(v) {
    const from = { p: camera.position.clone(), t: controls.target.clone() };
    const save = { p: camera.position.clone(), t: controls.target.clone() }; place(v);
    const to = { p: camera.position.clone(), t: controls.target.clone() }; camera.position.copy(save.p); controls.target.copy(save.t);
    if (reduce) { camera.position.copy(to.p); controls.target.copy(to.t); kick(); return; }
    fly = { from, to, t: 0 }; kick();
  }
  function zoom(f) {
    const d = camera.position.clone().sub(controls.target);
    const len = Math.min(controls.maxDistance, Math.max(controls.minDistance, d.length() * f));
    camera.position.copy(controls.target).add(d.setLength(len)); kick();
  }
  canvas.addEventListener("wheel", (e) => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); zoom(Math.exp(e.deltaY * 0.0022)); }, { passive: false });
  section.querySelectorAll("[data-zoom]").forEach((b) => b.addEventListener("click", () => zoom(b.dataset.zoom === "1" ? 1.3 : 1 / 1.3)));
  section.querySelectorAll("[data-fly]").forEach((b) => b.addEventListener("click", () => flyTo(VIEWS[+b.dataset.fly])));
  section.querySelectorAll("[data-type]").forEach((b) => b.addEventListener("click", () => {
    section.querySelectorAll("[data-type]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    type = b.dataset.type; target = cells.map((c) => (type === "All" ? c.n : c.types ? c.types[type] : 0.4));
    if (hover >= 0) show(hover);
    kick();
  }));

  // the readout
  const nearest = (c) => D.marks.reduce((a, m) => { const d = (m[1] - c.lat) ** 2 + ((m[2] - c.lon) * 0.89) ** 2; return d < a[0] ? [d, m[0]] : a; }, [Infinity, ""])[1];
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const MIXC = { "Coffee-led": "var(--red)", "Tea & chai": "var(--sky)", Bakery: "var(--pink)", "All-day café": "var(--stone-2)" };
  function show(i) {
    const c = cells[i];
    const split = type !== "All" && !c.types;
    const n = type === "All" ? c.n : split ? c.n : c.types[type];
    let html = `<p class="ro-k">Near ${esc(nearest(c))}</p><p class="ro-big">${n} <span>${type === "All" || split ? (n === 1 ? "café" : "cafés") : esc(type.toLowerCase()) + (n === 1 ? " café" : " cafés")}</span></p>`;
    if (c.mix) {
      html += `<div class="ro-mix" role="img" aria-label="Type mix">${Object.entries(c.mix).map(([t, v]) => `<i style="flex:${v};background:${MIXC[t]}" title="${esc(t)} ${v}%"></i>`).join("")}</div>`;
      html += `<ul class="ro-list">${Object.entries(c.mix).map(([t, v]) => `<li><span><i style="background:${MIXC[t]}"></i>${esc(t)}</span><b>${v}%</b></li>`).join("")}`;
      if (c.open_by_8 != null) html += `<li><span>Open by 8am</span><b>${c.open_by_8}%</b></li>`;
      if (c.price != null) html += `<li><span>Typical cost for two</span><b>₹${c.price.toLocaleString("en-IN")}</b></li>`;
      if (c.reviews != null) html += `<li><span>Typical Google reviews</span><b>${c.reviews.toLocaleString("en-IN")}</b></li>`;
      html += `</ul><p class="ro-foot">${c.n} cafés in this cell.</p>`;
    } else {
      html += `<p class="ro-foot">${c.n} ${c.n === 1 ? "café" : "cafés"} in this cell. The split by type, and every share, appears only where a cell holds ${D.k} or more.</p>`;
    }
    ro.innerHTML = html; ro.classList.add("on");
  }
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  let downAt = null;
  function pick(e) {
    const r = canvas.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObject(cols)[0];
    const i = hit ? hit.instanceId : -1;
    if (i !== hover) { hover = i; if (i >= 0) show(i); canvas.style.cursor = i >= 0 ? "pointer" : "grab"; kick(); }
  }
  canvas.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse" && !e.buttons) pick(e); });
  canvas.addEventListener("pointerdown", (e) => { downAt = [e.clientX, e.clientY]; stage.classList.add("touched"); });
  canvas.addEventListener("pointerup", (e) => { if (downAt && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 6) pick(e); downAt = null; });
  controls.addEventListener("change", kick);

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  const ease = (x) => 1 - Math.pow(1 - x, 3);
  function frame() {
    raf = 0;
    let moving = false;
    for (let i = 0; i < cells.length; i++) {
      const d = target[i] - cur[i];
      if (Math.abs(d) > 0.01) { cur[i] += reduce ? d : d * 0.12; moving = true; } else cur[i] = target[i];
    }
    if (fly) {
      fly.t = Math.min(1, fly.t + 1 / 70); const e = ease(fly.t);
      camera.position.lerpVectors(fly.from.p, fly.to.p, e); controls.target.lerpVectors(fly.from.t, fly.to.t, e);
      if (fly.t >= 1) fly = null; moving = true;
    }
    if (controls.update()) moving = true;
    paint();
    renderer.render(scene, camera);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const m of marks) {
      const p = m.v.clone().project(camera);
      const vis = p.z < 1 && Math.abs(p.x) < 0.9 && p.y < 0.72 && p.y > -0.85;   // clear of the controls and the zoom buttons
      m.n.style.transform = `translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px) translate(-50%, -140%)`;
      m.n.style.opacity = vis ? 1 : 0;
    }
    if (moving && visible) raf = requestAnimationFrame(frame);
  }
  // the columns rise once, when the map first comes into view
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); }, { threshold: 0.15 }).observe(canvas);
  new ResizeObserver(() => { resize(); kick(); }).observe(canvas);
  resize(); paint(); renderer.render(scene, camera); stage.classList.add("ready");
}
