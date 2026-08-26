// State + API calls for the archive browsing view. Read-only and paged, so it
// lives apart from the editable-config store in store.js.
//
// Message/channel/user IDs exceed Number.MAX_SAFE_INTEGER: they are strings
// end-to-end here; ordering decisions (before/after cursors) happen server-side.
import { reactive } from "vue";
import { api, token } from "./api";
import { store } from "./store";

export const arc = reactive({
  channels: [],
  channelsLoaded: false,
  currentChannelId: "",
  messages: [], // ascending by id
  hasMoreBefore: false,
  hasMoreAfter: false,
  loading: false, // full message-pane load (open / jump)
  loadingMore: false, // guards prepend/append fetches
  error: "",
  jumpTarget: "", // message id to center + flash after an around-load
  users: [],
  usersLoaded: false,
  search: {
    open: false,
    q: "",
    channelId: "",
    authorId: "",
    results: [],
    hasMore: false,
    searched: false,
    loading: false,
    error: "",
  },
});

function handleAuth(e) {
  if (e.auth) {
    store.needToken = true;
    return true;
  }
  return false;
}

export async function loadChannels() {
  try {
    const data = await api("/api/archive/channels");
    arc.channels = data.channels;
    arc.channelsLoaded = true;
    arc.error = "";
  } catch (e) {
    if (!handleAuth(e)) arc.error = e.message;
  }
}

export async function loadUsers() {
  if (arc.usersLoaded) return;
  try {
    const data = await api("/api/archive/users");
    arc.users = data.users;
    arc.usersLoaded = true;
  } catch (e) {
    handleAuth(e);
  }
}

async function loadPane(channelId, query, jumpTarget = "") {
  arc.currentChannelId = channelId;
  arc.loading = true;
  arc.error = "";
  arc.messages = [];
  arc.jumpTarget = jumpTarget;
  try {
    const data = await api(`/api/archive/messages?channel_id=${channelId}${query}`);
    if (arc.currentChannelId !== channelId) return; // switched away meanwhile
    arc.messages = data.messages;
    arc.hasMoreBefore = data.has_more_before;
    arc.hasMoreAfter = data.has_more_after;
  } catch (e) {
    if (!handleAuth(e)) arc.error = e.message;
  } finally {
    if (arc.currentChannelId === channelId) arc.loading = false;
  }
}

// data-only: ArchiveView watches arc.currentChannelId and syncs the URL,
// so this module stays free of a circular import on the router
export function openChannel(id) {
  return loadPane(id, "&limit=50");
}

export function jumpTo(channelId, messageId) {
  return loadPane(channelId, `&around=${messageId}&limit=50`, messageId);
}

// returns the number of prepended messages so the caller can restore scroll
export async function loadOlder() {
  if (!arc.hasMoreBefore || arc.loadingMore || !arc.messages.length) return 0;
  const channelId = arc.currentChannelId;
  arc.loadingMore = true;
  try {
    const data = await api(
      `/api/archive/messages?channel_id=${channelId}&before=${arc.messages[0].id}&limit=50`,
    );
    if (arc.currentChannelId !== channelId) return 0;
    arc.messages = [...data.messages, ...arc.messages];
    arc.hasMoreBefore = data.has_more_before;
    return data.messages.length;
  } catch (e) {
    handleAuth(e);
    return 0;
  } finally {
    arc.loadingMore = false;
  }
}

export async function loadNewer() {
  if (!arc.hasMoreAfter || arc.loadingMore || !arc.messages.length) return;
  const channelId = arc.currentChannelId;
  arc.loadingMore = true;
  try {
    const data = await api(
      `/api/archive/messages?channel_id=${channelId}&after=${arc.messages[arc.messages.length - 1].id}&limit=50`,
    );
    if (arc.currentChannelId !== channelId) return;
    arc.messages = [...arc.messages, ...data.messages];
    arc.hasMoreAfter = data.has_more_after;
  } catch (e) {
    handleAuth(e);
  } finally {
    arc.loadingMore = false;
  }
}

export async function runSearch(more = false) {
  const s = arc.search;
  const q = s.q.trim();
  if (q.length < 2) {
    s.error = "搜索词至少2个字符";
    return;
  }
  s.loading = true;
  s.error = "";
  try {
    let url = `/api/archive/search?q=${encodeURIComponent(q)}&limit=25`;
    if (s.channelId) url += `&channel_id=${s.channelId}`;
    if (s.authorId) url += `&author_id=${s.authorId}`;
    if (more && s.results.length) url += `&before=${s.results[s.results.length - 1].id}`;
    const data = await api(url);
    s.results = more ? [...s.results, ...data.results] : data.results;
    s.hasMore = data.has_more;
    s.searched = true;
  } catch (e) {
    if (!handleAuth(e)) s.error = e.message;
  } finally {
    s.loading = false;
  }
}

// media is fetched by <img>/<video>, which cannot send the auth header;
// the backend accepts the token as a query param instead
export function mediaUrl(att) {
  if (!att.url) return null;
  const t = token();
  return t ? `${att.url}?token=${encodeURIComponent(t)}` : att.url;
}

export function fmtTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtShortTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDay(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}

export function fmtSize(bytes) {
  if (bytes == null) return "";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}
