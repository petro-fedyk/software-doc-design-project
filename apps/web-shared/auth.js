import { api } from "./api.js";
const portal = document.querySelector('meta[name="portal"]')?.content === "management" ? "management" : "customer";
const storageKey = `pharmacy.${portal}.session`;
let accessToken = null, expiration = 0, currentUser = null, expirationTimer = 0;
function readStored() { try { return JSON.parse(globalThis.sessionStorage?.getItem(storageKey) || "null"); } catch { return null; } }
export const auth = {
  get token() {
    if (accessToken && expiration && Date.now() >= expiration) { this.clear(); window.dispatchEvent(new CustomEvent("auth-expired")); return null; }
    return accessToken;
  },
  get user() { return currentUser; },
  async signIn(username, password) {
    const result = await api.request("/auth/token/", { method: "POST", auth: false, body: { username, password } });
    this.save(result);
    try { return await this.loadUser(); } catch(error) { this.clear(); throw error; }
  },
  async register(payload) {
    if (portal !== "customer") throw new Error("Реєстрація недоступна у службовому порталі.");
    const result = await api.request("/auth/register/", { method: "POST", auth: false, body: payload });
    this.save(result);
    return this.loadUser();
  },
  save(result) {
    accessToken = result.access;
    expiration = result.expires_at || Date.now() + Number(result.expires_in || 0) * 1000;
    try { globalThis.sessionStorage?.setItem(storageKey, JSON.stringify({access: accessToken, expires_at: expiration})); } catch {}
    clearTimeout(expirationTimer);
    if (expiration > Date.now()) expirationTimer = setTimeout(() => { this.clear(); window.dispatchEvent(new CustomEvent("auth-expired")); }, expiration - Date.now());
  },
  async loadUser() {
    const user = await api.request("/me/");
    const allowed = portal === "management" ? ["STAFF", "ADMIN"] : ["CUSTOMER"];
    if (!allowed.includes(user.role)) {
      this.clear();
      throw new Error(portal === "management" ? "Доступ лише для працівників і адміністратора. Обліковий запис покупця не має службових прав." : "Це вхід покупця. Для працівників і адміністратора відкрийте службовий портал на порту 4174.");
    }
    currentUser = user;
    return user;
  },
  clear() { clearTimeout(expirationTimer); accessToken = null; expiration = 0; currentUser = null; try { globalThis.sessionStorage?.removeItem(storageKey); } catch {} },
};
const stored = readStored();
if (stored?.access && stored.expires_at > Date.now()) auth.save(stored);
else auth.clear();
window.pharmacyAuth = auth;
