const $ = selector => document.querySelector(selector);
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

let catalog = {languages: [], scenes: []};
let state = {sessions: []};
let recommendations = {review_queue: [], next_lesson: null, overview: {}};
let loading = false;

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value || "") : new Intl.DateTimeFormat("zh-CN", {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"}).format(date);
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2200);
}

function latestTargets(items) {
  const latest = new Map();
  for (const session of items) {
    for (const target of session.targets || []) {
      if (target.material_id && !latest.has(target.material_id)) latest.set(target.material_id, target);
    }
  }
  return [...latest.values()];
}

function recentRepairs(items, limit = 3) {
  const seen = new Set();
  const repairs = [];
  for (const session of items) {
    for (const repair of session.repairs || []) {
      const key = `${repair.learner || ""}\u0000${repair.natural || ""}`;
      if (!seen.has(key) && (repair.learner || repair.natural)) {
        seen.add(key);
        repairs.push(repair);
        if (repairs.length === limit) return repairs;
      }
    }
  }
  return repairs;
}

function firstNonEmpty(items, field) {
  for (const item of items) {
    const value = item[field];
    if (Array.isArray(value) && value.length) return value.filter(Boolean).slice(0, 3);
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return Array.isArray(items[0]?.[field]) ? [] : "";
}

function latestPronunciation(items) {
  for (const item of items) {
    if (item.pronunciation?.status === "observed" && item.pronunciation.notes?.length) return item.pronunciation;
  }
  return null;
}

function targetTag(target) {
  const classes = target.status === "needs_review" ? "review" : target.status === "developing" ? "developing" : "";
  const labels = {mastered: "已掌握", developing: "形成中", needs_review: "待复习", not_observed: "未观察"};
  return `<span class="target-tag ${classes}" title="${escapeHtml(target.meaning_zh || "")}">${escapeHtml(target.surface || target.material_id)}<small>${escapeHtml(labels[target.status] || "")}</small></span>`;
}

function repairHtml(repairs) {
  if (!repairs.length) return "";
  return `<section class="review-detail"><h3>重点纠正</h3><div class="repair-list">${repairs.map(repair => `
    <div class="repair-item">
      <p><span>原表达</span>${escapeHtml(repair.learner || "本次表达摘要")}</p>
      <p class="natural"><span>更自然</span>${escapeHtml(repair.natural || "")}</p>
      ${repair.reason_zh ? `<small>${escapeHtml(repair.reason_zh)}</small>` : ""}
    </div>`).join("")}</div></section>`;
}

function recommendedPrompt() {
  const lesson = recommendations.next_lesson;
  if (!lesson) return "请使用 $multilingual-speaking 根据我最近的复习记录安排一次复练。";
  const language = catalog.languages.find(item => item.id === lesson.language) || {label: lesson.language};
  const scene = catalog.scenes.find(item => item.id === lesson.scene) || {label: lesson.scene};
  const targets = lesson.review_target_ids?.length ? ` 本次优先回练这些 material_id：${lesson.review_target_ids.join("、")}。` : "";
  const interaction = lesson.interaction_mode === "voice" ? "请在当前语音通道实时互动，并仅按实际听到的音频记录发音证据。" : "本次使用文字互动，不评价我的发音。";
  return `请使用 $multilingual-speaking 开始推荐的 ${lesson.duration} 分钟${language.label} A1「${scene.label}」复练。辅助模式：${lesson.support_mode}。${interaction}${targets}请从内置课程包生成预习卡，等我明确准备好再进入角色；结束后自动整理纠正、掌握度和下一步，并保存到 workbench。`;
}

function renderReview() {
  const sessions = [...(state.sessions || [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const currentTargets = latestTargets(sessions);
  const mastered = currentTargets.filter(target => target.status === "mastered").length;
  const dueCount = currentTargets.filter(target => ["developing", "needs_review"].includes(target.status)).length;
  $("#stat-sessions").textContent = sessions.length;
  $("#stat-mastered").textContent = mastered;
  $("#stat-review").textContent = dueCount;
  $("#session-count").textContent = sessions.length ? `已经开口 ${sessions.length} 次` : "从第 1 次开始";
  $("#empty-review").classList.toggle("hidden", sessions.length > 0);
  $("#recommendation-card").classList.toggle("hidden", sessions.length === 0 || !recommendations.next_lesson);

  const lesson = recommendations.next_lesson;
  if (sessions.length && lesson) {
    const language = catalog.languages.find(item => item.id === lesson.language) || {label: lesson.language, emoji: "💬"};
    const scene = catalog.scenes.find(item => item.id === lesson.scene) || {label: lesson.scene, emoji: "·"};
    const typeLabel = {review: "重点回练", new_scene: "拓展新场景", maintenance: "保持熟练度"}[lesson.type] || "下一次复练";
    $("#recommendation-title").textContent = `${language.emoji} ${language.label} · ${scene.emoji} ${scene.label}`;
    $("#recommendation-reason").textContent = `${typeLabel}｜${lesson.reason}`;
    const due = (recommendations.review_queue || []).filter(item => lesson.review_target_ids?.includes(item.material_id));
    $("#recommendation-targets").innerHTML = due.map(item => `<span>${escapeHtml(item.surface)}<small>${escapeHtml(item.meaning_zh)}</small></span>`).join("");
  }

  const queue = recommendations.review_queue || [];
  $("#queue-section").classList.toggle("hidden", queue.length === 0);
  $("#review-queue").innerHTML = queue.map((item, index) => {
    const language = catalog.languages.find(value => value.id === item.language) || {emoji: "💬"};
    const scene = catalog.scenes.find(value => value.id === item.scene) || {label: item.scene};
    return `<article class="queue-item paper-card"><b class="queue-rank">${index + 1}</b><div><h3>${language.emoji} ${escapeHtml(item.surface)}</h3><p>${escapeHtml(item.meaning_zh)} · ${escapeHtml(scene.label)}</p><small>${escapeHtml(item.reasons.join(" · "))}</small></div><span class="priority-score">P${item.priority}</span></article>`;
  }).join("");

  const groups = sessions.reduce((result, session) => {
    const key = `${session.language}:${session.scene}`;
    (result[key] ||= []).push(session);
    return result;
  }, {});
  $("#review-list").innerHTML = Object.values(groups).map(items => {
    const latest = items[0];
    const language = catalog.languages.find(item => item.id === latest.language) || {label: latest.language, emoji: "💬"};
    const scene = catalog.scenes.find(item => item.id === latest.scene) || {label: latest.scene, emoji: "·"};
    const targets = latestTargets(items);
    const done = targets.filter(target => target.status === "mastered").length;
    const percent = targets.length ? Math.round(done / targets.length * 100) : 0;
    const repairs = recentRepairs(items);
    const focus = firstNonEmpty(items, "focus_next");
    const drill = firstNonEmpty(items, "next_drill");
    const pronunciation = latestPronunciation(items);
    return `<article class="review-topic paper-card">
      <div class="review-topic-header"><h2>${language.emoji} ${escapeHtml(language.label)} · ${scene.emoji} ${escapeHtml(scene.label)}</h2><div class="progress" title="掌握 ${percent}%"><i style="width:${percent}%"></i></div></div>
      <p class="review-meta">练过 ${items.length} 次 · ${latest.mission_completed === false ? "任务未完成" : "已归档"} · 已掌握 ${done}/${targets.length} · 最近 ${escapeHtml(formatDate(latest.created_at))}</p>
      <section class="review-detail"><h3>表达状态</h3><div class="target-tags">${targets.map(targetTag).join("") || "<span class='target-tag developing'>等待表达记录</span>"}</div></section>
      ${repairHtml(repairs)}
      ${focus.length ? `<section class="review-detail"><h3>下次重点</h3><div class="focus-list">${focus.map(item => `<span>${escapeHtml(item)}</span>`).join("")}</div></section>` : ""}
      ${drill ? `<section class="next-drill"><b>迁移练习</b><p>${escapeHtml(drill)}</p></section>` : ""}
      ${pronunciation?.status === "observed" && pronunciation.notes?.length ? `<section class="review-detail"><h3>发音记录</h3><p>${pronunciation.notes.map(escapeHtml).join("；")}</p></section>` : ""}
    </article>`;
  }).join("");
}

async function loadState() {
  if (loading) return;
  loading = true;
  try {
    const [catalogResponse, stateResponse, recommendationResponse] = await Promise.all([
      fetch("/api/catalog", {cache: "no-store"}), fetch("/api/state", {cache: "no-store"}), fetch("/api/recommendations", {cache: "no-store"})
    ]);
    if (!catalogResponse.ok || !stateResponse.ok || !recommendationResponse.ok) throw new Error("load failed");
    catalog = await catalogResponse.json();
    state = await stateResponse.json();
    recommendations = await recommendationResponse.json();
    renderReview();
    $("#save-status").textContent = `本地存档已同步 · ${new Date().toLocaleTimeString("zh-CN", {hour:"2-digit", minute:"2-digit"})}`;
  } catch {
    $("#save-status").textContent = "暂时无法读取本地存档";
  } finally {
    loading = false;
  }
}

$("#refresh-data").addEventListener("click", loadState);
$("#copy-review-prompt").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(recommendedPrompt());
    toast("复练指令已复制");
  } catch {
    toast("无法复制复练指令，请重试");
  }
});
document.addEventListener("visibilitychange", () => { if (!document.hidden) loadState(); });
loadState();
setInterval(loadState, 8000);
