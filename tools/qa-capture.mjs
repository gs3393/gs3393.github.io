// Screenshot + layout checks with real device emulation (Chrome DevTools Protocol).
// No npm dependencies: needs Node 22+ (global WebSocket, fetch) and a local Chrome.
//
//   node tools/qa-capture.mjs --base http://127.0.0.1:8765 --out _preview-assets/shots \
//        [--pages notes.html,notes/some-note.html] [--full]
//
// Why not `chrome --headless --window-size=390,...`? On Windows the window cannot be
// narrower than 500px, so the page lays out at 500px and the screenshot is just cropped.
// Emulation.setDeviceMetricsOverride gives a true 390px viewport.

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : "true"]);
    return acc;
  }, [])
);
const base = (args.base || "http://127.0.0.1:8765").replace(/\/$/, "");
const outDir = args.out || "_preview-assets/shots";
// Pages may be given without the leading slash ("notes.html,notes/x.html"). Git Bash on Windows
// rewrites arguments that start with "/" into Windows paths, so prefer that form there.
const pages = (args.pages || "/,notes.html,about.html,notes/diffusion-foundations.html,notes/jit-fd-loss-analysis.html")
  .split(",")
  .map((p) => (p.startsWith("/") ? p : "/" + p));
const fullPage = args.full === "true";
const port = Number(args.port || 9333);

const viewports = [
  { name: "wide", width: 1920, height: 1400, scale: 1, mobile: false },
  { name: "desktop", width: 1360, height: 1700, scale: 1, mobile: false },
  { name: "tablet", width: 768, height: 1400, scale: 1, mobile: true },
  { name: "mobile", width: 390, height: 1400, scale: 2, mobile: true },
];

const chromeCandidates = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);
const chromePath = chromeCandidates.find((p) => existsSync(p));
if (!chromePath) throw new Error("Chrome not found. Set CHROME_PATH.");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 0;
    const pending = new Map();
    const waiters = new Map();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error(msg.error.message)) : res(msg.result);
      } else if (msg.method && waiters.has(msg.method)) {
        waiters.get(msg.method)(msg.params);
        waiters.delete(msg.method);
      }
    };
    ws.onerror = (e) => reject(new Error("websocket error: " + (e.message || "")));
    ws.onopen = () =>
      resolve({
        send: (method, params = {}) =>
          new Promise((res, rej) => {
            const n = ++id;
            pending.set(n, { res, rej });
            ws.send(JSON.stringify({ id: n, method, params }));
          }),
        once: (method) => new Promise((res) => waiters.set(method, res)),
        close: () => ws.close(),
      });
  });
}

const probe = (expected) => `(async () => {
  const expected = ${expected};
  try { if (document.fonts && document.fonts.ready) await document.fonts.ready; } catch (e) {}
  try { if (window.MathJax && MathJax.startup && MathJax.startup.promise) await MathJax.startup.promise; } catch (e) {}
  await new Promise(r => setTimeout(r, 600));
  const vw = window.innerWidth;
  const doc = document.documentElement;
  const wide = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.right <= expected + 1) continue;
    // The fixed header and the footer only stretch to a viewport that something else widened.
    if (el.closest('#quarto-header, footer')) continue;
    // Ignore anything inside a container that scrolls on its own.
    let p = el.parentElement, scrolls = false;
    while (p && p !== document.body) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') { scrolls = true; break; }
      p = p.parentElement;
    }
    if (!scrolls) wide.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '') + ' right=' + Math.round(r.right));
    if (wide.length >= 12) break;
  }
  const body = getComputedStyle(document.body);
  return JSON.stringify({
    innerWidth: vw,
    scrollWidth: doc.scrollWidth,
    pageHeight: doc.scrollHeight,
    // With mobile emulation the layout viewport grows to fit wide content, so compare
    // against the emulated width rather than innerWidth.
    overflowX: doc.scrollWidth > expected + 1 || vw > expected + 1,
    wide,
    mathItems: document.querySelectorAll('mjx-container').length,
    mathErrors: document.querySelectorAll('mjx-merror').length,
    brokenImages: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src')),
    bodyFont: body.fontFamily.split(',')[0].trim(),
    bodyFontLoaded: document.fonts ? document.fonts.check('16px ' + body.fontFamily.split(',')[0].trim()) : null,
    bodySize: body.fontSize,
    background: body.backgroundColor,
  });
})()`;

const profile = mkdtempSync(join(tmpdir(), "qa-chrome-"));
const chrome = spawn(
  chromePath,
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"],
  { stdio: "ignore" }
);

let exitCode = 0;
try {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) break;
    } catch (e) {}
    await sleep(250);
  }
  mkdirSync(outDir, { recursive: true });
  const report = [];
  for (const page of pages) {
    for (const vp of viewports) {
      const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
      const cdp = await connect(target.webSocketDebuggerUrl);
      await cdp.send("Page.enable");
      await cdp.send("Emulation.setDeviceMetricsOverride", { width: vp.width, height: vp.height, deviceScaleFactor: vp.scale, mobile: vp.mobile });
      const loaded = cdp.once("Page.loadEventFired");
      await cdp.send("Page.navigate", { url: base + page });
      await Promise.race([loaded, sleep(20000)]);
      const res = await cdp.send("Runtime.evaluate", { expression: probe(vp.width), awaitPromise: true, returnByValue: true });
      const info = JSON.parse(res.result.value);
      const slug = (page === "/" ? "home" : page.replace(/^\//, "").replace(/\.html$/, "").replace(/[^a-z0-9]+/gi, "-")) + "-" + vp.name;
      const height = fullPage ? Math.min(info.pageHeight, 16000) : vp.height;
      const shot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: true,
        clip: { x: 0, y: 0, width: vp.width, height, scale: 1 },
      });
      writeFileSync(join(outDir, slug + ".png"), Buffer.from(shot.data, "base64"));
      report.push({ page, viewport: vp.name, ...info });
      const flag = info.overflowX || info.mathErrors || info.brokenImages.length ? "CHECK" : "ok";
      console.log(`${flag.padEnd(5)} ${vp.name.padEnd(7)} ${page}  vw=${info.innerWidth} sw=${info.scrollWidth} math=${info.mathItems}/${info.mathErrors}err img-broken=${info.brokenImages.length} font=${info.bodyFont}(${info.bodyFontLoaded}) ${info.wide.length ? "wide: " + info.wide.join(" | ") : ""}`);
      if (flag === "CHECK") exitCode = 1;
      await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`);
      cdp.close();
    }
  }
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
} finally {
  chrome.kill();
  await sleep(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch (e) {}
}
process.exit(exitCode);
