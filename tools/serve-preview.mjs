// Static file server for the rendered preview, with correct MIME types.
//
//   node tools/serve-preview.mjs [--dir _preview] [--port 8765]
//
// Why not `python -m http.server`? On this Windows machine Python maps .js to
// text/plain, and browsers refuse to run ES modules served that way. Quarto's
// quarto.js is a module, so the TOC scrollspy, reader mode, footnote tooltips
// and category links all silently stop in such a preview while they are fine
// on GitHub Pages.

import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => {
    if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : "true"]);
    return acc;
  }, [])
);
const root = resolve(args.dir || "_preview");
const port = Number(args.port || 8765);

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".py": "text/plain; charset=utf-8",
  ".pdf": "application/pdf",
};

const server = createServer((req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let file = normalize(join(root, urlPath));
  if (!file.startsWith(root + sep) && file !== root) { res.writeHead(403); res.end(); return; }
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!existsSync(file)) {
    const notFound = join(root, "404.html");
    res.writeHead(404, { "Content-Type": types[".html"] });
    if (existsSync(notFound)) createReadStream(notFound).pipe(res); else res.end("404");
    return;
  }
  res.writeHead(200, { "Content-Type": types[extname(file).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" });
  createReadStream(file).pipe(res);
});

server.listen(port, "127.0.0.1", () => {
  console.log(`serving ${root} at http://127.0.0.1:${port}/`);
});
