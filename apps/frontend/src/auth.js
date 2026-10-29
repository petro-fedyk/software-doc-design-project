import { api } from "./api.js";

let accessToken = null;
let expiration = 0;
let currentUser = null;
let expirationTimer = 0;

export const auth = {
  get token() {
    if (accessToken && expiration && Date.now() >= expiration) {
      this.clear();
      window.dispatchEvent(new CustomEvent("auth-expired"));
      return null;
    }
    return accessToken;
  },
  get user() { return currentUser; },
  async signIn(username, password) {
    const result = await api.request("/auth/token/", { method: "POST", auth: false, body: { username, password } });
    this.save(result);
    return this.loadUser();
  },
  async register(payload) {
    const result = await api.request("/auth/register/", { method: "POST", auth: false, body: payload });
    this.save(result);
    return this.loadUser();
  },
  save(result) {
    accessToken = result.access;
    expiration = Date.now() + Number(result.expires_in || 0) * 1000;
    clearTimeout(expirationTimer);
    if (expiration > Date.now()) expirationTimer = setTimeout(() => {
      this.clear();
      window.dispatchEvent(new CustomEvent("auth-expired"));
    }, expiration - Date.now());
  },
  async loadUser() {
    currentUser = await api.request("/me/");
    return currentUser;
  },
  clear() {
    clearTimeout(expirationTimer);
    accessToken = null;
    expiration = 0;
    currentUser = null;
  },
};

window.pharmacyAuth = auth;
