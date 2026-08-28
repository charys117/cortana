// Emoji parsing/rendering shared by the picker, buttons and previews.

export const SHORTCODES = {
  heart: "❤️", heartbeat: "💓", sparkling_heart: "💖", two_hearts: "💕", heartpulse: "💗",
  yellow_heart: "💛", green_heart: "💚", blue_heart: "💙", purple_heart: "💜",
  star: "⭐", star2: "🌟", sparkles: "✨", fire: "🔥", crystal_ball: "🔮",
  moneybag: "💰", dollar: "💵", coin: "🪙", gem: "💎", trophy: "🏆", medal: "🏅", crown: "👑",
  gift: "🎁", tada: "🎉", confetti_ball: "🎊", balloon: "🎈", partying_face: "🥳",
  bubble_tea: "🧋", coffee: "☕", tea: "🍵", cake: "🍰", cookie: "🍪", candy: "🍬",
  lollipop: "🍭", doughnut: "🍩", ice_cream: "🍨", ramen: "🍜", rice: "🍚", sushi: "🍣",
  bento: "🍱", pizza: "🍕", hamburger: "🍔", fries: "🍟", apple: "🍎", strawberry: "🍓",
  peach: "🍑", watermelon: "🍉", grapes: "🍇", cherries: "🍒", beer: "🍺", sake: "🍶",
  dog: "🐶", cat: "🐱", rabbit: "🐰", bear: "🐻", panda_face: "🐼", fox_face: "🦊",
  penguin: "🐧", chick: "🐤", parrot: "🦜", unicorn: "🦄", dragon: "🐉", whale: "🐳",
  sun_with_face: "🌞", full_moon_with_face: "🌝", rainbow: "🌈", cloud: "☁️",
  zap: "⚡", snowflake: "❄️", cherry_blossom: "🌸", rose: "🌹", sunflower: "🌻",
  four_leaf_clover: "🍀", maple_leaf: "🍁", dizzy: "💫", boom: "💥", bulb: "💡",
  100: "💯", ok_hand: "👌", thumbsup: "👍", clap: "👏", pray: "🙏", muscle: "💪",
  wave: "👋", point_up: "☝️", v: "✌️", eyes: "👀", smile: "😄", laughing: "😆",
  joy: "😂", rofl: "🤣", blush: "😊", heart_eyes: "😍", smirk: "😏", thinking: "🤔",
  sob: "😭", angry: "😠", ghost: "👻", alien: "👽", robot: "🤖", cat2: "🐈",
  game_die: "🎲", dart: "🎯", video_game: "🎮", jigsaw: "🧩", art: "🎨",
  musical_note: "🎵", notes: "🎶", microphone: "🎤", headphones: "🎧",
  rocket: "🚀", airplane: "✈️", umbrella: "☂️", hourglass: "⌛", alarm_clock: "⏰",
  bell: "🔔", key: "🔑", lock: "🔒", envelope: "✉️", memo: "📝", books: "📚",
  pill: "💊", syringe: "💉", warning: "⚠️", white_check_mark: "✅", x: "❌",
  question: "❓", exclamation: "❗", heavy_plus_sign: "➕", infinity: "♾️",
};

export const CUSTOM_RE = /<(a?):(\w+):(\d+)>/;

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// config value (unicode char / :shortcode: / <:name:id>) -> preview HTML
export function emojiHtml(value) {
  if (!value) return '<span class="hint">未设置</span>';
  const m = String(value).match(CUSTOM_RE);
  if (m) {
    const ext = m[1] === "a" ? "gif" : "png";
    return `<img class="em" src="https://cdn.discordapp.com/emojis/${m[3]}.${ext}" title="${esc(m[2])}">`;
  }
  const sc = String(value).match(/^:([\w+-]+):$/);
  if (sc) {
    const uni = SHORTCODES[sc[1]];
    return uni
      ? `<span class="em-txt" title="${esc(value)}">${uni}</span>`
      : `<span class="hint">${esc(value)}</span>`;
  }
  return `<span class="em-txt">${esc(String(value))}</span>`;
}

// mirror of src/core/tools.format_units
export function formatUnits(units, total, rowSize = 5) {
  if (total <= 0) return "";
  const nums = [];
  for (let i = units.length - 1; i >= 0; i--) {
    nums.push([Math.floor(total / 10 ** i), units[i]]);
    total %= 10 ** i;
  }
  let result = "";
  for (const [num, unit] of nums) {
    for (let r = 0; r < Math.floor(num / rowSize); r++) result += unit.repeat(rowSize) + "\n";
    if (num % rowSize) result += unit.repeat(num % rowSize) + "\n";
  }
  return result;
}

// tiny Discord-flavored renderer for message previews and archived messages:
// code, links, custom emoji, :shortcode:, mentions, **bold** *italic*
// __underline__ ~~strike~~ ||spoiler|| and > quote lines.
// `resolve` (optional) maps mention ids to names: { user(id), channel(id) }
export function mdToHtml(text, resolve = {}) {
  // lift code out first so no other rule fires inside it
  const codes = [];
  const stash = (h) => `\x00${codes.push(h) - 1}\x00`;
  let src = String(text ?? "");
  src = src.replace(/```(?:\w+\n)?([\s\S]*?)```/g, (_, body) =>
    stash(`<pre class="md-pre"><code>${esc(body.replace(/^\n+|\n+$/g, ""))}</code></pre>`),
  );
  src = src.replace(/`([^`\n]+)`/g, (_, body) => stash(`<code>${esc(body)}</code>`));
  // autolink on the raw text (odd split indices are URLs), escaping each part
  let html = src
    .split(/(https?:\/\/[^\s<>]+)/g)
    .map((seg, i) => {
      if (i % 2 === 0) return esc(seg);
      const url = seg.replace(/[),.;!?]+$/, "");
      const trail = seg.slice(url.length);
      return `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(url)}</a>${esc(trail)}`;
    })
    .join("");
  html = html.replace(/&lt;(a?):(\w+):(\d+)&gt;/g, (_, a, n, id) =>
    `<img class="em" src="https://cdn.discordapp.com/emojis/${id}.${a === "a" ? "gif" : "png"}" title="${n}">`);
  html = html.replace(/:([\w+-]+):/g, (m0, n) =>
    SHORTCODES[n] ? `<span class="em-txt">${SHORTCODES[n]}</span>` : m0);
  html = html.replace(/&lt;@!?(\d+)&gt;/g, (_, id) =>
    `<span class="mention">@${esc(resolve.user?.(id) || id)}</span>`);
  html = html.replace(/&lt;#(\d+)&gt;/g, (_, id) =>
    `<span class="mention">#${esc(resolve.channel?.(id) || id)}</span>`);
  html = html.replace(/&lt;@&amp;\d+&gt;/g, '<span class="mention">@身份组</span>');
  html = html
    .replace(/\*\*\*([^*\n]+)\*\*\*/g, "<b><i>$1</i></b>")
    .replace(/\*\*([^\n]+?)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<i>$2</i>")
    .replace(/__([^_\n]+)__/g, "<u>$1</u>")
    .replace(/(^|\s)_([^_\n]+)_(?=\s|$)/gm, "$1<i>$2</i>")
    .replace(/~~([^~\n]+)~~/g, "<s>$1</s>")
    .replace(/\|\|([\s\S]+?)\|\|/g, '<span class="spoiler">$1</span>');
  html = html.replace(/^&gt; ?(.*)$\n?/gm, '<span class="md-quote">$1</span>');
  html = html.replace(/\n/g, "<br>");
  return html.replace(/\x00(\d+)\x00/g, (_, i) => codes[i]);
}

export function toHex(n) {
  return "#" + (Number(n) >>> 0).toString(16).padStart(6, "0");
}
