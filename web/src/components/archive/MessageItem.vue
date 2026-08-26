<script setup>
import { computed, ref } from "vue";
import { emojiHtml, mdToHtml, toHex } from "../../emoji";
import { arc, fmtShortTime, fmtSize, fmtTime, jumpTo, mediaUrl } from "../../archive";

const props = defineProps({
  msg: { type: Object, required: true },
  compact: { type: Boolean, default: false },
});
defineEmits(["show-history"]);

const avatarFailed = ref(false);

// stable per-user fallback color when the CDN avatar has gone stale
const avatarColor = computed(() => {
  try {
    return `hsl(${Number(BigInt(props.msg.author_id || "0") % 360n)}, 55%, 45%)`;
  } catch {
    return "hsl(210, 55%, 45%)";
  }
});

const isSystem = computed(
  () => props.msg.type !== "default" && props.msg.type !== "reply",
);
const contentHtml = computed(() => mdToHtml(props.msg.content || ""));
const highlighted = computed(() => arc.jumpTarget === props.msg.id);

const plainAtts = computed(() =>
  (props.msg.attachments || []).filter((a) => a.kind === "attachment"),
);

// embed images were archived as attachment rows; pair them back by kind+order
function embedMedia(index, kind) {
  const list = (props.msg.attachments || []).filter((a) => a.kind === kind);
  return list[index] || null;
}

function isImage(att) {
  return (att.content_type || "").startsWith("image/");
}
function isVideo(att) {
  return (att.content_type || "").startsWith("video/");
}
function isAudio(att) {
  return (att.content_type || "").startsWith("audio/");
}

// reserve the box from stored dimensions so late-loading images don't shift scroll
function imgStyle(att) {
  if (!att.width || !att.height) return { maxWidth: "400px", maxHeight: "300px" };
  const w = Math.min(att.width, 400);
  return { aspectRatio: `${att.width} / ${att.height}`, width: w + "px" };
}

function embedColor(embed) {
  return embed.color != null ? toHex(embed.color) : "var(--el-border-color)";
}

function jumpToReply() {
  const ref_ = props.msg.reply_to;
  if (ref_ && !ref_.missing) jumpTo(props.msg.channel_id, ref_.id);
}
</script>

<template>
  <div
    class="msg"
    :class="{ compact, deleted: msg.deleted_at, highlighted, system: isSystem }"
    :data-mid="msg.id"
  >
    <div v-if="msg.reply_to" class="reply-line" @click="jumpToReply">
      <span class="reply-spine" />
      <template v-if="msg.reply_to.missing">
        <span class="reply-missing">原消息已无法加载</span>
      </template>
      <template v-else>
        <span class="reply-author">{{ msg.reply_to.author_name }}</span>
        <span class="reply-content" :class="{ strike: msg.reply_to.deleted }">
          {{ msg.reply_to.content || "（无文本内容）" }}
        </span>
      </template>
    </div>

    <div class="row">
      <div class="gutter">
        <template v-if="!compact">
          <img
            v-if="msg.avatar_url && !avatarFailed"
            class="avatar"
            :src="msg.avatar_url"
            alt=""
            loading="lazy"
            @error="avatarFailed = true"
          />
          <div v-else class="avatar avatar-fallback" :style="{ background: avatarColor }">
            {{ (msg.author_name || "?")[0] }}
          </div>
        </template>
        <span v-else class="gutter-time">{{ fmtShortTime(msg.created_at) }}</span>
      </div>

      <div class="body">
        <div v-if="!compact" class="header">
          <span class="author">{{ msg.author_name }}</span>
          <span v-if="msg.is_bot" class="bot-tag">BOT</span>
          <span class="time">{{ fmtTime(msg.created_at) }}</span>
          <span v-if="msg.pinned" class="pin" title="已置顶">📌</span>
          <span v-if="msg.deleted_at" class="del-tag" :title="'删除于 ' + fmtTime(msg.deleted_at)">
            已删除
          </span>
        </div>
        <span v-else-if="msg.deleted_at" class="del-tag inline">已删除</span>

        <div v-if="msg.content" class="content" :class="{ 'system-text': isSystem }">
          <span v-html="contentHtml" />
          <a
            v-if="msg.edited_at"
            class="edited"
            :title="'编辑于 ' + fmtTime(msg.edited_at)"
            @click="$emit('show-history', msg)"
          >(已编辑)</a>
        </div>

        <!-- direct attachments -->
        <div v-for="att in plainAtts" :key="att.id" class="attachment">
          <template v-if="!att.downloaded || !att.url">
            <div class="att-file undownloaded">
              <span class="file-ico">📎</span>
              <div>
                <div>{{ att.filename || "附件" }}</div>
                <div class="hint">附件未下载归档</div>
              </div>
            </div>
          </template>
          <a
            v-else-if="isImage(att)"
            class="att-media"
            :href="mediaUrl(att)"
            target="_blank"
            rel="noopener"
          >
            <img
              :src="mediaUrl(att)"
              :alt="att.filename || ''"
              loading="lazy"
              :style="imgStyle(att)"
            />
          </a>
          <video
            v-else-if="isVideo(att)"
            class="att-video"
            controls
            preload="metadata"
            :src="mediaUrl(att)"
          />
          <audio v-else-if="isAudio(att)" controls preload="none" :src="mediaUrl(att)" />
          <div v-else class="att-file">
            <span class="file-ico">📄</span>
            <div>
              <a :href="mediaUrl(att)" target="_blank" rel="noopener">
                {{ att.filename || att.id }}
              </a>
              <div class="hint">{{ fmtSize(att.size) }}</div>
            </div>
          </div>
        </div>

        <!-- embeds -->
        <div
          v-for="(embed, i) in msg.embeds"
          :key="'e' + i"
          class="embed"
          :style="{ borderLeftColor: embedColor(embed) }"
        >
          <div v-if="embed.author?.name" class="embed-author">{{ embed.author.name }}</div>
          <div v-if="embed.title" class="embed-title">
            <a v-if="embed.url" :href="embed.url" target="_blank" rel="noopener">
              {{ embed.title }}
            </a>
            <template v-else>{{ embed.title }}</template>
          </div>
          <div
            v-if="embed.description"
            class="embed-desc"
            v-html="mdToHtml(embed.description)"
          />
          <img
            v-if="embedMedia(i, 'embed_image')?.url"
            class="embed-img"
            :src="mediaUrl(embedMedia(i, 'embed_image'))"
            loading="lazy"
            alt=""
          />
          <img
            v-else-if="embed.image?.url"
            class="embed-img"
            :src="embed.image.url"
            loading="lazy"
            alt=""
            @error="(e) => (e.target.style.display = 'none')"
          />
          <div v-if="embed.footer?.text" class="embed-footer">{{ embed.footer.text }}</div>
        </div>

        <!-- stickers -->
        <div v-for="s in msg.stickers" :key="s.id" class="sticker">
          <img
            :src="s.url"
            :alt="s.name"
            :title="s.name"
            loading="lazy"
            @error="(e) => (e.target.outerHTML = '<span class=hint>[贴纸] ' + s.name + '</span>')"
          />
        </div>

        <!-- reactions -->
        <div v-if="msg.reactions?.length" class="reactions">
          <span v-for="r in msg.reactions" :key="r.emoji" class="reaction">
            <span class="r-emoji" v-html="emojiHtml(r.emoji)" />
            <span class="r-count">{{ r.count }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg {
  padding: 2px 16px 2px 12px;
  margin-top: 14px;
  border-left: 3px solid transparent;
}
.msg.compact { margin-top: 0; }
.msg:hover { background: rgba(0, 0, 0, 0.08); }
.msg.deleted { border-left-color: var(--el-color-danger); }
.msg.highlighted { animation: flash 2s ease-out; }
@keyframes flash {
  0%, 40% { background: rgba(88, 101, 242, 0.25); }
  100% { background: transparent; }
}

.reply-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 46px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;
}
.reply-line:hover .reply-content { color: var(--el-text-color-primary); }
.reply-spine {
  width: 24px;
  height: 9px;
  flex-shrink: 0;
  border-left: 2px solid var(--el-border-color);
  border-top: 2px solid var(--el-border-color);
  border-top-left-radius: 6px;
  margin-top: 9px;
}
.reply-author { font-weight: 600; flex-shrink: 0; }
.reply-content { overflow: hidden; text-overflow: ellipsis; }
.reply-content.strike { text-decoration: line-through; }
.reply-missing { font-style: italic; }

.row { display: flex; gap: 12px; }
.gutter { width: 40px; flex-shrink: 0; display: flex; justify-content: center; }
.avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
}
.gutter-time {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  visibility: hidden;
  align-self: center;
}
.msg:hover .gutter-time { visibility: visible; }

.body { flex: 1; min-width: 0; }
.header { display: flex; align-items: baseline; gap: 8px; }
.author { font-weight: 600; }
.bot-tag {
  background: var(--el-color-primary);
  color: #fff;
  font-size: 10px;
  border-radius: 4px;
  padding: 1px 5px;
  align-self: center;
}
.time { font-size: 12px; color: var(--el-text-color-placeholder); }
.del-tag {
  font-size: 11px;
  color: var(--el-color-danger);
  border: 1px solid var(--el-color-danger);
  border-radius: 4px;
  padding: 0 5px;
}
.del-tag.inline { float: right; }

.content {
  font-size: 15px;
  line-height: 1.45;
  color: var(--el-text-color-regular);
  word-break: break-word;
}
.system-text { font-style: italic; color: var(--el-text-color-secondary); }
.content :deep(a) { color: var(--el-color-primary-light-3); }
.content :deep(code),
.embed-desc :deep(code) {
  background: var(--ctn-input);
  border-radius: 4px;
  padding: 1px 4px;
  font-size: 13px;
}
.edited {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  margin-left: 4px;
}
.edited:hover { text-decoration: underline; }

.attachment { margin-top: 6px; }
.att-media img {
  display: block;
  max-width: min(400px, 100%);
  max-height: 500px;
  border-radius: 6px;
  background: var(--ctn-input);
  object-fit: cover;
}
.att-video { max-width: min(400px, 100%); border-radius: 6px; }
.att-file {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ctn-card);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 10px 14px;
  max-width: 400px;
}
.att-file a { color: var(--el-color-primary-light-3); text-decoration: none; }
.att-file.undownloaded { opacity: 0.65; }
.file-ico { font-size: 22px; }

.embed {
  margin-top: 6px;
  background: var(--ctn-card);
  border-left: 4px solid;
  border-radius: 4px;
  padding: 10px 14px;
  max-width: 480px;
  font-size: 14px;
}
.embed-author { font-size: 12px; font-weight: 600; margin-bottom: 4px; }
.embed-title { font-weight: 600; margin-bottom: 4px; }
.embed-title a { color: var(--el-color-primary-light-3); text-decoration: none; }
.embed-desc { color: var(--el-text-color-regular); word-break: break-word; }
.embed-img { max-width: 100%; max-height: 300px; border-radius: 4px; margin-top: 8px; }
.embed-footer {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  margin-top: 6px;
}

.sticker img { width: 160px; height: 160px; object-fit: contain; }

.reactions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.reaction {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--ctn-card);
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  padding: 2px 8px;
  font-size: 13px;
}
.reaction :deep(img.em) { width: 16px; height: 16px; vertical-align: -3px; }
.reaction :deep(.em-txt) { font-size: 15px; }
.r-count { color: var(--el-text-color-secondary); }
</style>
