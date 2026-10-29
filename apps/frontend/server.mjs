import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = resolve(fileURLToPath(new URL(".", import.meta.url)));
const root = resolve(here);
const port = Number(process.env.FRONTEND_PORT || 4173);
const apiOrigin = new URL(process.env.API_ORIGIN || "http://127.0.0.1:8000");
const mime = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp" };

createServer(async (req, res) => {
  const requestUrl = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (requestUrl.pathname === "/api" || requestUrl.pathname.startsWith("/api/")) {
    try {
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
  let file = resolve(root, `.${pathname === "/" ? "/index.html" : pathname}`);
  if (file !== root && !file.startsWith(`${root}${sep}`)) { res.writeHead(403).end("Forbidden"); return; }
  if (!existsSync(file) || !statSync(file).isFile()) file = resolve(root, "index.html");
  res.writeHead(200, { "content-type": mime[file.slice(file.lastIndexOf("."))] || "application/octet-stream", "cache-control": "no-store", "x-content-type-options": "nosniff" });
  createReadStream(file).pipe(res);
}).listen(port, "127.0.0.1", () => console.log(`Frontend: http://127.0.0.1:${port} (API proxy: ${apiOrigin.origin}/api/)`));
