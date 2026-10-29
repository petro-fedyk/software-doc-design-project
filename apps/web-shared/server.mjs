import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = resolve(fileURLToPath(new URL(".", import.meta.url)));
export function startPortal({ root, defaultPort, name, roles }) {
root = resolve(root);
const port = Number(process.env.FRONTEND_PORT || defaultPort);
const apiOrigin = new URL(process.env.API_ORIGIN || "http://127.0.0.1:8000");
const mime = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp" };

createServer(async (req, res) => {
  const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (requestUrl.pathname === "/api" || requestUrl.pathname.startsWith("/api/")) {
    try {
      if (!roles.includes("CUSTOMER") && requestUrl.pathname === "/api/auth/register/") {
        res.writeHead(403, { "content-type": "application/json" });
        res.end(JSON.stringify({ detail: "Реєстрація доступна лише в магазині." }));
        return;
      }
      const chunks = [];
      if (! ["GET", "HEAD"].includes(req.method || "GET")) {
        for await (const chunk of req) chunks.push(Buffer.from(chunk));
      }
      const payload = chunks.length ? Buffer.concat(chunks) : undefined;
      const upstream = await fetch(new URL(`${requestUrl.pathname}${requestUrl.search}`, apiOrigin), {
        method: req.method,
        headers: { "content-type": req.headers["content-type"] || "application/json", accept: req.headers.accept || "application/json", authorization: req.headers.authorization || "", cookie: req.headers.cookie || "" },
        body: payload,
      });
      if (requestUrl.pathname === "/api/auth/token/" && upstream.ok) {
        const session = await upstream.json();
        const identityResponse = await fetch(new URL("/api/me/", apiOrigin), { headers: { authorization: `Bearer ${session.access}` } });
        if (!identityResponse.ok) throw new Error("Identity validation failed");
        const identity = await identityResponse.json();
        const allowed = roles.includes(identity.role);
        res.writeHead(allowed ? 200 : 403, { "content-type": "application/json", "cache-control": "no-store" });
        res.end(JSON.stringify(allowed ? session : { detail: "Цей обліковий запис не має доступу до вибраного порталу." }));
        return;
      }
      res.writeHead(upstream.status, Object.fromEntries(upstream.headers));
      if (upstream.body) for await (const chunk of upstream.body) res.write(chunk);
      res.end();
    } catch (error) {
      res.writeHead(502, { "content-type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ detail: `API proxy failed: ${error.message}` }));
    }
    return;
  }
  let pathname;
  try { pathname = decodeURIComponent(requestUrl.pathname); } catch { res.writeHead(400).end("Invalid path"); return; }
  const staticRoot = pathname.startsWith("/web-shared/") ? here : root;
  if (pathname.startsWith("/web-shared/")) pathname = pathname.slice("/web-shared".length);
  if (staticRoot === here && !["/api.js", "/auth.js", "/ui.js", "/localize.js"].includes(pathname)) { res.writeHead(404).end("Not found"); return; }
  let file = resolve(staticRoot, `.${pathname === "/" ? "/index.html" : pathname}`);
  if (file !== staticRoot && !file.startsWith(`${staticRoot}${sep}`)) { res.writeHead(403).end("Forbidden"); return; }
  if (!existsSync(file) || !statSync(file).isFile()) { res.writeHead(404).end("Not found"); return; }
  res.writeHead(200, { "content-type": mime[file.slice(file.lastIndexOf("."))] || "application/octet-stream", "cache-control": "no-store", "x-content-type-options": "nosniff" });
  createReadStream(file).pipe(res);
}).listen(port, process.env.FRONTEND_HOST || "127.0.0.1", () => console.log(`${name}: http://127.0.0.1:${port} (API proxy: ${apiOrigin.origin}/api/)`));

}
