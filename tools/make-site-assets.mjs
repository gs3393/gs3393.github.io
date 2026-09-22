// Generates the site's decorative assets. Deterministic: same seed, same files.
//
//   node tools/make-site-assets.mjs
//
// Writes:
//   assets/site/noise-to-order.svg   Home strip: scattered dots settle into a halftone image
//   assets/site/favicon.svg          3x3 dot mark using the same idea
//   _preview-assets/social-card.html Source page for the 1200x630 social card (see README note below)
//
// The social card PNG is a screenshot of social-card.html:
//   chrome --headless=new --hide-scrollbars --window-size=1200,630 \
//          --screenshot=assets/site/social-card.png _preview-assets/social-card.html

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

const INK_SOFT = [86, 99, 107]; // #56636B
const TEAL_DEEP = [19, 107, 111]; // #136B6F

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const lerp = (a, b, t) => a + (b - a) * t;
const smoothstep = (e0, e1, x) => {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
};
const hex = (rgb) => "#" + rgb.map((c) => Math.round(c).toString(16).padStart(2, "0")).join("");

// The "image" that emerges on the right: a few soft hills, read as halftone dot sizes.
function image(x, y) {
  const bumps = [
    [700, 96, 78, 0.8],
    [845, 40, 84, 1.0],
    [1000, 100, 92, 1.0],
    [1135, 36, 70, 0.95],
  ];
  let v = 0;
  for (const [cx, cy, s, amp] of bumps) {
    const d2 = (x - cx) ** 2 + ((y - cy) * 1.5) ** 2;
    v = Math.max(v, amp * Math.exp(-d2 / (2 * s * s)));
  }
  return clamp(v, 0, 1);
}

function strip({ width = 1200, height = 132, cols = 64, rows = 7, seed = 3393 } = {}) {
  const rand = mulberry32(seed);
  const dx = width / cols;
  const dy = height / rows;
  const dots = [];
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const lx = dx * (i + 0.5);
      const ly = dy * (j + 0.5);
      const s = smoothstep(0.06, 0.9, lx / width); // 0 = noise, 1 = order
      const spread = (1 - s) ** 1.5;
      const x = clamp(lx + (rand() * 2 - 1) * 44 * spread, 3, width - 3);
      const y = clamp(ly + (rand() * 2 - 1) * 34 * spread, 3, height - 3);
      const rNoise = 1.3 + rand() * 1.9;
      const rOrder = 1.0 + 5.6 * image(lx, ly);
      const r = lerp(rNoise, rOrder, s);
      const color = hex(INK_SOFT.map((c, k) => lerp(c, TEAL_DEEP[k], s)));
      const opacity = lerp(0.5, 0.94, s);
      dots.push(
        `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(2)}" fill="${color}" fill-opacity="${opacity.toFixed(2)}"/>`
      );
    }
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="presentation" aria-hidden="true">\n` +
    dots.join("\n") +
    "\n</svg>\n"
  );
}

function favicon() {
  // Left column scattered and small, right column aligned and bright.
  const dots = [
    [15, 20, 3.2, "#FCFBF8", 0.55], [33, 17, 4.4, "#FCFBF8", 0.8], [47, 18, 5.6, "#8FD6D8", 1],
    [21, 35, 2.8, "#FCFBF8", 0.55], [31, 32, 4.4, "#FCFBF8", 0.8], [47, 32, 5.6, "#8FD6D8", 1],
    [14, 47, 3.4, "#FCFBF8", 0.55], [32, 47, 4.4, "#FCFBF8", 0.8], [47, 46, 5.6, "#8FD6D8", 1],
  ];
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n` +
    `<rect width="64" height="64" rx="14" fill="#223942"/>\n` +
    dots
      .map(([x, y, r, f, o]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${f}" fill-opacity="${o}"/>`)
      .join("\n") +
    "\n</svg>\n"
  );
}

function socialCard(stripSvg) {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600&family=JetBrains+Mono:wght@500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=block" rel="stylesheet">
<style>
  html, body { margin: 0; width: 1200px; height: 630px; background: #FCFBF8; color: #1F2A30; }
  .card { box-sizing: border-box; width: 1200px; height: 630px; padding: 76px 84px 0; display: flex; flex-direction: column; }
  .brand { font: 500 30px "JetBrains Mono", monospace; letter-spacing: -.01em; color: #223942; }
  h1 { margin: 92px 0 0; font: 600 68px/1.12 "Source Serif 4", serif; letter-spacing: -.02em; color: #223942; max-width: 940px; }
  p { margin: 30px 0 0; font: 500 27px/1.4 Inter, sans-serif; color: #56636B; }
  .strip { margin-top: auto; margin-left: -84px; width: 1200px; padding-bottom: 38px; }
  .strip svg { display: block; width: 1200px; height: 132px; }
</style></head>
<body><div class="card">
  <div class="brand">gs3393</div>
  <h1>Notes on image generation research</h1>
  <p>Fundamentals · Paper reviews · Experiments</p>
  <div class="strip">${stripSvg}</div>
</div></body></html>
`;
}

const stripSvg = strip();
mkdirSync(join(root, "assets", "site"), { recursive: true });
mkdirSync(join(root, "_preview-assets"), { recursive: true });
writeFileSync(join(root, "assets", "site", "noise-to-order.svg"), stripSvg);
writeFileSync(join(root, "assets", "site", "favicon.svg"), favicon());
writeFileSync(join(root, "_preview-assets", "social-card.html"), socialCard(stripSvg));
console.log("wrote assets/site/noise-to-order.svg, assets/site/favicon.svg, _preview-assets/social-card.html");
