// Thin fetch wrapper with bearer-token auth.
// A 401 raises an error flagged `auth: true`; the UI renders an in-page token
// gate instead of prompting per call (parallel calls would prompt repeatedly).

function token() {
  return localStorage.getItem("cortana_token") || "";
}

export const hasToken = () => !!token();

export function setToken(v) {
  localStorage.setItem("cortana_token", v);
}

export function clearToken() {
  localStorage.removeItem("cortana_token");
}

export async function api(path, opts = {}) {
  opts.headers = Object.assign(
    {},
    opts.headers,
    token() ? { Authorization: "Bearer " + token() } : {},
  );
  const r = await fetch(path, opts);
  if (r.status === 401) {
    const err = new Error("未授权");
    err.auth = true;
    throw err;
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

export const getConfig = () => api("/api/config");
export const getGuild = () => api("/api/guild");
export const putConfig = (config) =>
  api("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
