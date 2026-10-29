const API_ROOT = (document.querySelector('meta[name="api-base"]')?.content || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function formatError(data, status) {
  if (data && typeof data === "object") {
    if (typeof data.detail === "string") return data.detail;
    if (typeof data.code === "string") return data.code.replaceAll("_", " ").toLowerCase();
    return Object.entries(data).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : typeof value === "object" ? JSON.stringify(value) : value}`).join(" · ");
  }
  return typeof data === "string" && data ? data : `HTTP ${status}`;
}

export const api = {
  async request(path, { method = "GET", body, auth = true, timeout = 12000 } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const token = auth ? window.pharmacyAuth?.token : null;
    if (token) headers.Authorization = `Bearer ${token}`;
    let response;
    try {
      response = await fetch(`${API_ROOT}${path}`, {
        method, headers, credentials: "same-origin",
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(timeout),
      });
    } catch (error) {
      const message = error.name === "TimeoutError" || error.name === "AbortError"
        ? "Сервер не відповів вчасно. Спробуйте ще раз."
        : "Не вдалося з’єднатися з API аптеки. Перевірте з’єднання.";
      throw new ApiError(message, 0, error);
    }
    const raw = await response.text();
    let data = null;
    if (raw) { try { data = JSON.parse(raw); } catch { data = raw; } }
    if (!response.ok) {
      if (response.status === 401 && token) window.dispatchEvent(new CustomEvent("auth-expired"));
      if (response.status === 403) throw new ApiError("У вас немає дозволу на цю дію (403).", 403, data);
      if (response.status === 404) throw new ApiError("Запис або сторінку не знайдено (404).", 404, data);
      if (response.status === 409) throw new ApiError(`Конфлікт даних: ${formatError(data, response.status)}`, 409, data);
      throw new ApiError(formatError(data, response.status), response.status, data);
    }
    return data;
  },
};
