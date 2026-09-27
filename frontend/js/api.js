const BASE = window.CRAVE_API_BASE || "";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function describeDetail(detail) {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((err) => (err && err.msg ? String(err.msg).replace(/^Value error,\s*/i, "") : String(err)))
      .join(" ");
  }
  return String(detail);
}

async function request(path, { method = "GET", body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(0, "Can't reach the Crave API. Is the server running?");
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = describeDetail(payload && payload.detail) || `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return payload;
}

export const api = {
  health: () => request("/health"),
  meta: () => request("/meta"),
  locations: () => request("/meta/locations").then((d) => d.locations || []),
  cuisines: () => request("/meta/cuisines").then((d) => d.cuisines || []),
  recommend: (body, signal) => request("/recommend", { method: "POST", body, signal }),
};
