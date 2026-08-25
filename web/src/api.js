// Thin fetch wrapper with bearer-token auth.
// On 401 it asks the UI for a token (App.vue registers the prompt) and retries.

let tokenPrompt = null; // async () => string | null

export function setTokenPrompt(fn) {
  tokenPrompt = fn;
}

function token() {
  return localStorage.getItem("cortana_token") || "";
}

export async function api(path, opts = {}) {
  opts.headers = Object.assign(
    {},
    opts.headers,
    token() ? { Authorization: "Bearer " + token() } : {},
  );
  const r = await fetch(path, opts);
  if (r.status === 401 && tokenPrompt) {
    const t = await tokenPrompt();
    if (t) {
      localStorage.setItem("cortana_token", t);
      return api(path, opts);
    }
    throw new Error("未授权");
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
