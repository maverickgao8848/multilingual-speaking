const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

const DURATION_OPTIONS = [5, 10, 20, 40];
const SUPPORT_OPTIONS = [
  {id: "immersion", label: "沉浸"},
  {id: "guided", label: "引导"},
  {id: "learning", label: "学习"},
];
const INTERACTION_OPTIONS = [
  {id: "text", label: "文字"},
  {id: "voice", label: "实时语音"},
];

let catalog = {languages: [], scenes: []};
let state = {preferences: {language: "es", scene: "cafe-order", duration: 10, support_mode: "guided", interaction_mode: "text"}, sessions: []};
let recommendations = {review_queue: [], next_lesson: null, overview: {}};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2200);
}

function renderChoices() {
  const selected = state.preferences;
  $("#languages").innerHTML = catalog.languages.map(language => `
    <button class="topic-card ${selected.language === language.id ? "selected" : ""}" data-language="${language.id}" aria-pressed="${selected.language === language.id}">
      <span class="emoji">${language.emoji}</span><b>${escapeHtml(language.label)}</b><small>${escapeHtml(language.default_locale)}</small>
    </button>`).join("");
  $("#scenes").innerHTML = catalog.scenes.map(scene => `
    <button class="topic-card ${selected.scene === scene.id ? "selected" : ""}" data-scene="${scene.id}" aria-pressed="${selected.scene === scene.id}">
      <span class="emoji">${scene.emoji}</span><b>${escapeHtml(scene.label)}</b>
    </button>`).join("");
  $("#durations").innerHTML = DURATION_OPTIONS.map(duration => `
    <button class="choice-button ${selected.duration === duration ? "selected" : ""}" data-duration="${duration}" aria-pressed="${selected.duration === duration}">${duration} 分钟</button>`).join("");
  $("#support-modes").innerHTML = SUPPORT_OPTIONS.map(mode => `
    <button class="choice-button ${selected.support_mode === mode.id ? "selected" : ""}" data-support="${mode.id}" aria-pressed="${selected.support_mode === mode.id}">${mode.label}</button>`).join("");
  $("#interaction-modes").innerHTML = INTERACTION_OPTIONS.map(mode => `
    <button class="choice-button ${selected.interaction_mode === mode.id ? "selected" : ""}" data-interaction="${mode.id}" aria-pressed="${selected.interaction_mode === mode.id}">${mode.label}</button>`).join("");

  $$('[data-language]').forEach(button => button.onclick = () => choose("language", button.dataset.language));
  $$('[data-scene]').forEach(button => button.onclick = () => choose("scene", button.dataset.scene));
  $$('[data-duration]').forEach(button => button.onclick = () => choose("duration", Number(button.dataset.duration)));
  $$('[data-support]').forEach(button => button.onclick = () => choose("support_mode", button.dataset.support));
  $$('[data-interaction]').forEach(button => button.onclick = () => choose("interaction_mode", button.dataset.interaction));
}

async function choose(field, value) {
  state.preferences[field] = value;
  renderChoices();
  try {
    const response = await fetch("/api/preferences", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(state.preferences)});
    if (!response.ok) throw new Error("save failed");
    $("#save-status").textContent = "选择已保存";
  } catch {
    $("#save-status").textContent = "预览模式 · 选择未保存";
  }
}

function practicePrompt() {
  const language = catalog.languages.find(item => item.id === state.preferences.language);
  const scene = catalog.scenes.find(item => item.id === state.preferences.scene);
  const supportLabel = SUPPORT_OPTIONS.find(item => item.id === state.preferences.support_mode)?.label;
  const interaction = state.preferences.interaction_mode === "voice" ? "请在当前语音通道进行实时语音互动；只有确实听到音频时才评价发音。" : "本次使用文字互动，不要根据文字推断发音。";
  return `请使用 $multilingual-speaking 开始一次 ${state.preferences.duration} 分钟的${language.label} A1「${scene.label}」口语练习。辅助模式：${supportLabel}（${state.preferences.support_mode}）。${interaction}请从内置已审计课程包生成预习卡，不要给完整对话；等我明确说准备好了再进入角色。练习结束后，请生成符合多语种 workbench 格式的归档 JSON，并调用 skill 内的 workbench.py 保存。`;
}

function recommendedPrompt() {
  const lesson = recommendations.next_lesson;
  if (!lesson) return practicePrompt();
  const language = catalog.languages.find(item => item.id === lesson.language);
  const scene = catalog.scenes.find(item => item.id === lesson.scene);
  const targets = lesson.review_target_ids?.length ? ` 本次优先回练这些 material_id：${lesson.review_target_ids.join("、")}。` : "";
  const interaction = lesson.interaction_mode === "voice" ? "请在当前语音通道实时互动，并仅按实际听到的音频记录发音证据。" : "本次使用文字互动，不评价我的发音。";
  return `请使用 $multilingual-speaking 开始推荐的 ${lesson.duration} 分钟${language.label} A1「${scene.label}」口语练习。辅助模式：${lesson.support_mode}。${interaction}${targets}请从内置已审计课程包生成预习卡，不要给完整对话；等我明确说准备好了再进入角色。练习结束后生成 workbench 归档 JSON 并保存。`;
}

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(practicePrompt());
    toast("练习指令已复制");
  } catch {
    toast("无法访问剪贴板，请在安全上下文中重试");
  }
}

function switchView(view) {
  $$(".view").forEach(item => item.classList.toggle("active", item.id === `${view}-view`));
  $$(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.view === view));
  history.replaceState(null, "", `#${view}`);
  if (view === "review") loadState();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value || "") : new Intl.DateTimeFormat("zh-CN", {month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"}).format(date);
}

function renderReview() {
  const sessions = [...(state.sessions || [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const targets = sessions.flatMap(session => session.targets || []);
  const mastered = targets.filter(target => target.status === "mastered").length;
  const review = targets.filter(target => target.status === "needs_review").length;
  $("#stat-sessions").textContent = sessions.length;
  $("#stat-mastered").textContent = mastered;
  $("#stat-review").textContent = review;
  $("#session-count").textContent = sessions.length ? `已经开口 ${sessions.length} 次` : "从第 1 次开始";
  $("#empty-review").classList.toggle("hidden", sessions.length > 0);

  const lesson = recommendations.next_lesson;
  if (lesson) {
    const language = catalog.languages.find(item => item.id === lesson.language) || {label: lesson.language, emoji: "💬"};
    const scene = catalog.scenes.find(item => item.id === lesson.scene) || {label: lesson.scene, emoji: "·"};
    const typeLabel = {review: "重点回练", new_scene: "拓展新场景", maintenance: "保持熟练度"}[lesson.type] || "下一课";
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
    return `<article class="queue-item paper-card">
      <b class="queue-rank">${index + 1}</b>
      <div><h3>${language.emoji} ${escapeHtml(item.surface)}</h3><p>${escapeHtml(item.meaning_zh)} · ${escapeHtml(scene.label)}</p><small>${escapeHtml(item.reasons.join(" · "))}</small></div>
      <span class="priority-score">P${item.priority}</span>
    </article>`;
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
    const allTargets = items.flatMap(item => item.targets || []);
    const done = allTargets.filter(target => target.status === "mastered").length;
    const percent = allTargets.length ? Math.round(done / allTargets.length * 100) : 0;
    const tags = allTargets.slice(0, 12).map(target => {
      const kind = target.status === "needs_review" ? "review" : target.status === "developing" ? "developing" : "";
      return `<span class="target-tag ${kind}" title="${escapeHtml(target.meaning_zh)}">${escapeHtml(target.surface)}</span>`;
    }).join("");
    return `<article class="review-topic paper-card">
      <div class="review-topic-header"><h2>${language.emoji} ${escapeHtml(language.label)} · ${scene.emoji} ${escapeHtml(scene.label)}</h2><div class="progress" title="掌握 ${percent}%"><i style="width:${percent}%"></i></div></div>
      <p class="review-meta">练过 ${items.length} 次 · 已掌握 ${done}/${allTargets.length} · 最近 ${escapeHtml(formatDate(latest.created_at))}</p>
      <div class="target-tags">${tags || "<span class='target-tag developing'>等待表达记录</span>"}</div>
    </article>`;
  }).join("");
}

async function loadState() {
  try {
    const [catalogResponse, stateResponse, recommendationResponse] = await Promise.all([fetch("/api/catalog"), fetch("/api/state"), fetch("/api/recommendations")]);
    if (!catalogResponse.ok || !stateResponse.ok || !recommendationResponse.ok) throw new Error("load failed");
    catalog = await catalogResponse.json();
    state = await stateResponse.json();
    recommendations = await recommendationResponse.json();
    $("#save-status").textContent = "本地工作台已连接";
  } catch {
    $("#save-status").textContent = "工作台连接失败";
  }
  renderChoices();
  renderReview();
}

function init() {
  $$(".nav-item").forEach(button => button.onclick = () => switchView(button.dataset.view));
  $$('[data-go-practice]').forEach(button => button.onclick = () => switchView("practice"));
  $("#copy-prompt").onclick = copyPrompt;
  $("#use-recommendation").onclick = async () => {
    const lesson = recommendations.next_lesson;
    if (!lesson) return;
    state.preferences.language = lesson.language;
    state.preferences.scene = lesson.scene;
    state.preferences.duration = lesson.duration;
    state.preferences.support_mode = lesson.support_mode;
    state.preferences.interaction_mode = lesson.interaction_mode || "text";
    try {
      await navigator.clipboard.writeText(recommendedPrompt());
      await fetch("/api/preferences", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(state.preferences)});
      renderChoices();
      switchView("practice");
      toast("推荐练习指令已复制");
    } catch { toast("无法复制推荐指令，请重试"); }
  };
  loadState();
  switchView(location.hash === "#review" ? "review" : "practice");
}

init();
