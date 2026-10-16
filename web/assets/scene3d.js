// Decorative 3D café objects (coffee cup, donut, beans), built procedurally — no model files.
// Purely ornamental: canvases are aria-hidden and the page is complete without them.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const GLOW = ["#0894ff", "#c959dd", "#ff2e54", "#ff9004", "#ffffff"];
const clamp = (v) => Math.min(1, Math.max(0, v));

// ---------- models ----------
function latteTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const g = c.getContext("2d");
  const rg = g.createRadialGradient(256, 256, 40, 256, 256, 256);
  rg.addColorStop(0, "#9a5f38");
  rg.addColorStop(0.75, "#7a4527");
  rg.addColorStop(1, "#4e2a16");
  g.fillStyle = rg;
  g.fillRect(0, 0, 512, 512);
  // a poured heart in milk foam
  g.filter = "blur(3px)";
  g.fillStyle = "#f4e6d4";
  g.beginPath();
  g.moveTo(256, 360);
  g.bezierCurveTo(140, 290, 120, 200, 180, 170);
  g.bezierCurveTo(222, 150, 250, 180, 256, 210);
  g.bezierCurveTo(262, 180, 290, 150, 332, 170);
  g.bezierCurveTo(392, 200, 372, 290, 256, 360);
  g.fill();
  g.filter = "blur(2px)";
  g.strokeStyle = "#f4e6d4";
  g.lineWidth = 7;
  g.beginPath();
  g.moveTo(256, 120);
  g.lineTo(256, 395);
  g.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function ceramic() {
  return new THREE.MeshPhysicalMaterial({ color: "#ffffff", roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.06 });
}

function makeCup() {
  const g = new THREE.Group();
  const prof = [[0, 0], [0.6, 0], [0.66, 0.04], [0.72, 0.26], [0.8, 0.64], [0.86, 1.0], [0.875, 1.045],
    [0.845, 1.06], [0.8, 1.0], [0.74, 0.64], [0.66, 0.3], [0.58, 0.12], [0, 0.12]]
    .map(([x, y]) => new THREE.Vector2(x, y));
  const body = new THREE.Mesh(new THREE.LatheGeometry(prof, 72), ceramic());
  g.add(body);
  const coffee = new THREE.Mesh(new THREE.CircleGeometry(0.778, 72),
    new THREE.MeshStandardMaterial({ map: latteTexture(), roughness: 0.32 }));
  coffee.rotation.x = -Math.PI / 2;
  coffee.position.y = 0.92;
  g.add(coffee);
  const arc = Math.PI * 1.2;
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.27, 0.065, 20, 48, arc), ceramic());
  handle.rotation.z = -arc / 2;
  handle.scale.set(1, 1.15, 1);
  handle.position.set(0.83, 0.56, 0);
  g.add(handle);
  const dish = [[0, -0.06], [0.62, -0.06], [1.22, 0.02], [1.34, 0.07], [1.32, 0.1], [1.2, 0.07], [0.64, 0.0], [0, 0.0]]
    .map(([x, y]) => new THREE.Vector2(x, y));
  g.add(new THREE.Mesh(new THREE.LatheGeometry(dish, 72), ceramic()));
  g.children.forEach((m) => (m.position.y -= 0.5));
  return g;
}

function makeDonut() {
  const g = new THREE.Group();
  const R = 0.62, r = 0.3;
  g.add(new THREE.Mesh(new THREE.TorusGeometry(R, r, 48, 120),
    new THREE.MeshPhysicalMaterial({ color: "#d99a5e", roughness: 0.72, sheen: 0.5, sheenColor: "#f6cf9b" })));

  // icing: a slightly fatter torus whose lower half is tucked inside the dough, with a wavy edge
  const edge = (u) => r * (-0.02 + 0.16 * Math.sin(5 * u) + 0.08 * Math.sin(11 * u + 1));
  const ig = new THREE.TorusGeometry(R, r * 1.06, 48, 120);
  const pos = ig.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const u = Math.atan2(v.y, v.x);
    if (v.z < edge(u)) {
      const c = new THREE.Vector3(R * Math.cos(u), R * Math.sin(u), 0);
      v.sub(c).multiplyScalar(0.9).add(c);
      pos.setXYZ(i, v.x, v.y, v.z);
    }
  }
  ig.computeVertexNormals();
  g.add(new THREE.Mesh(ig, new THREE.MeshPhysicalMaterial({ color: "#ffb9d2", roughness: 0.22, clearcoat: 0.7 })));

  // sprinkles in the site's glow colours
  const n = 90;
  const sp = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.017, 0.07, 4, 8),
    new THREE.MeshStandardMaterial({ roughness: 0.35 }), n);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(1, 1, 1), col = new THREE.Color();
  let placed = 0;
  for (let k = 0; placed < n && k < n * 20; k++) {
    const u = Math.random() * Math.PI * 2, t = 0.35 + Math.random() * 2.4;
    const z = r * 1.08 * Math.sin(t);
    if (z < edge(u) + 0.05) continue;
    const p = new THREE.Vector3((R + r * 1.08 * Math.cos(t)) * Math.cos(u), (R + r * 1.08 * Math.cos(t)) * Math.sin(u), z);
    q.setFromEuler(new THREE.Euler(Math.random() * 3, Math.random() * 3, Math.random() * 3));
    m.compose(p, q, s);
    sp.setMatrixAt(placed, m);
    sp.setColorAt(placed, col.set(GLOW[placed % GLOW.length]));
    placed++;
  }
  sp.count = placed;
  g.add(sp);
  return g;
}

function makeBean() {
  const geo = new THREE.SphereGeometry(0.16, 40, 28);
  const pos = geo.attributes.position, v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i).multiply(new THREE.Vector3(1, 0.72, 0.52));
    // one soft S-shaped groove down the flat side
    if (v.z > 0) {
      const d = (v.y - 0.012 * Math.sin(v.x * 16)) / 0.018;
      v.z -= 0.045 * Math.exp(-d * d) * (v.z / 0.083);
    }
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({ color: "#4a2816", roughness: 0.38, clearcoat: 0.5 }));
}

// ---------- layouts: where each object sits, as a fraction of the visible frame ----------
const LAYOUTS = {
  // tall = narrower than 5:4; objects then sit above and below the headline instead of beside it
  hero: () => [
    { obj: makeCup(), tilt: [0.5, -0.4, 0.08], spin: 0.12, bob: 0.08, drift: 0.9,
      at: (w, h, tall) => (tall ? [w * 0.24, -h * 0.3, 0.9] : [w * 0.38, -h * 0.16, 0.95]) },
    { obj: makeDonut(), tilt: [-1.05, 0.3, 0.4], spin: -0.1, bob: 0.1, drift: 1.2,
      at: (w, h, tall) => (tall ? [-w * 0.27, h * 0.33, 0.85] : [-w * 0.38, h * 0.12, 0.95]) },
    { obj: makeBean(), tilt: [0.4, 0.8, 0.3], spin: 0.5, bob: 0.06, drift: 1.8,
      at: (w, h, tall) => (tall ? [w * 0.33, h * 0.36, 1.4] : [-w * 0.26, -h * 0.34, 1.4]) },
    { obj: makeBean(), tilt: [-0.6, 0.2, 1.1], spin: -0.4, bob: 0.07, drift: 2.2,
      at: (w, h, tall) => (tall ? [-w * 0.34, -h * 0.38, 1.2] : [w * 0.22, h * 0.36, 1.2]) },
    { obj: makeBean(), tilt: [0.2, -0.5, -0.8], spin: 0.35, bob: 0.05, drift: 1.5,
      at: (w, h, tall) => (tall ? [w * 0.02, h * 0.42, 1.0] : [w * 0.44, h * 0.3, 1.0]) },
  ],
  coffee: () => [
    { obj: makeCup(), tilt: [0.55, -0.5, 0.06], spin: 0.18, bob: 0.06, drift: 0.6,
      at: (w, h) => [0, -h * 0.04, 1.25] },
    { obj: makeBean(), tilt: [0.4, 0.8, 0.3], spin: 0.5, bob: 0.06, drift: 1.2, at: (w, h) => [-w * 0.33, h * 0.3, 1.4] },
    { obj: makeBean(), tilt: [-0.6, 0.2, 1.1], spin: -0.45, bob: 0.07, drift: 1.6, at: (w, h) => [w * 0.34, -h * 0.32, 1.2] },
  ],
};

// ---------- mounting ----------
function mount(canvas) {
  const make = LAYOUTS[canvas.dataset.scene3d];
  if (!make) return;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const key = new THREE.DirectionalLight("#ffffff", 1.4); key.position.set(3, 5, 6); scene.add(key);
  const rimA = new THREE.DirectionalLight("#ff6fa3", 2.2); rimA.position.set(-6, 2, -3); scene.add(rimA);
  const rimB = new THREE.DirectionalLight("#4aa8ff", 2.2); rimB.position.set(6, -2, -3); scene.add(rimB);

  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  camera.position.set(0, 0, 10);
  const rig = new THREE.Group();
  scene.add(rig);
  const items = make().map((it, i) => {
    it.obj.rotation.set(...it.tilt);
    it.phase = i * 1.7;
    rig.add(it.obj);
    return it;
  });

  let place = [];
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const vh = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.position.z;
    const vw = vh * camera.aspect;
    const tall = camera.aspect < 1.25;
    // scale with the frame: 1 at a 16:9 desktop, smaller on narrow screens
    const k = canvas.dataset.scene3d !== "hero" ? 1 : tall ? Math.min(1, vw / 5.4) * 0.55 : Math.min(1, vw / 9.5);
    place = items.map((it) => { const [x, y, sc] = it.at(vw, vh, tall); return [x, y, sc * k]; });
    items.forEach((it, i) => {
      const [x, y, s] = place[i];
      it.obj.position.set(x, y, 0);
      it.obj.scale.setScalar(s);
    });
    renderer.render(scene, camera);   // a still frame straight away; the loop takes over when visible
  }

  let px = 0, py = 0, tx = 0, ty = 0;
  addEventListener("pointermove", (e) => {
    tx = (e.clientX / innerWidth - 0.5) * 2;
    ty = (e.clientY / innerHeight - 0.5) * 2;
  }, { passive: true });

  let visible = false, running = false;
  const clock = new THREE.Clock();
  function loop() {
    if (!visible || document.hidden) { running = false; return; }
    running = true;
    const t = clock.getElapsedTime();
    const r = canvas.getBoundingClientRect();
    const p = clamp((innerHeight - r.top) / (innerHeight + r.height)) - 0.5;   // -0.5..0.5 through the viewport
    px += (tx - px) * 0.05; py += (ty - py) * 0.05;
    rig.rotation.set(py * 0.12, px * 0.18, 0);
    items.forEach((it, i) => {
      const [x, y] = place[i] || [0, 0];
      it.obj.position.set(x, y + Math.sin(t * 0.9 + it.phase) * it.bob - p * it.drift, 0);
      it.obj.rotation.y = it.tilt[1] + t * it.spin + p * 2.2;
    });
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }
  const wake = () => { if (!running && visible && !reduce) { clock.getDelta(); requestAnimationFrame(loop); } };

  new ResizeObserver(resize).observe(canvas);
  resize();
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; wake(); }).observe(canvas);
  document.addEventListener("visibilitychange", wake);
  canvas.classList.add("is-ready");
}

try {
  const probe = document.createElement("canvas");
  if (probe.getContext("webgl2") || probe.getContext("webgl")) {
    document.querySelectorAll("canvas[data-scene3d]").forEach((c) => {
      try { mount(c); } catch (err) { c.remove(); }
    });
  }
} catch (err) { /* decorative only */ }
