// Checks every local link, image and anchor in a rendered site folder.
//
//   node tools/check-links.mjs _preview
//
// External (http, mailto, data) links are listed in the summary count but not fetched.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";

const root = resolve(process.argv[2] || "_preview");

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name !== "site_libs") walk(p, out);
    } else if (name.endsWith(".html")) out.push(p);
  }
  return out;
}

const idsCache = new Map();
function idsOf(file) {
  if (!idsCache.has(file)) {
    const html = readFileSync(file, "utf8");
    idsCache.set(file, new Set([...html.matchAll(/\s(?:id|name)="([^"]+)"/g)].map((m) => m[1])));
  }
  return idsCache.get(file);
}

let checked = 0, external = 0;
const problems = [];
// Values that must never reach the published site (see _variables.yml).
const placeholders = ["example.com", "REPLACE-ME"];
for (const file of walk(root)) {
  const raw = readFileSync(file, "utf8");
  for (const p of placeholders) {
    if (raw.includes(p)) problems.push(`${relative(root, file)}: placeholder "${p}" is still in the page`);
  }
  const html = raw.replace(/<script[\s\S]*?<\/script>/g, "");
  for (const m of html.matchAll(/\s(?:href|src)="([^"]*)"/g)) {
    const raw = m[1].replace(/&amp;/g, "&");
    if (!raw || /^(https?:|mailto:|data:|javascript:|tel:)/i.test(raw)) { external++; continue; }
    checked++;
    const [pathPart, hash] = raw.split("#");
    const clean = decodeURIComponent(pathPart.split("?")[0]);
    let target = clean === "" ? file : clean.startsWith("/") ? join(root, clean) : resolve(dirname(file), clean);
    if (existsSync(target) && statSync(target).isDirectory()) target = join(target, "index.html");
    if (!existsSync(target)) { problems.push(`${relative(root, file)}: missing ${raw}`); continue; }
    if (hash && target.endsWith(".html") && !hash.startsWith("category=")) {
      if (!idsOf(target).has(decodeURIComponent(hash))) problems.push(`${relative(root, file)}: no anchor #${hash} in ${relative(root, target)}`);
    }
  }
}

console.log(`checked ${checked} local references in ${root} (${external} external skipped)`);
if (problems.length) {
  for (const p of [...new Set(problems)]) console.log("PROBLEM " + p);
  process.exit(1);
}
console.log("no broken local links, images, anchors, or leftover placeholders");
