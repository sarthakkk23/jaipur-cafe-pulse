// "The map": café-density terrain (counts only), scroll-driven camera, morphs between snapshots.
import * as THREE from "three";

const section = document.getElementById("map");
const dataEl = document.getElementById("terrain-data");
if (section && dataEl) {
  try { init(); } catch (e) { section.classList.add("no-webgl"); }
}

function init() {
  const D = JSON.parse(dataEl.textContent);
  const canvas = section.querySelector(".tr-canvas");
  const labelsEl = section.querySelector(".tr-labels");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const probe = document.createElement("canvas");
  if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) { section.classList.add("no-webgl"); return; }

  const [rows, cols] = D.grid;
  const mlat = 111320, mlon = 111320 * Math.cos((26.88 * Math.PI) / 180);
  const Hm = (D.bbox.lat[1] - D.bbox.lat[0]) * mlat, Wm = (D.bbox.lon[1] - D.bbox.lon[0]) * mlon;
  const H = 10, W = (H * Wm) / Hm, PEAK = 1.9;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight("#ffffff", "#d9d9e3", 1.6));
  const sun = new THREE.DirectionalLight("#ffffff", 1.6); sun.position.set(-4, 8, 6); scene.add(sun);
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);

  const geo = new THREE.PlaneGeometry(W, H, cols - 1, rows - 1);
  geo.rotateX(-Math.PI / 2);               // lie flat; row 0 (north) ends up at -z
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const land = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.55, metalness: 0.05 }));
  scene.add(land);
  const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: "#1d1d1f", wireframe: true, transparent: true, opacity: 0.06 }));
  wire.position.y = 0.002;
  scene.add(wire);

  // colour ramp: paper -> blue -> violet -> pink -> orange (the site's glow)
  const stops = ["#f5f5f7", "#0894ff", "#c959dd", "#ff2e54", "#ff9004"].map((c) => new THREE.Color(c));
  const ramp = (t) => {
    const x = Math.min(0.9999, Math.max(0, t)) * (stops.length - 1), i = Math.floor(x);
    return stops[i].clone().lerp(stops[i + 1], x - i);
  };

  const cur = new Float32Array(rows * cols), target = new Float32Array(rows * cols);
  let kind = "all", label = Object.keys(D.frames).at(-1);
  const setTarget = () => {
    const f = D.frames[label]?.[kind];
    if (!f) return;
    for (let i = 0; i < f.length; i++) target[i] = f[i] / 255;
    if (reduce) cur.set(target);
  };
  const apply = () => {
    const c = new THREE.Color();
    for (let i = 0; i < cur.length; i++) {
      pos.setY(i, Math.pow(cur[i], 0.8) * PEAK);
      c.copy(ramp(Math.pow(cur[i], 0.7)));
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
    }
    pos.needsUpdate = true; geo.attributes.color.needsUpdate = true; geo.computeVertexNormals();
  };

  // area labels, projected from map coordinates
  const toXZ = ([la, lo]) => [((lo - D.bbox.lon[0]) / (D.bbox.lon[1] - D.bbox.lon[0]) - 0.5) * W,
                              ((D.bbox.lat[1] - la) / (D.bbox.lat[1] - D.bbox.lat[0]) - 0.5) * H];
  const labels = Object.entries(D.areas).map(([name, ll]) => {
    const el = document.createElement("span"); el.className = "tr-label"; el.textContent = name; labelsEl.appendChild(el);
    const [x, z] = toXZ(ll);
    return { el, v: new THREE.Vector3(x, PEAK + 0.35, z) };
  });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // leave room for the copy: map sits right of it on wide screens, below it on narrow ones
    if (w / h < 0.9) camera.setViewOffset(w, h, 0, -h * 0.2, w, h);
    else camera.setViewOffset(w, h, -w * Math.min(0.22, 360 / w), 0, w, h);
    camera.updateProjectionMatrix();
  }

  // camera path: top-down map -> tilted fly-over, driven by scroll through the pinned section
  const ease = (t) => t * t * (3 - 2 * t);
  function place() {
    const r = section.getBoundingClientRect();
    const nav = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--nav-h")) || 0;
    const p = reduce ? 0.7 : ease(Math.min(1, Math.max(0, (nav - r.top) / Math.max(1, r.height - innerHeight + nav))));
    const narrow = camera.aspect < 0.9;
    const dist = narrow ? 18 : 14;
    const tilt = 0.02 + p * 0.95, turn = -0.25 + p * 0.9;
    camera.position.set(Math.sin(turn) * Math.sin(tilt) * dist, Math.cos(tilt) * dist, Math.cos(turn) * Math.sin(tilt) * dist + 0.01);
    camera.lookAt(0, 0, 0);
  }

  function frameLabels() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const l of labels) {
      const v = l.v.clone().project(camera);
      l.el.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -100%)`;
      l.el.style.opacity = v.z < 1 ? 1 : 0;
    }
  }

  let visible = false, running = false;
  function loop() {
    if (!visible || document.hidden) { running = false; return; }
    running = true;
    let moving = false;
    for (let i = 0; i < cur.length; i++) {
      const d = target[i] - cur[i];
      if (Math.abs(d) > 0.002) { cur[i] += d * 0.08; moving = true; } else cur[i] = target[i];
    }
    if (moving) apply();
    place(); frameLabels();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }
  const wake = () => { if (visible && !running) requestAnimationFrame(loop); };

  section.querySelectorAll('input[name="tr-kind"]').forEach((i) => i.addEventListener("change", () => { kind = i.value; setTarget(); if (reduce) apply(); draw(); wake(); }));
  section.querySelectorAll('input[name="tr-snap"]').forEach((i) => i.addEventListener("change", () => { label = i.value; setTarget(); if (reduce) apply(); draw(); wake(); }));
  const draw = () => { place(); frameLabels(); renderer.render(scene, camera); };

  new ResizeObserver(() => { resize(); draw(); }).observe(canvas);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; wake(); }).observe(section);
  document.addEventListener("visibilitychange", wake);
  setTarget(); cur.set(target); apply(); resize(); draw();
  canvas.classList.add("is-ready");
}
