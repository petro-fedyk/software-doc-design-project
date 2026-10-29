import test from "node:test";
import assert from "node:assert/strict";

globalThis.document = { querySelector: () => ({ content: "/api" }) };
const events = [];
globalThis.window = {
  pharmacyAuth: { token: "test-access-token" },
  dispatchEvent: (event) => events.push(event.type),
};
globalThis.CustomEvent = class CustomEvent { constructor(type) { this.type = type; } };
const { api, ApiError } = await import("../src/api.js");

test("API client sends bearer token and JSON body", async () => {
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url, init };
    return new Response('{"ok":true}', { status: 200, headers: { "content-type": "application/json" } });
  };
  assert.deepEqual(await api.request("/cart/", { method: "PUT", body: { product_id: 3, quantity: 2 } }), { ok: true });
  assert.equal(captured.init.headers.Authorization, "Bearer test-access-token");
  assert.deepEqual(JSON.parse(captured.init.body), { product_id: 3, quantity: 2 });
  assert.equal(captured.url, "/api/cart/");
});

test("API client dispatches session expiry for 401", async () => {
  events.length = 0;
  globalThis.fetch = async () => new Response('{"detail":"Invalid token"}', { status: 401 });
  await assert.rejects(api.request("/me/"), (error) => error instanceof ApiError && error.status === 401);
  assert.deepEqual(events, ["auth-expired"]);
});

test("API client distinguishes forbidden response from unauthenticated response", async () => {
  events.length = 0;
  globalThis.fetch = async () => new Response('{"detail":"Forbidden"}', { status: 403 });
  await assert.rejects(api.request("/admin/users/"), (error) => error.status === 403 && error.message.includes("403"));
  assert.deepEqual(events, []);
});

test("API client reports network failures without leaking internals", async () => {
  globalThis.fetch = async () => { throw new TypeError("socket closed"); };
  await assert.rejects(api.request("/products/", { auth: false }), (error) => error.status === 0 && error.message.includes("API аптеки"));
});
