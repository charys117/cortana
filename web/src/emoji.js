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

// tiny renderer for the Discord-message preview: custom emoji, :shortcode:, **bold**
export function mdToHtml(text) {
  let html = esc(text);
  html = html.replace(/&lt;(a?):(\w+):(\d+)&gt;/g, (_, a, n, id) =>
    `<img class="em" src="https://cdn.discordapp.com/emojis/${id}.${a === "a" ? "gif" : "png"}" title="${n}">`);
  html = html.replace(/:([\w+-]+):/g, (m0, n) =>
    SHORTCODES[n] ? `<span class="em-txt">${SHORTCODES[n]}</span>` : m0);
  html = html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  return html.replace(/\n/g, "<br>");
}

export function toHex(n) {
  return "#" + (Number(n) >>> 0).toString(16).padStart(6, "0");
}
