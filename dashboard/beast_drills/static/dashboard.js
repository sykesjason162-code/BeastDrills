let RESPONSE_CATEGORIES = [
  "anti_air", "throw", "throw_tech", "counter_hit", "punish_counter_hit", "block",
  "perfect_parry", "drive_impact", "drive_impact_counter", "drive_impact_vs_di",
  "stuff_dash", "stuff_drive_rush",
  "block_then_punish", "hit_confirm", "reversal", "do_nothing", "pressure",
];

const STATS_CHARACTER_KEY = "bd.stats.character";
let statsCharacter = localStorage.getItem(STATS_CHARACTER_KEY) || "all";

const STATS_DUMMY_KEY = "bd.stats.dummy";
let statsDummy = localStorage.getItem(STATS_DUMMY_KEY) || "all";

const t = (s) => (window.i18n ? window.i18n.T(s) : s);

const statsUrl = (path) => {
  const q = new URLSearchParams();
  if (statsCharacter && statsCharacter !== "all") q.set("character", statsCharacter);
  if (statsDummy && statsDummy !== "all") q.set("dummy", statsDummy);
  const s = q.toString();
  return s ? `${path}?${s}` : path;
};

async function loadResponseCategories() {
  try {
    const r = await fetch("/api/response_categories");
    if (!r.ok) return;
    const j = await r.json();
    if (Array.isArray(j.categories) && j.categories.length)
      RESPONSE_CATEGORIES = j.categories;

    if (Array.isArray(j.trains) && j.trains.length)
      TRAINS_CATEGORIES = j.trains;
    if (Array.isArray(j.trains_for) && j.trains_for.length)
      TRAINS_FOR_CATEGORIES = j.trains_for;
  } catch (e) {

  }
}

const OFFENSE_TALLY_KEYS = [
  "anti_air", "throw", "throw_missed_me", "throw_tech", "counter_hit",
  "punish_counter_hit", "block", "parry", "perfect_parry", "drive_impact",
  "drive_impact_counter", "drive_impact_vs_di", "stuff_dash",
  "stuff_drive_rush", "jump_attack", "hit_confirm",
  "blocked_their_string", "hit", "hit_high", "hit_mid", "hit_low",
  "reversal",
];
const DEFENSE_TALLY_KEYS = [
  "whiff", "got_hit", "got_hit_high", "got_hit_mid", "got_hit_low",
  "throw_whiff", "throw_got_teched", "got_drive_impact_countered",
  "lost_di_clash", "dash_got_stuffed", "drive_rush_got_stuffed",
  "block_miss", "parry_miss", "got_thrown", "got_counter_hit",
  "got_punish_countered", "got_blocked", "got_parried", "got_anti_aired",
  "got_drive_impacted", "got_jump_attacked", "got_hit_confirmed",
  "non_hit_confirm", "parry_whiff", "got_reversaled",
];

const POSITION_PRESETS = [
  "dummy_corner_right", "dummy_corner_left", "player_corner_left",
  "player_corner_right", "center", "center_reversed",
];

const BLOCK_SETTINGS = ["block_after_first_hit", "no_guard", "all_block", "random_guard"];

const CHARACTER_IDS = [
  "ryu", "luke", "kimberly", "chun_li", "manon", "zangief", "jp", "dhalsim",
  "cammy", "ken", "dee_jay", "lily", "blanka", "juri", "marisa", "guile",
  "honda", "jamie", "mai",
];

let TRAINS_CATEGORIES = [
  "whiff", "got_hit", "got_hit_high", "got_hit_mid", "got_hit_low",
  "block_miss", "parry_miss",
  "got_thrown", "throw_whiff", "throw_got_teched",
  "got_counter_hit", "got_punish_countered",
  "got_blocked", "got_parried", "got_anti_aired",
  "got_drive_impacted", "got_drive_impact_countered", "lost_di_clash",
  "dash_got_stuffed", "drive_rush_got_stuffed", "got_jump_attacked",
  "got_hit_confirmed", "non_hit_confirm", "parry_whiff",
  "got_reversaled", "got_backrolled", "no_backroll",
];

let TRAINS_FOR_CATEGORIES = [
  "anti_air", "throw", "throw_missed_me", "throw_tech", "counter_hit",
  "punish_counter_hit", "block", "parry", "perfect_parry", "drive_impact",
  "drive_impact_counter", "drive_impact_vs_di", "stuff_dash",
  "stuff_drive_rush", "jump_attack", "hit_confirm", "reversal", "backroll",
  "blocked_their_string", "hit", "hit_high", "hit_mid", "hit_low",
];

const REVERSAL_TYPE_TO_INT = { NORMAL: 0, COMMAND_NORMAL: 1, SPECIAL: 2, SA: 3, COMMON: 5 };
const REVERSAL_TYPE_LABELS = {
  COMMON: "Common (jump/dash/throw/parry/DI/do-nothing)",
  NORMAL: "Normal (5LP-5HK, cr.LP-cr.HK)",
  COMMAND_NORMAL: "Command Normal",
  SPECIAL: "Special",
  SA: "Super Art",
};
const REVERSAL_TYPES = Object.keys(REVERSAL_TYPE_TO_INT);

const _skillListCache = new Map();
async function fetchReversalSkills(type, dummy) {
  const key = `${type}|${dummy || ""}`;
  if (_skillListCache.has(key)) return _skillListCache.get(key);
  const params = new URLSearchParams({ type });
  if (dummy) params.set("dummy", dummy);
  const promise = fetch(`/api/reversal-skills?${params}`)
    .then((r) => r.json())
    .then((d) => d.skills || [])
    .catch(() => []);
  _skillListCache.set(key, promise);
  return promise;
}

const GRADE_CLASS = { 1: "g-again", 2: "g-hard", 3: "g-good", 4: "g-easy" };
const GRADE_LABELS = { 1: "Again", 2: "Hard", 3: "Good", 4: "Easy" };

let editingDrillId = null;
let editingDrillOriginal = null;
let fixedResponseSelected = new Set();

let trainsSelected = new Set();

let trainsForSelected = new Set();

let fixedComboText = null;
let slotRows = [];

const SLOT_KIND_LABELS = {
  reversal: "Wake-up Reversal",
  block_reversal: "Block Reversal",
  damage_reversal: "Reversal After Damage",
  recording: "Recording",
};
const SLOT_KIND_TO_TS_KEY = {
  reversal: "reversal_slots",
  block_reversal: "block_reversal_slots",
  damage_reversal: "damage_reversal_slots",
  recording: "recording_slots",
};

const SLOT_KIND_MAX_INDEX = {
  reversal: 9, block_reversal: 9, damage_reversal: 9,
  recording: 7,
};

const REPEAT_REPLAY_LABELS = { off: "Off", on: "On", always: "Always Repeat Playback" };

function normalizeRecordingSlotEntry(entry) {
  if (typeof entry === "object" && entry !== null) return entry;
  return { index: entry };
}

function kindForSlotIndex(ts, index) {
  if ((ts.recording_slots || []).some((e) => normalizeRecordingSlotEntry(e).index === index)) return "recording";
  if ((ts.reversal_slots || []).some((c) => c.index === index)) return "reversal";
  if ((ts.block_reversal_slots || []).some((c) => c.index === index)) return "block_reversal";
  if ((ts.damage_reversal_slots || []).some((c) => c.index === index)) return "damage_reversal";
  return "reversal";
}

function configForSlotIndex(ts, kind, index) {
  const tsKey = SLOT_KIND_TO_TS_KEY[kind];
  if (kind === "recording") {
    const entry = (ts.recording_slots || []).find((e) => normalizeRecordingSlotEntry(e).index === index);
    return entry ? normalizeRecordingSlotEntry(entry) : null;
  }
  return (ts[tsKey] || []).find((c) => c.index === index) || null;
}

function buildSlotRowsFor(drill, ts) {
  const rows = [];
  const seen = new Set();
  const push = (kind, index) => {
    if (!Number.isInteger(index) || seen.has(kind + ":" + index)) return;
    seen.add(kind + ":" + index);
    const outcome = (drill.slot_outcomes || {})[String(index)];
    const recordingCfg = kind === "recording" ? configForSlotIndex(ts, kind, index) : null;
    rows.push({
      index, kind,

      expectedResponseRaw: (outcome && outcome.expected_response) || null,
      action: actionFromConfig(configForSlotIndex(ts, kind, index)),
      weight: (recordingCfg && recordingCfg.weight) || 1,
      pattern: (recordingCfg && recordingCfg.pattern) || null,

      actionText: (recordingCfg && recordingCfg.action_text) || undefined,
      selected: toResponseSet(outcome && outcome.expected_response),
      note: (outcome && outcome.note) || "",
    });
  };

  (ts.recording_slots || []).forEach(
    (e) => push("recording", normalizeRecordingSlotEntry(e).index));
  ["reversal", "block_reversal", "damage_reversal"].forEach((kind) => {
    (ts[SLOT_KIND_TO_TS_KEY[kind]] || []).forEach(
      (c) => push(kind, typeof c === "number" ? c : c.index));
  });

  Object.keys(drill.slot_outcomes || {}).forEach((k) => {
    const index = parseInt(k, 10);
    push(kindForSlotIndex(ts, index), index);
  });

  return rows.sort((a, b) => a.index - b.index);
}

function actionFromConfig(cfg) {
  if (!cfg || cfg.type === undefined || cfg.skill_index === undefined) {
    return { type: "COMMON", skillIndex: null, delay: 0 };
  }
  const typeName = Object.keys(REVERSAL_TYPE_TO_INT).find((k) => REVERSAL_TYPE_TO_INT[k] === cfg.type);
  return { type: typeName || "COMMON", skillIndex: cfg.skill_index, delay: cfg.delay || 0 };
}

let deleteTargetId = null;
let deleteTargetName = null;

async function fetchJSON(url, options) {
  const resp = await fetch(url, options);
  let body = null;
  try { body = await resp.json(); } catch (e) {  }
  return { ok: resp.ok, status: resp.status, body };
}

function toResponseSet(expectedResponse) {
  const set = new Set();
  if (Array.isArray(expectedResponse)) expectedResponse.forEach((c) => set.add(c));
  else if (expectedResponse) set.add(expectedResponse);
  return set;
}
function fromResponseSet(set) {
  const list = RESPONSE_CATEGORIES.filter((c) => set.has(c));
  if (list.length === 0) return null;
  if (list.length === 1) return list[0];
  return list;
}

function isChippable(expectedResponse) {
  if (expectedResponse === null || expectedResponse === undefined) return true;
  const parts = Array.isArray(expectedResponse) ? expectedResponse : [expectedResponse];
  return parts.every((c) => RESPONSE_CATEGORIES.includes(c));
}

function slotOutcomeFor(row) {
  const fromChips = fromResponseSet(row.selected);
  if (fromChips !== null) return fromChips;

  return isChippable(row.expectedResponseRaw) ? null : row.expectedResponseRaw;
}

async function refreshOverview() {
  const el = document.getElementById("overview-badges");
  const cardCountsEl = document.getElementById("card-counts-body");
  if (!el && !cardCountsEl) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/overview"));
  if (!ok) {
    if (el) el.innerHTML = "";
    return;
  }
  if (el) {

    const t = (s) => (window.i18n ? window.i18n.T(s) : s);
    el.innerHTML = `
      <span class="badge">${t("New")} <b>${body.new}</b></span>
      <span class="badge">${t("Learning")} <b>${body.learning}</b></span>
      <span class="badge">${t("Review")} <b>${body.review}</b></span>
      <span class="badge due">${t("Due now")} <b>${body.due_now}</b></span>
    `;
  }
  if (cardCountsEl) renderCardCounts(body);
}

const CARD_COUNT_COLORS = {
  new: "var(--accent)", learning: "var(--prog)",
  review_young: "var(--research)", review_mature: "var(--done)",
};
const CARD_COUNT_LABELS = { new: "New", learning: "Learning", review_young: "Young", review_mature: "Mature" };

function renderCardCounts(overview) {
  const el = document.getElementById("card-counts-body");
  if (!el) return;
  const total = overview.total || 0;
  if (total === 0) {
    el.innerHTML = `<p class="dim">No drills yet.</p>`;
    return;
  }
  const keys = ["new", "learning", "review_young", "review_mature"];
  let acc = 0;
  const stops = keys.map((k) => {
    const pct = (100 * (overview[k] || 0)) / total;
    const start = acc;
    acc += pct;
    return `${CARD_COUNT_COLORS[k]} ${start}% ${acc}%`;
  }).join(", ");
  const legend = keys.map((k) => `
    <div class="legend-row">
      <span class="legend-swatch" style="background:${CARD_COUNT_COLORS[k]}"></span>
      <span>${CARD_COUNT_LABELS[k]}</span>
      <b>${overview[k]}</b>
      <span class="dim">${Math.round((1000 * (overview[k] || 0)) / total) / 10}%</span>
    </div>
  `).join("");
  el.innerHTML = `
    <div class="donut donut-lg" style="background:conic-gradient(${stops})"><div class="donut-hole donut-hole-lg">${total}</div></div>
    <div class="legend-list">${legend}</div>
  `;
}

function localDateKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function windowDateRange(daysDict, period, defaultValue) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let start;
  if (period === "all") {
    const keys = Object.keys(daysDict).sort();
    start = keys.length ? new Date(keys[0] + "T00:00:00") : new Date(today);
  } else {
    start = new Date(today);
    start.setDate(start.getDate() - (Number(period) - 1));
  }
  const result = [];
  const cursor = new Date(start);
  while (cursor <= today) {
    const key = localDateKey(cursor);
    const value = Object.prototype.hasOwnProperty.call(daysDict, key) ? daysDict[key] : defaultValue;
    result.push([key, value]);
    cursor.setDate(cursor.getDate() + 1);
  }
  return result;
}

function renderBarChart(container, items, opts = {}) {
  if (!items.length) {
    container.innerHTML = `<p class="dim">No data yet.</p>`;
    return;
  }
  const max = Math.max(1, ...items.map((i) => i.value || 0));
  const showLabels = opts.showLabels !== false;
  const labelEvery = opts.labelEvery || 1;
  const bars = items.map((item, idx) => {
    const pct = item.value > 0 ? Math.max(2, Math.round((100 * item.value) / max)) : 0;
    const color = item.color || "var(--accent)";
    const valueText = opts.formatValue ? opts.formatValue(item.value) : item.value;
    const tooltip = item.tooltip || `${item.label}: ${valueText}`;
    const label = showLabels && idx % labelEvery === 0
      ? `<div class="bar-label">${escapeHTML(item.label)}</div>` : "";
    return `
      <div class="bar-col" title="${escapeHTML(tooltip)}">
        <div class="bar-fill" style="height:${pct}%; background:${color}"></div>
        ${label}
      </div>
    `;
  }).join("");
  container.innerHTML = `<div class="bar-chart">${bars}</div>`;
}

function renderHistogram(container, values, opts = {}) {
  if (!values.length) {
    container.innerHTML = `<p class="dim">No data yet.</p>`;
    return;
  }
  const bucketSize = opts.bucketSize || 1;
  const counts = {};
  values.forEach((v) => {
    const bucket = Math.round(v / bucketSize) * bucketSize;
    counts[bucket] = (counts[bucket] || 0) + 1;
  });
  const keys = Object.keys(counts).map(Number).sort((a, b) => a - b);
  const items = keys.map((k) => ({
    label: opts.formatLabel ? opts.formatLabel(k) : String(k),
    value: counts[k],
  }));
  renderBarChart(container, items, { showLabels: true, labelEvery: Math.max(1, Math.ceil(items.length / 12)) });
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function statLineHTML(label, value) {
  return `<div class="live-stat"><div class="label">${escapeHTML(label)}</div><div class="value">${value}</div></div>`;
}

async function refreshToday() {
  const el = document.getElementById("today-body");
  if (!el) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/reviews"));
  if (!ok) return;
  const today = body.days[localDateKey(new Date())];
  el.innerHTML = today
    ? statLineHTML(t("Sessions Today"), today.sessions) + statLineHTML(t("Attempts"), today.attempts) + statLineHTML(t("Successes"), today.successes)
    : `<p class="dim">No drills studied today.</p>`;
}

async function refreshForecast() {
  const chartEl = document.getElementById("forecast-chart");
  if (!chartEl) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/forecast"));
  if (!ok) return;
  const days = Object.keys(body.days).sort().slice(0, 30);
  const items = days.map((d) => ({ label: d, value: body.days[d] }));
  renderBarChart(chartEl, items, { showLabels: false, formatValue: (v) => `${v} due` });
  const avg = days.length ? Math.round((10 * days.reduce((a, d) => a + body.days[d], 0)) / days.length) / 10 : 0;
  document.getElementById("forecast-stats").innerHTML =
    statLineHTML(t("Backlog"), body.backlog) + statLineHTML(t("Total"), body.total) + statLineHTML(t("Average/day"), avg);
}

const periodState = { reviews: "all", added: "all" };
let reviewsPayload = null;
let addedPayload = null;
let calendarYear = new Date().getFullYear();

async function refreshReviews() {
  const chartEl = document.getElementById("reviews-chart");
  const calendarEl = document.getElementById("calendar-grid");
  if (!chartEl && !calendarEl) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/reviews"));
  if (!ok) return;
  reviewsPayload = body;
  renderReviewsChart();
  renderCalendar();
}

function renderReviewsChart() {
  const chartEl = document.getElementById("reviews-chart");
  if (!chartEl || !reviewsPayload) return;
  const days = windowDateRange(reviewsPayload.days, periodState.reviews, { attempts: 0, successes: 0, sessions: 0 });
  const items = days.map(([date, d]) => ({ label: date, value: d.attempts }));
  renderBarChart(chartEl, items, { showLabels: false, formatValue: (v) => `${v} attempts` });
  const daysStudied = days.filter(([, d]) => d.sessions > 0).length;
  const totalAttempts = items.reduce((a, i) => a + i.value, 0);
  document.getElementById("reviews-stats").innerHTML =
    statLineHTML(t("Days studied"), `${daysStudied} / ${days.length}`) +
    statLineHTML(t("Total attempts"), totalAttempts) +
    statLineHTML(t("Sessions"), reviewsPayload.total_sessions);
}

function renderCalendar() {
  const grid = document.getElementById("calendar-grid");
  if (!grid || !reviewsPayload) return;
  document.getElementById("calendar-year-label").textContent = calendarYear;
  const days = reviewsPayload.days;
  const maxCount = Math.max(1, ...Object.values(days).map((d) => d.attempts));
  const yearStart = new Date(calendarYear, 0, 1);
  const yearEnd = new Date(calendarYear, 11, 31);
  const gridStart = new Date(yearStart);
  gridStart.setDate(gridStart.getDate() - gridStart.getDay());
  const cells = [];
  const cursor = new Date(gridStart);
  while (cursor <= yearEnd) {
    const inYear = cursor.getFullYear() === calendarYear;
    const key = localDateKey(cursor);
    cells.push({ key, count: inYear ? (days[key] ? days[key].attempts : 0) : null, inYear });
    cursor.setDate(cursor.getDate() + 1);
  }
  grid.innerHTML = cells.map((c) => {
    if (!c.inYear) return `<div class="cal-cell cal-cell-pad"></div>`;
    const alpha = c.count > 0 ? Math.min(1, 0.15 + 0.85 * (c.count / maxCount)) : 0;

    const bg = c.count > 0 ? `rgba(255,210,0,${alpha})` : "var(--bg2)";
    return `<div class="cal-cell" style="background:${bg}" title="${c.key}: ${c.count} attempts"></div>`;
  }).join("");
  grid.style.gridTemplateRows = "repeat(7, 1fr)";
  grid.style.gridTemplateColumns = `repeat(${Math.ceil(cells.length / 7)}, 1fr)`;
  grid.style.gridAutoFlow = "column";
}

async function refreshIntervalsAndEase() {
  const intervalsEl = document.getElementById("intervals-chart");
  const easeEl = document.getElementById("ease-chart");
  if (!intervalsEl && !easeEl) return;
  const { ok, body } = await fetchJSON("/api/drills");
  if (!ok) return;
  const intervals = body.map((d) => Math.round(d.interval_days)).filter((v) => Number.isFinite(v));
  const eases = body.map((d) => d.ease_factor).filter((v) => Number.isFinite(v));
  if (intervalsEl) {
    renderHistogram(intervalsEl, intervals, { bucketSize: 1, formatLabel: (v) => `${v}d` });
    const m = median(intervals);
    document.getElementById("intervals-stat").innerHTML = statLineHTML(t("Median interval"), m == null ? "-" : `${m}d`);
  }
  if (easeEl) {
    const easePercents = eases.map((e) => Math.round(e * 100));
    renderHistogram(easeEl, easePercents, { bucketSize: 10, formatLabel: (v) => `${v}%` });
    const m = median(easePercents);
    document.getElementById("ease-stat").innerHTML = statLineHTML(t("Median ease"), m == null ? "-" : `${m}%`);
  }
}

async function refreshRetention() {
  const wrap = document.getElementById("retention-table-wrap");
  if (!wrap) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/retention"));
  if (!ok) return;
  const rows = [
    ["Today", "today"], ["Yesterday", "yesterday"], ["Last week", "last_week"],
    ["Last month", "last_month"], ["Last year", "last_year"], ["All time", "all_time"],
  ];
  const fmt = (v) => (v == null ? "N/A" : `${v}%`);
  wrap.innerHTML = `
    <table class="history-table">
      <thead><tr><th></th><th>Young</th><th>Mature</th><th>Total</th><th>Count</th></tr></thead>
      <tbody>
        ${rows.map(([label, key]) => {
          const r = body[key];
          return `<tr><td><b>${label}</b></td><td>${fmt(r.young)}</td><td>${fmt(r.mature)}</td><td>${fmt(r.total)}</td><td>${r.count}</td></tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

async function refreshHourly() {
  const el = document.getElementById("hourly-chart");
  if (!el) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/hourly"));
  if (!ok) return;
  const items = body.hours.map((h) => ({
    label: String(h.hour),
    value: h.success_rate == null ? 0 : h.success_rate,
    tooltip: `${h.hour}:00 -- ${h.success_rate == null ? "no data" : h.success_rate + "% (" + h.attempts + " attempts)"}`,
  }));
  renderBarChart(el, items, { showLabels: true, labelEvery: 2 });
}

async function refreshAnswerButtons() {
  const el = document.getElementById("answer-buttons-chart");
  if (!el) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/answer_buttons"));
  if (!ok) return;
  const items = [
    { label: "Again", value: body.by_grade["1"], color: "var(--danger)" },
    { label: "Hard", value: body.by_grade["2"], color: "var(--prog)" },
    { label: "Good", value: body.by_grade["3"], color: "var(--done)" },
    { label: "Easy", value: body.by_grade["4"], color: "var(--accent)" },
  ];
  renderBarChart(el, items, { showLabels: true });
}

async function refreshAdded() {
  const chartEl = document.getElementById("added-chart");
  if (!chartEl) return;
  const { ok, body } = await fetchJSON(statsUrl("/api/stats/added"));
  if (!ok) return;
  addedPayload = body;
  renderAddedChart();
}

function renderAddedChart() {
  const chartEl = document.getElementById("added-chart");
  if (!chartEl || !addedPayload) return;
  const days = windowDateRange(addedPayload.days, periodState.added, 0);
  const items = days.map(([date, v]) => ({ label: date, value: v }));
  renderBarChart(chartEl, items, { showLabels: false, formatValue: (v) => `${v} added` });
  document.getElementById("added-stats").innerHTML =
    statLineHTML(t("Total"), addedPayload.total) + statLineHTML(t("Average/day"), addedPayload.average_per_day);
}

async function refreshLive() {
  const { ok, body } = await fetchJSON("/api/live");
  const freshnessEl = document.getElementById("live-freshness");
  const bodyEl = document.getElementById("live-body");
  if (!bodyEl) return;
  if (!ok || !body) return;

  if (body.is_stale || !body.live_status) {
    freshnessEl.textContent = "no live data (game not running?)";
    freshnessEl.className = "freshness stale";
    bodyEl.innerHTML = `<p class="dim">Waiting for a live session status...</p>`;
    return;
  }

  freshnessEl.textContent = `live (${body.live_status_age_seconds.toFixed(1)}s ago)`;
  freshnessEl.className = "freshness live";

  const s = body.live_status;
  syncMatchupFromLive(s);
  const tally = s.criteria_tally || {};
  const bySide = s.criteria_tally_side || { left: {}, right: {} };

  bodyEl.innerHTML = `
    <div class="live-stat"><div class="label">${t("Session")}</div><div class="value">${s.session_status ?? "-"}</div></div>
    <div class="live-stat"><div class="label">${t("Attempt")}</div><div class="value">${s.session_attempt_count ?? 0}/${s.session_attempts_target ?? "?"}</div></div>
    <div class="live-stat"><div class="label">${t("Successes")}</div><div class="value">${s.session_success_count ?? 0}</div></div>
    ${renderTallyPairs(tally, bySide)}
  `;
}

const TALLY_PAIRS = [
  ["hit", "got_hit"],
  ["hit_high", "got_hit_high"],
  ["hit_mid", "got_hit_mid"],
  ["hit_low", "got_hit_low"],
  ["hit_confirm", "got_hit_confirmed"],
  ["blocked_their_string", "non_hit_confirm"],
  ["block", "got_blocked"],
  ["parry", "got_parried"],
  ["perfect_parry", "parry_whiff"],
  [null, "parry_miss"],
  [null, "block_miss"],
  [null, "whiff"],
  ["counter_hit", "got_counter_hit"],
  ["punish_counter_hit", "got_punish_countered"],
  ["anti_air", "got_anti_aired"],
  ["jump_attack", "got_jump_attacked"],
  ["throw", "got_thrown"],
  ["throw_tech", "throw_got_teched"],
  ["throw_missed_me", "throw_whiff"],
  ["drive_impact", "got_drive_impacted"],
  ["drive_impact_counter", "got_drive_impact_countered"],
  ["drive_impact_vs_di", "lost_di_clash"],
  ["stuff_dash", "dash_got_stuffed"],
  ["stuff_drive_rush", "drive_rush_got_stuffed"],
];

function renderTallyPairs(tally, bySide) {
  const left = (bySide && bySide.left) || {};
  const right = (bySide && bySide.right) || {};
  const half = (k, side) => {
    if (!k) return `<span class="tly-half tly-${side} tly-blank"></span>`;
    const l = left[k] ?? 0, r = right[k] ?? 0;
    return `
      <span class="tly-half tly-${side}" title="${k} -- left ${l} / right ${r}">
        <span class="tly-name">${counterLabel(k)}</span>
        <b class="tly-num">${tally[k] ?? 0}</b>
        <i class="tly-sides" title="left ${l} / right ${r}">${l}<span>/</span>${r}</i>
      </span>`;
  };

  const pairs = TALLY_PAIRS
    .map(([mine, theirs]) => `<div class="tly-pair">${half(mine, "mine")}${half(theirs, "theirs")}</div>`)
    .join("");

  return `
    <div class="tally-section">
      <div class="tly-legend">
        <span class="tly-key tly-mine">${t("In my favour")}</span>
        <span class="tly-key tly-theirs">${t("Against me")}</span>
      </div>
      <div class="tly-grid">${pairs}</div>
    </div>
  `;
}

function renderTallySection(title, keys, tally, bySide) {
  const left = (bySide && bySide.left) || {};
  const right = (bySide && bySide.right) || {};
  const cells = keys.map((k) => `
    <div class="tally-cell">
      <span>${k}</span>
      <span class="tally-nums">
        <b>${tally[k] ?? 0}</b>
        <i class="tally-side" title="left side">L ${left[k] ?? 0}</i>
        <i class="tally-side" title="right side">R ${right[k] ?? 0}</i>
      </span>
    </div>`).join("");
  return `
    <div class="tally-section">
      <div class="tally-section-title">${title}</div>
      <div class="tally-grid">${cells}</div>
    </div>
  `;
}

let hitZoneStats = {};

let hitZoneDirection = localStorage.getItem("bd.hitzones.direction") || "taken";

function lerpZoneColor(pct) {
  const blue = [0x57, 0xa5, 0xff];
  const red = [0xff, 0x6b, 0x6b];
  const t = Math.max(0, Math.min(1, (pct || 0) / 100));
  const rgb = blue.map((b, i) => Math.round(b + (red[i] - b) * t));
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

const MATCHUP_STORAGE_KEY = "beastdrills.matchup";

const FOLLOW_GAME_STORAGE_KEY = "beastdrills.followGame";
let followGame = false;
const matchup = { player: null, dummy: null };
let matchupActiveSlot = "player";

function loadMatchup() {
  try {
    followGame = localStorage.getItem(FOLLOW_GAME_STORAGE_KEY) === "1";
  } catch {  }
  try {
    const saved = JSON.parse(localStorage.getItem(MATCHUP_STORAGE_KEY) || "{}");
    if (CHARACTER_ROSTER.includes(saved.player)) matchup.player = saved.player;
    if (CHARACTER_ROSTER.includes(saved.dummy)) matchup.dummy = saved.dummy;
  } catch {  }
}

function saveMatchup() {
  try {
    localStorage.setItem(FOLLOW_GAME_STORAGE_KEY, followGame ? "1" : "0");
    localStorage.setItem(MATCHUP_STORAGE_KEY, JSON.stringify(matchup));
  } catch {  }
}

function characterTileUrl(characterId, selected) {
  return `/static/character_select/${characterId}${selected ? "_over" : ""}.png`;
}

function buildCharacterSelect() {
  const strip = document.getElementById("hz-charselect");
  if (!strip) return;
  strip.innerHTML = CHARACTER_ROSTER.map((c) => `
    <button type="button" class="charselect-tile" data-character="${c}" role="option"
            aria-selected="false" title="${characterLabel(c)}">
      <img src="${characterTileUrl(c, false)}" alt="${characterLabel(c)}" loading="lazy">
    </button>`).join("");

  strip.querySelectorAll(".charselect-tile").forEach((tile) => {
    tile.addEventListener("click", () => pickCharacter(tile.dataset.character));
  });
  document.querySelectorAll(".matchup-slot").forEach((slot) => {
    slot.addEventListener("click", () => {
      matchupActiveSlot = slot.dataset.slot;
      renderMatchup();
    });
  });
  renderMatchup();
}

function pickCharacter(characterId) {

  if (followGame) {
    followGame = false;
    const box = document.getElementById("hz-follow-game");
    if (box) box.checked = false;
  }
  matchup[matchupActiveSlot] = characterId;
  matchupActiveSlot = matchupActiveSlot === "player" ? "dummy" : "player";
  saveMatchup();
  renderMatchup();
  renderHitZonesForMatchup();
}

function renderMatchup() {
  document.querySelectorAll(".charselect-tile").forEach((tile) => {
    const c = tile.dataset.character;
    const isPlayer = matchup.player === c;
    const isDummy = matchup.dummy === c;
    tile.classList.toggle("is-player", isPlayer);
    tile.classList.toggle("is-dummy", isDummy);
    tile.setAttribute("aria-selected", String(isPlayer || isDummy));
    tile.dataset.role = isPlayer ? "P1" : isDummy ? "P2" : "";
    const src = characterTileUrl(c, isPlayer || isDummy);
    const img = tile.querySelector("img");
    if (!img.src.endsWith(src)) img.src = src;
  });
  document.querySelectorAll(".matchup-slot").forEach((slot) => {
    slot.classList.toggle("is-active", slot.dataset.slot === matchupActiveSlot);
  });
  document.querySelectorAll("[data-slot-name]").forEach((el) => {
    const picked = matchup[el.dataset.slotName];
    el.textContent = picked ? characterLabel(picked) : "—";
  });
}

let hitZoneSprites = null;

async function loadHitZoneSprites() {
  if (hitZoneSprites) return hitZoneSprites;
  try {
    const r = await fetch("/static/hitzone/manifest.json");
    hitZoneSprites = r.ok ? new Set(await r.json()) : new Set();
  } catch {
    hitZoneSprites = new Set();
  }
  return hitZoneSprites;
}

const ZONE_STOPS = {

  blanka:  [22, 42, 62, 80],

  elena:   [12, 28, 46, 64],

  manon:   [14, 30, 48, 62],

  ingrid:  [20, 40, 60, 78],

  dhalsim: [16, 34, 50, 66],
};

function spriteFigure(id, label, fill) {
  const url = `/static/hitzone/${id}.png`;
  const s = ZONE_STOPS[id];
  const stops = s ? `--z1:${s[0]}%; --z2:${s[1]}%; --z3:${s[2]}%; --z4:${s[3]}%;` : "";
  return `
    <div class="hz-fig" style="--sprite:url('${url}')" role="img"
         aria-label="${label} hit zones">
      <img class="hz-fig-base" src="${url}" alt="">
      <div class="hz-fig-zones" style="${stops} --c-high:${fill("high")};
           --c-mid:${fill("mid")}; --c-low:${fill("low")}"></div>
    </div>`;
}

function genericFigure(label, fill) {
  return `
    <svg class="body-silhouette" viewBox="0 0 120 220" role="img" aria-label="${label} hit zones">
      <circle style="fill:${fill("high")}" cx="60" cy="28" r="24"></circle>
      <path style="fill:${fill("mid")}" d="M25,58 Q60,48 95,58 L88,140 L32,140 Z"></path>
      <path style="fill:${fill("low")}" d="M40,140 L55,140 L52,218 L35,218 Z"></path>
      <path style="fill:${fill("low")}" d="M80,140 L65,140 L68,218 L85,218 Z"></path>
    </svg>`;
}

function renderSideFigure(el, label, stats, characterId) {
  const counts = (stats && stats.counts) || {};
  const pct = (stats && stats.percentages) || { high: 0, mid: 0, low: 0, total: 0 };
  const total = pct.total || 0;
  el.classList.toggle("is-empty", !total);
  const fill = (z) => lerpZoneColor(pct[z] || 0);
  const hasSprite = characterId && hitZoneSprites && hitZoneSprites.has(characterId);
  el.innerHTML = `
    <div class="hz-side-label">${label}</div>
    ${hasSprite ? spriteFigure(characterId, label, fill) : genericFigure(label, fill)}
    <div class="hz-side-rows">
      ${["high", "mid", "low"].map((z) => `
        <div class="hz-side-row"><span>${z.toUpperCase()}</span>
          <span><b>${pct[z] || 0}%</b> (${counts[z] || 0})</span></div>`).join("")}
    </div>
    <div class="hz-side-total">${total ? `<b>${total}</b> hits` : "no hits yet"}</div>`;
}

function sideStatsFor(entry, side) {
  if (!entry) return null;

  if (!matchup.dummy) return (entry.by_side || {})[side] || null;
  const picked = (entry.by_dummy || {})[matchup.dummy];
  if (!picked) return null;
  return (picked.by_side || {})[side] || null;
}

function hitZoneVictim() {
  if (hitZoneDirection !== "dealt") return matchup.player;
  return matchup.dummy || null;
}

function renderHitZoneWhose(victim) {
  const el = document.getElementById("hz-whose");
  if (!el) return;
  if (hitZoneDirection !== "dealt") {
    el.textContent = victim ? `where ${characterLabel(victim)} gets hit` : "";
    return;
  }
  el.textContent = victim
    ? `where you hit ${characterLabel(victim)}`
    : "where you hit — pick a dummy to see whose body";
}

function renderHitZonesForMatchup() {
  const left = document.getElementById("hz-side-left");
  const right = document.getElementById("hz-side-right");
  if (!left || !right || !hitZoneStats) return;
  const entry = matchup.player ? hitZoneStats[matchup.player] : null;
  const victim = hitZoneVictim();
  renderHitZoneWhose(victim);

  renderSideFigure(left, "Left side", sideStatsFor(entry, "left"), victim);
  renderSideFigure(right, "Right side", sideStatsFor(entry, "right"), victim);
}

function syncMatchupFromLive(live) {
  if (!followGame || !live) return;
  const pick = (id, raw) => id || (raw != null ? `fighter_${raw}` : null);
  const player = pick(live.p1_character_id, live.p1_fighter_id);
  const dummy = pick(live.p2_character_id, live.p2_fighter_id);
  let changed = false;
  if (player && matchup.player !== player) { matchup.player = player; changed = true; }
  if (dummy && matchup.dummy !== dummy) { matchup.dummy = dummy; changed = true; }
  if (changed) {
    saveMatchup();
    renderMatchup();
    renderHitZonesForMatchup();
  }
}

async function refreshHitZones() {
  if (!document.getElementById("hz-side-left")) return;
  await loadHitZoneSprites();
  const route = hitZoneDirection === "dealt"
    ? "/api/stats/hit_zones_dealt"
    : "/api/stats/hit_zones";
  const { ok, body } = await fetchJSON(statsUrl(route));
  if (!ok || !body) return;
  hitZoneStats = body;
  if (!matchup.player) {
    const available = Object.keys(body).sort();
    if (available.length > 0) {
      matchup.player = available[0];
      saveMatchup();
      renderMatchup();
    }
  }
  renderHitZonesForMatchup();
}

let allDrills = [];

const DRILL_PAGE = 200;

let drillSearchText = "";
let drillOffset = 0;
let drillMatched = 0;

let drillTotal = 0;

async function refreshDrills({ append = false } = {}) {
  const grid = document.getElementById("drills-grid");
  if (!grid) return;

  if (!append) drillOffset = 0;
  const params = new URLSearchParams({
    limit: String(DRILL_PAGE),
    offset: String(drillOffset),
  });
  const query = combinedDrillQuery();
  if (query) params.set("q", query);

  const { ok, body } = await fetchJSON(`/api/drills?${params}`);
  if (!ok) {
    grid.innerHTML = `<p class="dim">Could not load drills -- is beast_drills.service running?</p>`;
    return;
  }

  const rows = Array.isArray(body) ? body : (body.drills || []);
  drillMatched = Array.isArray(body) ? rows.length : (body.matched ?? rows.length);

  allDrills = append ? allDrills.concat(rows) : rows;
  drillOffset = allDrills.length;

  if (drillTotal === 0) await populateDrillFilterOptions();
  renderDrillsGrid();
  renderDrillsMore();
}

function renderDrillsMore() {
  const wrap = document.getElementById("drills-more");
  if (!wrap) return;
  const remaining = Math.max(0, drillMatched - allDrills.length);
  wrap.classList.toggle("hidden", remaining === 0);
  const count = document.getElementById("drills-more-count");
  if (count) {
    count.textContent = remaining
      ? `showing ${allDrills.length} of ${drillMatched}`
      : "";
  }
}

const DRILL_TYPE_ORDER = ["recording", "reversal", "combo", "none"];
const DRILL_TYPE_LABELS = { recording: "Recording", reversal: "Reversal", combo: "Combo", none: "None" };
const UNSET_FILTER_VALUE = "__unset__";
const drillFilters = { type: "", character: "", dummy: "" };

function populateOptionsPreserving(selectEl, options, blankLabel) {
  const prev = selectEl.value;
  selectEl.innerHTML = `<option value="">${blankLabel}</option>` +
    options.map((o) => `<option value="${o.value}">${escapeHTML(o.label)}</option>`).join("");
  selectEl.value = options.some((o) => o.value === prev) ? prev : "";
}

function populateCharacterFilterSelect(selectEl, characterIds, hasUnset) {
  const options = Array.from(new Set(characterIds.filter(Boolean)))
    .sort((a, b) => characterLabel(a).localeCompare(characterLabel(b)))
    .map((c) => ({ value: c, label: characterLabel(c) }));
  if (hasUnset) options.unshift({ value: UNSET_FILTER_VALUE, label: "Any/Unset" });
  populateOptionsPreserving(selectEl, options, "All");
}

function filterQueryTerms() {
  return ["type", "character", "dummy"]
    .filter((k) => drillFilters[k])
    .map((k) => `${k}:${drillFilters[k]}`);
}

function combinedDrillQuery() {
  return [drillSearchText, ...filterQueryTerms()].filter(Boolean).join(" ");
}

function readDrillFilterInputs() {
  drillFilters.type = document.getElementById("filter-type").value;
  drillFilters.character = document.getElementById("filter-character").value;
  drillFilters.dummy = document.getElementById("filter-dummy").value;
}

async function populateDrillFilterOptions() {
  const typeSelect = document.getElementById("filter-type");
  if (!typeSelect) return;

  const { ok, body } = await fetchJSON("/api/drills/facets");
  if (!ok) return;
  drillTotal = body.total || 0;

  const presentTypes = new Set(body.types || []);
  populateOptionsPreserving(
    typeSelect,
    DRILL_TYPE_ORDER.filter((t) => presentTypes.has(t)).map((t) => ({ value: t, label: DRILL_TYPE_LABELS[t] })),
    "All types"
  );
  populateCharacterFilterSelect(
    document.getElementById("filter-character"), body.characters || [], body.characters_unset);
  populateCharacterFilterSelect(
    document.getElementById("filter-dummy"), body.dummies || [], body.dummies_unset);

  readDrillFilterInputs();
}

function updateFilterStatus() {
  const countEl = document.getElementById("filter-count");
  if (!countEl) return;

  const total = drillTotal || allDrills.length;
  const anyActive = !!(drillSearchText || drillFilters.type || drillFilters.character || drillFilters.dummy);
  countEl.textContent = anyActive
    ? `${drillMatched} of ${total} drill${total === 1 ? "" : "s"}`
    : `${total} drill${total === 1 ? "" : "s"}`;
  const clearBtn = document.getElementById("filter-clear-btn");
  if (clearBtn) clearBtn.classList.toggle("hidden", !anyActive);
}

function renderDrillsGrid() {
  const grid = document.getElementById("drills-grid");
  if (!grid) return;
  const filtered = allDrills;
  if (filtered.length === 0) {
    grid.innerHTML = drillTotal === 0
      ? `<p class="dim">No drills yet.</p>`
      : `<p class="dim drills-empty-state">No drills match the current filters.</p>`;
  } else {
    grid.innerHTML = filtered.map(cardHTML).join("");
    filtered.forEach((d) => {
      document.getElementById(`edit-${d.id}`).addEventListener("click", () => openEditModal(d));
      document.getElementById(`delete-${d.id}`).addEventListener("click", () => openDeleteModal(d.id, d.name));
      document.getElementById(`history-${d.id}`).addEventListener("click", () => openHistoryModal(d.id));
      document.getElementById(`select-${d.id}`).addEventListener("change", (e) => {
        toggleDrillSelection(d.id, e.target.checked);
      });
      document.getElementById(`fav-${d.id}`).addEventListener("click", () => toggleDrillFavorite(d.id));
    });
  }
  updateFilterStatus();
  updateSelectionStatus();
}

function clearDrillFilters() {
  drillFilters.type = "";
  drillFilters.character = "";
  drillFilters.dummy = "";
  ["filter-type", "filter-character", "filter-dummy"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  refreshDrills();
}

function updateSelectionStatus() {
  const el = document.getElementById("selection-status-text");
  if (!el) return;
  const selectedCount = allDrills.filter((d) => d.selected).length;
  el.textContent = selectedCount > 0
    ? `${selectedCount} selected — only these will run`
    : `None selected — all drills will run`;
  el.classList.toggle("has-selection", selectedCount > 0);
}

const OUTBOX_RECONCILE_MS = 1200;

async function toggleDrillSelection(drillId, selected) {
  const drill = allDrills.find((d) => d.id === drillId);
  if (drill) drill.selected = selected;
  renderDrillsGrid();
  await fetchJSON(`/api/drills/${encodeURIComponent(drillId)}/selection`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected }),
  });
  setTimeout(refreshDrills, OUTBOX_RECONCILE_MS);
}

async function toggleDrillFavorite(drillId) {
  const drill = allDrills.find((d) => d.id === drillId);
  if (!drill) return;
  drill.favorite = !drill.favorite;
  const btn = document.getElementById(`fav-${drillId}`);
  if (btn) {
    btn.classList.toggle("on", drill.favorite);
    btn.innerHTML = drill.favorite ? "&#9733;" : "&#9734;";
    btn.setAttribute("aria-pressed", drill.favorite ? "true" : "false");
    btn.title = drill.favorite ? "In your favorites" : "Add to favorites";
  }
  await fetchJSON(`/api/drills/${encodeURIComponent(drillId)}/favorite`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ favorite: drill.favorite }),
  });
}

async function setSelectionForShown(selected) {
  const ids = allDrills.map((d) => d.id);
  if (ids.length === 0) return;
  const idSet = new Set(ids);
  allDrills.forEach((d) => { if (idSet.has(d.id)) d.selected = selected; });
  renderDrillsGrid();
  await fetchJSON("/api/drills/selection", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drill_ids: ids, selected }),
  });
  setTimeout(refreshDrills, OUTBOX_RECONCILE_MS);
}

function donutHTML(d) {
  if (!d.total_attempts) {
    return `<div class="donut" style="background:var(--bg2)"><div class="donut-hole">–</div></div>`;
  }
  const pct = Math.round((d.total_successes / d.total_attempts) * 100);
  return `
    <div class="donut" style="background:conic-gradient(var(--done) 0% ${pct}%, var(--danger) ${pct}% 100%)" title="${d.total_successes}/${d.total_attempts} lifetime successes">
      <div class="donut-hole">${pct}%</div>
    </div>
  `;
}

function gradeLineHTML(d) {
  if (d.average_grade === null || d.average_grade === undefined) {
    return `<div class="grade-line dim">Not attempted yet</div>`;
  }
  const lastPill = d.last_grade
    ? `<span class="grade-pill ${GRADE_CLASS[d.last_grade] || ""}">${d.last_grade_label}</span>`
    : "";
  return `
    <div class="grade-line">
      <span>Avg <b>${d.average_grade}</b></span>
      <span>Last ${lastPill}</span>
    </div>
  `;
}

function characterArtUrl(characterId, variant) {
  if (!characterId || !/^[a-z0-9_]+$/i.test(characterId)) return null;
  return `/static/characters/${characterId}${variant}.png`;
}

const PC_CHIPS_SHOWN = 6;

function perCharacterHTML(d) {
  const progress = d.character_progress || {};
  const names = Object.keys(progress);
  if (!names.length) return "";
  const now = new Date().toISOString();

  const rows = names.map((id) => {
    const p = progress[id] || {};
    return {
      id,
      sessions: p.total_sessions || 0,
      streak: p.streak || 0,
      due: !p.next_review || p.next_review <= now,
    };
  });

  rows.sort((a, b) =>
    (b.due - a.due) || (b.sessions - a.sessions) || a.id.localeCompare(b.id));

  const chip = (r, hidden) => {
    const name = escapeHTML(characterLabel(r.id));
    return `<span class="pc-chip${r.due ? " is-due" : ""}${hidden ? " pc-extra" : ""}"
      title="${name}: ${r.sessions} session${r.sessions === 1 ? "" : "s"}, streak ${r.streak}${r.due ? " -- due now" : ""}"
      >${name} ${r.sessions}</span>`;
  };

  const chips = rows.map((r, i) => chip(r, i >= PC_CHIPS_SHOWN)).join("");

  const more = rows.length > PC_CHIPS_SHOWN
    ? `<button class="pc-more" onclick="togglePerCharacter(this)"
         title="Show every character who has practised this">+${rows.length - PC_CHIPS_SHOWN} more</button>`
    : "";
  return `<div class="per-character is-clamped" title="Practised per character">${chips}${more}</div>`;
}

function togglePerCharacter(btn) {
  const row = btn.parentElement;
  const clamped = row.classList.toggle("is-clamped");
  const hidden = row.querySelectorAll(".pc-extra").length;
  btn.textContent = clamped ? `+${hidden} more` : "Less";
}

const DIFFICULTY_LABELS = {
  "very-easy": "V.EASY", easy: "EASY", medium: "MED",
  hard: "HARD", "very-hard": "V.HARD",
};

function difficultyTagHTML(difficulty) {
  if (!difficulty) return "";
  const key = String(difficulty).toLowerCase();
  const label = DIFFICULTY_LABELS[key];
  if (!label) return "";
  return `<span class="tag diff-${key}" title="Difficulty">${label}</span>`;
}

function isOrderedCriteria(v) {
  if (typeof v === "string") return v.includes(">");
  if (Array.isArray(v)) return v.some((x) => typeof x === "string" && x.includes(">"));
  return false;
}

function fillAdvancedCriteria(d) {
  const val = (id, v) => { const el = document.getElementById(id); if (el) el.value = v ?? ""; };
  const ordered = isOrderedCriteria(d.fixed_expected_response);
  val("f-adv-success", ordered
    ? (Array.isArray(d.fixed_expected_response)
        ? d.fixed_expected_response.join(", ") : d.fixed_expected_response)
    : "");
  val("f-against", (d.against_criteria || []).map(kebab).join(", "));
  val("f-setup", (d.expected_setup || []).map(kebab).join(", "));
  val("f-survive", d.survive_seconds ?? "");
  const err = document.getElementById("adv-criteria-error");
  if (err) err.classList.add("hidden");

  const box = document.getElementById("f-advanced-criteria");
  if (box) box.open = Boolean(ordered || d.against_criteria || d.expected_setup || d.survive_seconds);
}

function kebab(s) { return String(s).replace(/_/g, "-"); }

function readAdvancedCriteria() {
  const get = (id) => (document.getElementById(id)?.value || "").trim();
  return { success: get("f-adv-success"), against: get("f-against"),
           setup: get("f-setup"), survive: get("f-survive") };
}

async function validateAdvancedCriteria() {
  const adv = readAdvancedCriteria();
  const err = document.getElementById("adv-criteria-error");
  if (!adv.success && !adv.against && !adv.setup) {
    if (err) err.classList.add("hidden");
    return { ok: true, parsed: {} };
  }
  const { ok, body } = await fetchJSON("/api/criteria/validate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(adv),
  });
  if (!ok || !body) return { ok: false, parsed: {} };
  if (!body.ok && err) {
    err.classList.remove("hidden");
    err.innerHTML = body.errors.map((e) => escapeHTML(e.message)).join("<br>");
  } else if (err) {
    err.classList.add("hidden");
  }
  return { ok: body.ok, parsed: body.parsed || {} };
}

function cardHTML(d) {
  const artUrl = characterArtUrl(d.character_id, "_card");
  const dummyUrl = characterArtUrl(d.dummy_character_id, "_dummy");

  const cardClass = "card" + (artUrl ? " has-art" : "") + (dummyUrl ? " has-dummy-art" : "");
  const selectedClass = d.selected ? " is-selected" : "";
  const favClass = d.favorite ? " is-favorite" : "";
  const vars = [
    artUrl ? `--char-art-url:url('${artUrl}')` : null,
    dummyUrl ? `--dummy-art-url:url('${dummyUrl}')` : null,
  ].filter(Boolean);
  const artStyle = vars.length ? ` style="${vars.join(";")}"` : "";
  return `
    <div class="${cardClass}${selectedClass}${favClass}"${artStyle}>
      <div class="top">
        <label class="card-select" title="Send this drill to the game">
          <input type="checkbox" class="card-select-checkbox" id="select-${d.id}"${d.selected ? " checked" : ""}>
        </label>
        <button class="card-fav${d.favorite ? " on" : ""}" id="fav-${d.id}"
                aria-pressed="${d.favorite ? "true" : "false"}"
                title="${d.favorite ? "In your favorites" : "Add to favorites"}">${d.favorite ? "&#9733;" : "&#9734;"}</button>
      </div>
      <!-- Reserves the band the character's face occupies, so the title
           starts below it (2026-08-18, Jason: "Align the image to the top
           of the card and put the tags and donut at the bottom of the
           card. Still have that space above the title though. This way
           the face shows."). Collapses to nothing on a card with no art. -->
      <div class="card-art-space"></div>
      <h3>${escapeHTML(d.name)}</h3>
      <p>${linkify(d.description || "")}</p>
      ${gradeLineHTML(d)}
      ${perCharacterHTML(d)}
      <div class="card-actions">
        <button class="btn" id="edit-${d.id}">Edit</button>
        <button class="btn" id="history-${d.id}">History</button>
        <button class="btn" id="delete-${d.id}">Delete</button>
      </div>
      <div class="card-meta">
        <div class="top-tags">
          <span class="tag ${d.bucket}">${bucketLabel(d.bucket)}</span>
          ${d.is_due ? '<span class="tag due">DUE</span>' : ""}
          ${difficultyTagHTML(d.difficulty)}
        </div>
        ${donutHTML(d)}
      </div>
    </div>
  `;
}

function escapeHTML(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

const URL_PATTERN = /https?:\/\/[^\s<>"']+/g;

function linkify(text) {
  return escapeHTML(text).replace(URL_PATTERN, (url) => {
    // Trailing punctuation is far more likely to be the sentence's than
    // the URL's: "see https:
    const trimmed = url.replace(/[.,;:!?)\]]+$/, "");
    const tail = url.slice(trimmed.length);
    return `<a href="${trimmed}" target="_blank" rel="noopener noreferrer">`
         + `${trimmed}</a>${tail}`;
  });
}

function populateSelect(selectEl, options, currentValue, blankLabel) {
  selectEl.innerHTML = `<option value="">${blankLabel}</option>` +
    options.map((o) => `<option value="${o}">${o}</option>`).join("");
  selectEl.value = options.includes(currentValue) ? currentValue : "";
}

function renderChipRow(elementId, categories, selected, rerender) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = categories.map(
    (c) => `<span class="chip${selected.has(c) ? " selected" : ""}" data-cat="${c}">${c}</span>`
  ).join("");
  el.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cat = chip.dataset.cat;
      if (selected.has(cat)) selected.delete(cat);
      else selected.add(cat);
      rerender();
    });
  });
}

const GAUGE_DEFAULTS = { health: 100, drive: 6, sa: 0 };

const RECOVERY_MODES = ["refill", "fixed", "standard"];
const RECOVERY_DEFAULTS = {
  health_recovery: "refill",
  drive_recovery: "refill",
  sa_recovery: "refill",
};

const PAIR_DEFAULTS = { ...GAUGE_DEFAULTS, ...RECOVERY_DEFAULTS };

function applyGaugesFromForm(trainingSettings) {
  for (const key of Object.keys(PAIR_DEFAULTS)) {
    const isMode = key in RECOVERY_DEFAULTS;
    const value = {};
    for (const side of ["mine", "theirs"]) {
      const el = document.getElementById(`f-${key}-${side}`);
      if (!el) continue;
      const raw = el.value.trim();
      if (raw === "") continue;

      if (isMode) {
        if (RECOVERY_MODES.includes(raw) && raw !== PAIR_DEFAULTS[key]) value[side] = raw;
      } else {
        const n = Number(raw);
        if (Number.isFinite(n) && n !== PAIR_DEFAULTS[key]) value[side] = n;
      }
    }
    if (Object.keys(value).length) trainingSettings[key] = value;
    else delete trainingSettings[key];
  }

  const cpuRaw = (document.getElementById("f-cpu-level")?.value || "").trim();
  if (cpuRaw === "") delete trainingSettings.cpu_level;
  else trainingSettings.cpu_level = Number(cpuRaw);
}

function fillGaugesIntoForm(ts) {
  for (const key of Object.keys(PAIR_DEFAULTS)) {
    const value = (ts && ts[key]) || {};
    for (const side of ["mine", "theirs"]) {
      const el = document.getElementById(`f-${key}-${side}`);
      if (!el) continue;

      if (key in RECOVERY_DEFAULTS && !el.options.length) {

        el.appendChild(new Option(`${PAIR_DEFAULTS[key]} (default)`, ""));
        for (const mode of RECOVERY_MODES) {
          if (mode !== PAIR_DEFAULTS[key]) el.appendChild(new Option(mode, mode));
        }
      }
      el.value = value[side] === undefined ? "" : value[side];
    }
  }
  const cpu = document.getElementById("f-cpu-level");

  if (cpu) cpu.value = ts && ts.cpu_level !== undefined ? ts.cpu_level : "";
}

function renderTrainsChips() {
  renderChipRow("f-trains-chips", TRAINS_CATEGORIES,
                trainsSelected, renderTrainsChips);
  renderChipRow("f-trains-for-chips", TRAINS_FOR_CATEGORIES,
                trainsForSelected, renderTrainsChips);
}

function renderFixedResponseChips() {
  const el = document.getElementById("f-fixed-response-chips");
  el.innerHTML = RESPONSE_CATEGORIES.map(
    (c) => `<span class="chip${fixedResponseSelected.has(c) ? " selected" : ""}" data-cat="${c}">${c}</span>`
  ).join("");
  el.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cat = chip.dataset.cat;
      if (fixedResponseSelected.has(cat)) fixedResponseSelected.delete(cat);
      else fixedResponseSelected.add(cat);
      renderFixedResponseChips();
    });
  });
}

let attemptsTouched = false;

function attemptsSuggestion() {
  if (!slotRows.length) return null;
  if (slotRows.some((r) => r.kind !== "recording")) {
    return { value: "slot", why: "the dummy starts a reversal drill, and your attack is the setup for it" };
  }
  return { value: "action", why: "the recording loops on its own timer, so it says nothing about how many times you tried" };
}

document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("f-attempts");
  if (select) {
    select.addEventListener("change", () => {
      attemptsTouched = true;
      refreshAttemptsSuggestion();
    });
  }

  const formPanel = document.getElementById("modal-form-panel");
  if (formPanel) {
    formPanel.addEventListener("input", markFormDirty, true);
    formPanel.addEventListener("change", markFormDirty, true);
  }
});

function refreshAttemptsSuggestion() {
  const select = document.getElementById("f-attempts");
  const hint = document.getElementById("f-attempts-suggestion");
  if (!select || !hint) return;
  const s = attemptsSuggestion();
  if (!s) { hint.hidden = true; return; }

  if (!attemptsTouched) select.value = s.value;

  if (select.value === s.value) { hint.hidden = true; return; }
  const label = s.value === "action" ? "Action" : "Slot";
  hint.textContent = `Suggested: ${label} — ${s.why}.`;
  hint.hidden = false;
}

function renderSlotRows() {
  refreshAttemptsSuggestion();
  const container = document.getElementById("f-slots-container");
  const isReversalKind = (kind) => kind !== "recording";

  container.innerHTML = slotRows.map((row, i) => `
    <div class="slot-row" data-i="${i}">
      <label class="slot-kind">Type<select class="slot-kind-select">
        ${Object.entries(SLOT_KIND_LABELS).map(([k, label]) =>
          `<option value="${k}"${row.kind === k ? " selected" : ""}>${label}</option>`).join("")}
      </select></label>
      <label class="slot-index">Slot # (max ${SLOT_KIND_MAX_INDEX[row.kind]})<input type="number" min="0" max="${SLOT_KIND_MAX_INDEX[row.kind]}" class="slot-index-input" value="${row.index}"></label>
      <div class="slot-main">
        ${isReversalKind(row.kind) ? `
        <div class="slot-action">
          <label>Dummy's action<select class="slot-action-type">
            ${REVERSAL_TYPES.map((t) =>
              `<option value="${t}"${row.action.type === t ? " selected" : ""}>${REVERSAL_TYPE_LABELS[t]}</option>`).join("")}
          </select></label>
          <label>Skill<span class="slot-skill-holder">
            <input type="number" min="0" class="slot-action-skill-fallback" placeholder="skill index" value="${row.action.skillIndex ?? ""}">
          </span></label>
          <label class="slot-action-delay-label">Delay (f)<input type="number" min="0" class="slot-action-delay" value="${row.action.delay || 0}"></label>
        </div>` : `
        <div class="slot-action">
          <label>Action (recorded input -- same notation as WongScript, e.g. "236HP, [6:10f]")
            <textarea class="slot-action-notation mono" rows="2" placeholder="leave blank to use whatever's already recorded in Training Mode">${escapeHTML(row.actionText || "")}</textarea>
          </label>
          <span class="hint${row.actionError ? " slot-action-error" : ""}">${
            row.actionError || (row.pattern
              ? `🎬 ${row.pattern.length} frames -- will auto-inject + auto-play at session start`
              : "No action authored -- this slot must already have a real recording in Training Mode.")
          }</span>
          <label>Random Selection Rate<input type="number" min="1" class="slot-recording-weight" value="${row.weight || 1}"></label>
        </div>`}
        <div class="chip-row slot-chip-row"></div>
        <input type="text" class="slot-note" placeholder="note (optional)" value="${escapeHTML(row.note || "")}">
      </div>
      <button type="button" class="btn remove-slot-btn">&times;</button>
    </div>
  `).join("") || `<p class="dim" style="font-size:12.5px">No slots yet.</p>`;

  container.querySelectorAll(".slot-row").forEach((rowEl) => {
    const i = parseInt(rowEl.dataset.i, 10);
    const row = slotRows[i];

    rowEl.querySelector(".slot-kind-select").addEventListener("change", (e) => {
      row.kind = e.target.value;
      // Switching from a 10-slot Reversal kind to the 8-slot Recording
      // kind can leave an out-of-range index (e.g. index 8 or 9) --
      // clamp immediately so a stale value can't silently save.
      row.index = Math.min(row.index, SLOT_KIND_MAX_INDEX[row.kind]);
      renderSlotRows();
    });

    const chipRow = rowEl.querySelector(".slot-chip-row");
    chipRow.innerHTML = RESPONSE_CATEGORIES.map(
      (c) => `<span class="chip${row.selected.has(c) ? " selected" : ""}" data-cat="${c}">${c}</span>`
    ).join("");
    chipRow.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const cat = chip.dataset.cat;
        if (row.selected.has(cat)) row.selected.delete(cat);
        else row.selected.add(cat);
        renderSlotRows();
      });
    });

    rowEl.querySelector(".slot-index-input").addEventListener("input", (e) => {
      const raw = parseInt(e.target.value, 10) || 0;
      const clamped = Math.max(0, Math.min(raw, SLOT_KIND_MAX_INDEX[row.kind]));
      row.index = clamped;
      if (clamped !== raw) e.target.value = clamped; // reflect the clamp visually, not just internally
    });
    rowEl.querySelector(".slot-note").addEventListener("input", (e) => {
      row.note = e.target.value;
    });
    rowEl.querySelector(".remove-slot-btn").addEventListener("click", () => {
      slotRows.splice(i, 1);
      renderSlotRows();
    });

    if (isReversalKind(row.kind)) {
      rowEl.querySelector(".slot-action-type").addEventListener("change", (e) => {
        row.action.type = e.target.value;
        row.action.skillIndex = null; // a different category has a different name list
        populateSkillPicker(rowEl, row);
      });
      rowEl.querySelector(".slot-action-delay").addEventListener("input", (e) => {
        row.action.delay = parseInt(e.target.value, 10) || 0;
      });
      populateSkillPicker(rowEl, row);
    } else {
      rowEl.querySelector(".slot-recording-weight").addEventListener("input", (e) => {
        row.weight = parseInt(e.target.value, 10) || 1;
      });
      // Validated on blur (not every keystroke) -- reuses wongscript.py's
      // real notation parser server-side rather than a duplicate JS
      // implementation (2026-08-17, Jason: "It should use the same

      rowEl.querySelector(".slot-action-notation").addEventListener("blur", async (e) => {
        row.actionText = e.target.value;
        const text = row.actionText.trim();
        if (!text) {
          row.pattern = null;
          row.actionError = null;
          renderSlotRows();
          return;
        }
        const { ok, body } = await fetchJSON("/api/pattern/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (ok && body && body.pattern) {
          row.pattern = body.pattern;
          row.actionError = null;
        } else {
          row.pattern = null;
          row.actionError = (body && body.errors && body.errors[0] && body.errors[0].message) || "Could not parse this action.";
        }
        renderSlotRows();
      });
    }
  });
}

async function loadActionNotationTexts() {
  for (const row of slotRows) {
    if (row.kind === "recording" && row.pattern && row.actionText === undefined) {
      const { ok, body } = await fetchJSON("/api/pattern/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pattern: row.pattern }),
      });
      row.actionText = (ok && body && body.text) || "";
    }
  }
  renderSlotRows();
}

async function populateSkillPicker(rowEl, row) {
  const dummy = document.getElementById("f-dummy-character").value || null;
  const names = await fetchReversalSkills(row.action.type, dummy);
  const holder = rowEl.querySelector(".slot-skill-holder");
  if (!holder) return;

  if (names.length) {
    holder.innerHTML = `<select class="slot-action-skill-select">
      <option value="">(choose...)</option>
      ${names.map((name, idx) =>
        `<option value="${idx}"${row.action.skillIndex === idx ? " selected" : ""}>${escapeHTML(name)}</option>`).join("")}
    </select>`;
    holder.querySelector("select").addEventListener("change", (e) => {
      row.action.skillIndex = e.target.value === "" ? null : parseInt(e.target.value, 10);
    });
  } else {
    holder.innerHTML = `<input type="number" min="0" class="slot-action-skill-fallback" placeholder="skill index (raw -- set dummy: character above for names)" value="${row.action.skillIndex ?? ""}">`;
    holder.querySelector("input").addEventListener("input", (e) => {
      row.action.skillIndex = e.target.value === "" ? null : (parseInt(e.target.value, 10) || 0);
    });
  }
}

function addSlotRow() {
  const defaultKind = "reversal";
  const nextIndex = slotRows.length ? Math.max(...slotRows.map((r) => r.index)) + 1 : 0;
  slotRows.push({
    index: Math.min(nextIndex, SLOT_KIND_MAX_INDEX[defaultKind]),
    kind: defaultKind,
    action: { type: "COMMON", skillIndex: null, delay: 0 },
    weight: 1,
    pattern: null,
    actionText: "",
    actionError: null,
    selected: new Set(),
    note: "",
  });
  renderSlotRows();
}

function resetModalFields() {
  document.getElementById("f-name").value = "";
  document.getElementById("f-description").value = "";
  document.getElementById("f-response-window").value = "";
  fillGaugesIntoForm(null);
  document.getElementById("f-attempts").value = "slot";
  attemptsTouched = false;

  formDirtySinceSync = false;
  document.getElementById("f-game-speed").value = "";
  document.getElementById("f-reps").value = "";
  document.getElementById("f-advanced-slots").value = "";
  document.getElementById("f-wong").value = "";
  document.getElementById("f-wong-dummy").value = "";
  hideWongErrors();
  wongLoadedForCurrentDrill = false;
  fixedResponseSelected = new Set();
  trainsSelected = new Set();
  trainsForSelected = new Set();
  fixedComboText = null;
  slotRows = [];
  populateSelect(document.getElementById("f-position"), POSITION_PRESETS, "", "(keep as captured)");
  populateSelect(document.getElementById("f-block-setting"), BLOCK_SETTINGS, "", "(default: block after first hit)");
  populateSelect(document.getElementById("f-repeat-replay"), Object.keys(REPEAT_REPLAY_LABELS), "", "(keep as captured)");
  populateSelect(document.getElementById("f-character"), CHARACTER_IDS, "", "(none)");
  populateSelect(document.getElementById("f-dummy-character"), CHARACTER_IDS, "", "(none)");
  renderFixedResponseChips();
  renderTrainsChips();
  renderSlotRows();
  hideFormError();
  selectFormTab();
}

function openCreateModal() {
  editingDrillId = null;
  editingDrillOriginal = null;
  document.getElementById("modal-title").textContent = "New Drill";
  resetModalFields();
  document.getElementById("modal-backdrop").classList.remove("hidden");
}

function openEditModal(d) {
  editingDrillId = d.id;
  editingDrillOriginal = d;
  document.getElementById("modal-title").textContent = `Edit: ${d.name}`;
  resetModalFields();

  document.getElementById("f-name").value = d.name || "";
  document.getElementById("f-description").value = d.description || "";
  document.getElementById("f-response-window").value = d.response_window_frames ?? "";
  document.getElementById("f-attempts").value = d.attempts === "action" ? "action" : "slot";

  attemptsTouched = true;
  document.getElementById("f-game-speed").value = d.game_speed ?? "";
  document.getElementById("f-reps").value = d.reps ?? "";
  document.getElementById("f-character").value = d.character_id || "";
  document.getElementById("f-dummy-character").value = d.dummy_character_id || "";

  const ts = d.training_settings || {};

  if (typeof ts.position === "string") {
    document.getElementById("f-position").value = POSITION_PRESETS.includes(ts.position) ? ts.position : "";
  }
  if (ts.block_setting) document.getElementById("f-block-setting").value = ts.block_setting;

  fillGaugesIntoForm(ts);
  fixedResponseSelected = toResponseSet(d.fixed_expected_response);
  fillAdvancedCriteria(d);
  trainsSelected = new Set(d.trains || []);
  trainsForSelected = new Set(d.trains_for || []);
  fixedComboText = d.fixed_expected_combo || null;
  renderFixedResponseChips();
  renderTrainsChips();

  slotRows = buildSlotRowsFor(d, ts);
  renderSlotRows();
  loadActionNotationTexts();

  if (REPEAT_REPLAY_LABELS[ts.repeat_replay]) {
    document.getElementById("f-repeat-replay").value = ts.repeat_replay;
  }

  const advanced = {};

  if (ts.recording_slots !== undefined) {
    advanced.recording_slots = ts.recording_slots.map((e) => {
      const { pattern, ...rest } = normalizeRecordingSlotEntry(e);
      return rest;
    });
  }
  if (ts.reversal_slots !== undefined) advanced.reversal_slots = ts.reversal_slots;
  if (ts.block_reversal_slots !== undefined) advanced.block_reversal_slots = ts.block_reversal_slots;
  if (ts.damage_reversal_slots !== undefined) advanced.damage_reversal_slots = ts.damage_reversal_slots;
  document.getElementById("f-advanced-slots").value = Object.keys(advanced).length
    ? JSON.stringify(advanced, null, 2) : "";

  document.getElementById("modal-backdrop").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
}

function showFormError(msg) {
  const el = document.getElementById("form-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}
function hideFormError() {
  document.getElementById("form-error").classList.add("hidden");
}

function buildSlotListsFromRows(rows, base) {
  const byKind = { reversal: [], block_reversal: [], damage_reversal: [], recording: [] };
  rows.forEach((row) => byKind[row.kind].push(row));

  const result = {
    recording_slots: undefined, reversal_slots: undefined,
    block_reversal_slots: undefined, damage_reversal_slots: undefined,
  };
  if (byKind.recording.length) {

    result.recording_slots = byKind.recording.slice().sort((a, b) => a.index - b.index).map((row) => ({
      index: row.index,
      weight: row.weight || 1,
      pattern: row.pattern || null,
      action_text: (row.pattern && row.actionText && row.actionText.trim()) || null,
    }));
  }
  ["reversal", "block_reversal", "damage_reversal"].forEach((kind) => {
    if (!byKind[kind].length) return;
    const tsKey = SLOT_KIND_TO_TS_KEY[kind];
    const existing = base[tsKey] || [];
    result[tsKey] = byKind[kind].slice().sort((a, b) => a.index - b.index).map((row) => {

      if (row.action && row.action.skillIndex !== null && row.action.skillIndex !== undefined) {
        return {
          index: row.index,
          type: REVERSAL_TYPE_TO_INT[row.action.type],
          skill_index: row.action.skillIndex,
          delay: row.action.delay || 0,
        };
      }

      return existing.find((c) => c.index === row.index) || { index: row.index };
    });
  });
  return result;
}

async function submitModal() {

  const wongTabActive = !document.getElementById("modal-wong-panel").classList.contains("hidden");
  if (wongTabActive) {
    const parsedOk = await parseWongScriptIntoForm();
    if (!parsedOk) return;
  }

  const payload = await buildDrillPayloadFromForm({ wongTabActive });
  if (!payload) return;

  const url = editingDrillId ? `/api/drills/${encodeURIComponent(editingDrillId)}` : "/api/drills";
  const method = editingDrillId ? "PATCH" : "POST";
  const { ok, body } = await fetchJSON(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!ok) return showFormError((body && body.error) || "Save failed.");

  closeModal();
  refreshDrills();
  refreshOverview();
}

async function buildDrillPayloadFromForm({ wongTabActive }) {
  const name = document.getElementById("f-name").value.trim();
  if (!name) { showFormError("Name is required."); return null; }

  for (const row of slotRows) {
    if (row.index > SLOT_KIND_MAX_INDEX[row.kind]) {
      return showFormError(`${SLOT_KIND_LABELS[row.kind]} only has slots 0-${SLOT_KIND_MAX_INDEX[row.kind]} in-game -- slot ${row.index} isn't reachable.`);
    }
  }

  const advancedRaw = document.getElementById("f-advanced-slots").value.trim();
  let advancedSlots = {};
  if (advancedRaw) {
    try {
      advancedSlots = JSON.parse(advancedRaw);
    } catch (e) {
      return showFormError(`Advanced slot config: invalid JSON (${e.message})`);
    }
  }

  const baseTrainingSettings = { ...((editingDrillOriginal && editingDrillOriginal.training_settings) || {}), ...advancedSlots };
  const slotDerived = buildSlotListsFromRows(slotRows, baseTrainingSettings);
  const trainingSettings = { ...baseTrainingSettings, ...slotDerived };
  const position = document.getElementById("f-position").value;
  if (position) trainingSettings.position = position;
  const blockSetting = document.getElementById("f-block-setting").value;
  if (blockSetting) trainingSettings.block_setting = blockSetting;
  const repeatReplay = document.getElementById("f-repeat-replay").value;
  if (repeatReplay) trainingSettings.repeat_replay = repeatReplay;
  applyGaugesFromForm(trainingSettings);

  const slotOutcomes = {};
  slotRows.forEach((row) => {
    const resp = slotOutcomeFor(row);
    if (resp !== null) {
      slotOutcomes[String(row.index)] = row.note ? { expected_response: resp, note: row.note } : { expected_response: resp };
    }
  });

  const adv = await validateAdvancedCriteria();
  if (!adv.ok) {
    const box = document.getElementById("f-advanced-criteria");
    if (box) box.open = true;
    return;
  }
  const surviveRaw = (document.getElementById("f-survive")?.value || "").trim();

  const rwRaw = document.getElementById("f-response-window").value.trim();
  const gsRaw = document.getElementById("f-game-speed").value.trim();
  const repsRaw = document.getElementById("f-reps").value.trim();

  const payload = {
    name,
    description: document.getElementById("f-description").value,
    training_settings: trainingSettings,
    slot_outcomes: Object.keys(slotOutcomes).length ? slotOutcomes : null,

    fixed_expected_response: adv.parsed.fixed_expected_response
      ?? fromResponseSet(fixedResponseSelected),
    against_criteria: adv.parsed.against ?? null,
    expected_setup: adv.parsed.setup ?? null,
    survive_seconds: surviveRaw === "" ? null : parseInt(surviveRaw, 10),
    trains: trainsSelected.size > 0 ? [...trainsSelected] : null,
    trains_for: trainsForSelected.size > 0 ? [...trainsForSelected] : null,
    response_window_frames: rwRaw === "" ? null : parseInt(rwRaw, 10),
    attempts: document.getElementById("f-attempts").value,
    game_speed: gsRaw === "" ? null : parseInt(gsRaw, 10),
    reps: repsRaw === "" ? null : parseInt(repsRaw, 10),
    character_id: document.getElementById("f-character").value || null,
    dummy_character_id: document.getElementById("f-dummy-character").value || null,

    wongscript_text: wongTabActive ? document.getElementById("f-wong").value : null,
  };

  if (wongTabActive) payload.fixed_expected_combo = fixedComboText;

  return payload;
}

function openDeleteModal(id, name) {
  deleteTargetId = id;
  deleteTargetName = name;
  document.getElementById("delete-name").textContent = name;
  document.getElementById("delete-confirm-input").value = "";
  document.getElementById("delete-confirm-btn").disabled = true;
  document.getElementById("delete-backdrop").classList.remove("hidden");
}

function closeDeleteModal() {
  document.getElementById("delete-backdrop").classList.add("hidden");
  deleteTargetId = null;
}

async function confirmDelete() {
  if (!deleteTargetId) return;
  await fetchJSON(`/api/drills/${encodeURIComponent(deleteTargetId)}`, { method: "DELETE" });
  closeDeleteModal();
  refreshDrills();
  refreshOverview();
}

function renderDrillTrend(history) {
  if (history.length < 2) return "";
  const bars = history.map((h) => {
    const pct = h.attempts ? Math.round(((h.successes || 0) / h.attempts) * 100) : 0;

    const cls = pct >= 80 ? "good" : pct >= 50 ? "mid" : "poor";
    return `<i class="tb-${cls}" style="height:${Math.max(pct, 3)}%" title="${escapeHTML(h.date || "")}: ${pct}%"></i>`;
  }).join("");
  return `<div class="drill-trend"><div class="tb-bars">${bars}</div>
            <div class="tb-axis"><span>oldest</span><span>success rate per session</span><span>newest</span></div>
          </div>`;
}

async function openHistoryModal(id) {
  const { ok, body: d } = await fetchJSON(`/api/drills/${encodeURIComponent(id)}`);
  if (!ok) return;

  document.getElementById("history-title").textContent = `History: ${d.name}`;

  const history = d.history || [];

  const attempts = history.reduce((a, h) => a + (h.attempts || 0), 0);
  const successes = history.reduce((a, h) => a + (h.successes || 0), 0);
  const rate = attempts ? Math.round((successes / attempts) * 100) : null;
  const last = history.length ? history[history.length - 1].date : null;

  document.getElementById("history-summary").innerHTML = `
    <div class="live-stat"><div class="label">${t("Success")}</div><div class="value">${rate == null ? "&mdash;" : rate + "%"}</div></div>
    <div class="live-stat"><div class="label">${t("Sessions")}</div><div class="value">${history.length}</div></div>
    <div class="live-stat"><div class="label">${t("Streak")}</div><div class="value">${d.streak ?? 0}</div></div>
    <div class="live-stat"><div class="label">${t("Ease")}</div><div class="value">${(d.ease_factor ?? 0).toFixed ? d.ease_factor.toFixed(2) : d.ease_factor}</div></div>
    <div class="live-stat"><div class="label">${t("Interval")}</div><div class="value">${d.interval_days ?? "-"}d</div></div>
    <div class="live-stat"><div class="label">${t("Last played")}</div><div class="value" style="font-size:13px">${last ? escapeHTML(last) : "never"}</div></div>
    <div class="live-stat"><div class="label">${t("Next review")}</div><div class="value" style="font-size:13px">${d.next_review ? d.next_review.slice(0, 10) : "-"}</div></div>
  `;

  document.getElementById("history-trend").innerHTML = renderDrillTrend(history);

  const rows = history.length
    ? [...history].reverse().map((h) => {

        const vs = h.dummy_character_id
          ? `${characterLabel(h.character_id)} vs ${characterLabel(h.dummy_character_id)}`
          : `<span class="dim">not recorded</span>`;
        const pct = h.attempts ? Math.round(((h.successes || 0) / h.attempts) * 100) + "%" : "-";
        return `
        <tr>
          <td>${escapeHTML(h.date || "-")}</td>
          <td>${h.successes ?? "-"}/${h.attempts ?? "-"} <span class="dim">${pct}</span></td>
          <td>${vs}</td>
          <td><span class="grade-pill ${GRADE_CLASS[h.final_grade] || ""}">${GRADE_LABELS[h.final_grade] || "-"}</span></td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="4" class="dim">No sessions yet.</td></tr>`;
  document.getElementById("history-rows").innerHTML = rows;

  document.getElementById("history-backdrop").classList.remove("hidden");
}

function closeHistoryModal() {
  document.getElementById("history-backdrop").classList.add("hidden");
}

async function showFormTab() {
  if (!document.getElementById("modal-wong-panel").classList.contains("hidden")) {
    if (!(await parseWongScriptIntoForm())) return;
  }
  selectFormTab();
}

function selectFormTab() {
  document.getElementById("tab-form-btn").classList.add("tab-active");
  document.getElementById("tab-wong-btn").classList.remove("tab-active");
  document.getElementById("modal-form-panel").classList.remove("hidden");
  document.getElementById("modal-wong-panel").classList.add("hidden");
}

let formDirtySinceSync = false;

function markFormDirty() { formDirtySinceSync = true; }

async function syncFormIntoWong() {
  const payload = await buildDrillPayloadFromForm({ wongTabActive: false });
  if (!payload) return false;
  const dummy = document.getElementById("f-wong-dummy").value.trim();
  const { ok, body } = await fetchJSON("/api/wongscript/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drill: payload, dummy: dummy || null }),
  });
  if (!ok || !body || body.error || typeof body.wong !== "string") {
    showWongErrors([{ line: 0, message: (body && body.error) || "Could not render this drill as WongScript." }]);
    return false;
  }
  document.getElementById("f-wong").value = body.wong;
  formDirtySinceSync = false;
  return true;
}

let wongLoadedForCurrentDrill = false;

async function showWongTab() {
  hideWongErrors();
  if (!wongLoadedForCurrentDrill) {

    wongLoadedForCurrentDrill = true;
    if (editingDrillId) {
      await loadWongScriptText();
    } else if (!(await syncFormIntoWong())) {

      wongLoadedForCurrentDrill = false;
      return;
    }
  } else if (formDirtySinceSync || !document.getElementById("f-wong").value.trim()) {

    if (!(await syncFormIntoWong())) return;
  }
  document.getElementById("tab-wong-btn").classList.add("tab-active");
  document.getElementById("tab-form-btn").classList.remove("tab-active");
  document.getElementById("modal-wong-panel").classList.remove("hidden");
  document.getElementById("modal-form-panel").classList.add("hidden");
}

async function loadWongScriptText() {
  hideWongErrors();
  if (!editingDrillId) return;
  const dummy = document.getElementById("f-wong-dummy").value.trim();
  const url = `/api/drills/${encodeURIComponent(editingDrillId)}/wong` + (dummy ? `?dummy=${encodeURIComponent(dummy)}` : "");
  const { ok, body } = await fetchJSON(url);
  if (!ok || !body) return showWongErrors([{ line: 0, message: "Could not load this drill as WongScript." }]);
  document.getElementById("f-wong").value = body.wong;
}

function showWongErrors(errors) {
  const el = document.getElementById("wong-errors");
  el.innerHTML = errors.map((e) => `line ${e.line}: ${escapeHTML(e.message)}`).join("<br>");
  el.classList.remove("hidden");
}
function hideWongErrors() {
  document.getElementById("wong-errors").classList.add("hidden");
}

function fillFormFromParsedDrill(drill) {
  document.getElementById("f-name").value = drill.name || "";
  document.getElementById("f-description").value = drill.description || "";
  document.getElementById("f-response-window").value = drill.response_window_frames ?? "";
  document.getElementById("f-attempts").value = drill.attempts === "action" ? "action" : "slot";
  attemptsTouched = true;
  document.getElementById("f-game-speed").value = drill.game_speed ?? "";
  document.getElementById("f-reps").value = drill.reps ?? "";
  document.getElementById("f-character").value = drill.character_id || "";
  document.getElementById("f-dummy-character").value = drill.dummy_character_id || "";

  const ts = drill.training_settings || {};
  if (typeof ts.position === "string") {
    document.getElementById("f-position").value = POSITION_PRESETS.includes(ts.position) ? ts.position : "";
  }
  if (ts.block_setting) document.getElementById("f-block-setting").value = ts.block_setting;

  fillGaugesIntoForm(ts);
  fixedResponseSelected = toResponseSet(drill.fixed_expected_response);
  fillAdvancedCriteria(drill);
  trainsSelected = new Set(drill.trains || []);
  trainsForSelected = new Set(drill.trains_for || []);
  fixedComboText = drill.fixed_expected_combo || null;
  renderFixedResponseChips();
  renderTrainsChips();

  slotRows = buildSlotRowsFor(drill, ts);
  renderSlotRows();
  loadActionNotationTexts();

  if (REPEAT_REPLAY_LABELS[ts.repeat_replay]) {
    document.getElementById("f-repeat-replay").value = ts.repeat_replay;
  }

  const advanced = {};
  if (ts.recording_slots !== undefined) {
    advanced.recording_slots = ts.recording_slots.map((e) => {
      const { pattern, ...rest } = normalizeRecordingSlotEntry(e);
      return rest;
    });
  }
  if (ts.reversal_slots !== undefined) advanced.reversal_slots = ts.reversal_slots;
  if (ts.block_reversal_slots !== undefined) advanced.block_reversal_slots = ts.block_reversal_slots;
  if (ts.damage_reversal_slots !== undefined) advanced.damage_reversal_slots = ts.damage_reversal_slots;
  document.getElementById("f-advanced-slots").value = Object.keys(advanced).length
    ? JSON.stringify(advanced, null, 2) : "";
}

async function parseWongScriptIntoForm() {
  hideWongErrors();
  const text = document.getElementById("f-wong").value;
  const { ok, body } = await fetchJSON("/api/wongscript/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!ok || !body) {
    showWongErrors([{ line: 0, message: "Parse request failed." }]);
    return false;
  }
  if (body.errors && body.errors.length) {
    showWongErrors(body.errors);
    return false;
  }
  fillFormFromParsedDrill(body.drill);
  return true;
}

function openImportModal() {
  document.getElementById("f-import-wong").value = "";
  document.getElementById("f-import-file").value = "";
  document.getElementById("import-file-name").textContent = "";
  const append = document.querySelector('input[name="import-mode"][value="append"]');
  if (append) append.checked = true;
  document.getElementById("import-result").classList.add("hidden");
  document.getElementById("import-backdrop").classList.remove("hidden");
}

function loadImportFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    document.getElementById("f-import-wong").value = reader.result || "";
    document.getElementById("import-file-name").textContent = file.name;
  };
  reader.onerror = () => {
    const el = document.getElementById("import-result");
    el.classList.remove("hidden");
    el.textContent = "Could not read that file.";
  };
  reader.readAsText(file);
}
function closeImportModal() {
  document.getElementById("import-backdrop").classList.add("hidden");
}

async function submitImport() {
  const text = document.getElementById("f-import-wong").value;
  const checked = document.querySelector('input[name="import-mode"]:checked');
  const mode = checked ? checked.value : "append";
  const { ok, body } = await fetchJSON("/api/wongscript/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, mode }),
  });
  const el = document.getElementById("import-result");
  el.classList.remove("hidden");
  if (!ok || !body) {
    el.textContent = (body && body.error) || "Import request failed.";
    return;
  }

  const parts = [];
  if (body.imported.length) parts.push(`Added ${body.imported.length} new drill(s).`);
  if (body.updated.length) parts.push(`Replaced ${body.updated.length} you already had.`);
  if (body.skipped.length) parts.push(`Left ${body.skipped.length} you already had untouched.`);
  if (!parts.length) parts.push("Nothing to import.");
  if (body.errors.length) {
    parts.push(`${body.errors.length} skipped due to errors:`);
    body.errors.forEach((e) => parts.push(`  line ${e.line}: ${e.message}`));
  }
  el.innerHTML = parts.map(escapeHTML).join("<br>");
  if (body.imported.length || body.updated.length) {
    refreshDrills();
    refreshOverview();
  }
}

document.addEventListener("DOMContentLoaded", () => {

  loadResponseCategories();

  if (document.getElementById("new-drill-btn")) {
    document.getElementById("new-drill-btn").addEventListener("click", openCreateModal);

  document.querySelectorAll(".modal-backdrop").forEach((overlay) => {
    overlay.addEventListener("mousedown", (e) => {
      if (e.target === overlay) overlay.classList.add("close-armed");
    });
    overlay.addEventListener("mouseup", (e) => {
      const armed = overlay.classList.contains("close-armed");
      overlay.classList.remove("close-armed");
      if (armed && e.target === overlay) overlay.classList.add("hidden");
    });
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal-cancel").addEventListener("click", closeModal);
    document.getElementById("modal-save").addEventListener("click", submitModal);
    document.getElementById("add-slot-btn").addEventListener("click", addSlotRow);

    document.getElementById("f-dummy-character").addEventListener("change", () => renderSlotRows());
    document.getElementById("tab-form-btn").addEventListener("click", showFormTab);
    document.getElementById("tab-wong-btn").addEventListener("click", showWongTab);

    document.getElementById("f-wong-dummy").addEventListener("change", loadWongScriptText);

    document.getElementById("import-wong-btn").addEventListener("click", openImportModal);
    document.getElementById("import-close").addEventListener("click", closeImportModal);
    document.getElementById("import-cancel-btn").addEventListener("click", closeImportModal);
    document.getElementById("import-submit-btn").addEventListener("click", submitImport);
    document.getElementById("f-import-file").addEventListener("change", (e) => {
      loadImportFile(e.target.files && e.target.files[0]);
    });

    document.getElementById("delete-cancel-btn").addEventListener("click", closeDeleteModal);
    document.getElementById("delete-confirm-btn").addEventListener("click", confirmDelete);
    document.getElementById("delete-confirm-input").addEventListener("input", (e) => {
      document.getElementById("delete-confirm-btn").disabled = e.target.value !== deleteTargetName;
    });

    document.getElementById("history-close").addEventListener("click", closeHistoryModal);
    document.getElementById("history-close-btn").addEventListener("click", closeHistoryModal);

    ["filter-type", "filter-character", "filter-dummy"].forEach((id) => {
      document.getElementById(id).addEventListener("change", () => {
        readDrillFilterInputs();
        refreshDrills();
      });
    });
    document.getElementById("filter-clear-btn").addEventListener("click", clearDrillFilters);

    const search = document.getElementById("drill-search");
    if (search) {
      let timer = null;
      search.addEventListener("input", () => {
        clearTimeout(timer);

        timer = setTimeout(() => {
          drillSearchText = search.value.trim();
          refreshDrills();
        }, 200);
      });
      search.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { search.value = ""; drillSearchText = ""; refreshDrills(); }
      });
    }
    const helpBtn = document.getElementById("drill-search-help-btn");
    if (helpBtn) {
      helpBtn.addEventListener("click", () =>
        document.getElementById("drill-search-help").classList.toggle("hidden"));
    }
    const moreBtn = document.getElementById("drills-more-btn");
    if (moreBtn) moreBtn.addEventListener("click", () => refreshDrills({ append: true }));

    document.getElementById("select-all-shown-btn").addEventListener("click", () => setSelectionForShown(true));
    document.getElementById("clear-selection-btn").addEventListener("click", () => setSelectionForShown(false));
  }

  if (document.getElementById("hz-charselect")) {
    loadMatchup();
    buildCharacterSelect();
    const follow = document.getElementById("hz-follow-game");
    if (follow) {
      follow.checked = followGame;
      follow.addEventListener("change", (e) => {
        followGame = e.target.checked;
        saveMatchup();
      });
    }
  }

  document.querySelectorAll(".period-toggle").forEach((toggle) => {
    const chart = toggle.dataset.chart;
    toggle.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        toggle.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        periodState[chart] = btn.dataset.period;
        if (chart === "reviews") renderReviewsChart();
        if (chart === "added") renderAddedChart();
      });
    });
  });
  if (document.getElementById("calendar-prev-year")) {
    document.getElementById("calendar-prev-year").addEventListener("click", () => {
      calendarYear -= 1;
      renderCalendar();
    });
    document.getElementById("calendar-next-year").addEventListener("click", () => {
      calendarYear += 1;
      renderCalendar();
    });
  }

  function refreshStatsPanels() {
    refreshOverview();
    refreshHitZones();
    refreshToday();
    refreshForecast();
    refreshReviews();
    refreshIntervalsAndEase();
    refreshRetention();
    refreshHourly();
    refreshAnswerButtons();
    refreshAdded();
  }

  document.querySelectorAll(".hz-dir-btn").forEach((btn) => {
    btn.classList.toggle("is-on", btn.dataset.dir === hitZoneDirection);
    btn.addEventListener("click", () => {
      if (btn.dataset.dir === hitZoneDirection) return;
      hitZoneDirection = btn.dataset.dir;
      localStorage.setItem("bd.hitzones.direction", hitZoneDirection);
      document.querySelectorAll(".hz-dir-btn").forEach((b) =>
        b.classList.toggle("is-on", b.dataset.dir === hitZoneDirection));
      refreshHitZones();
    });
  });

  const dupToggle = document.getElementById("duplicates-toggle");
  if (dupToggle) {
    refreshDuplicatesSummary();
    dupToggle.addEventListener("click", () => {
      const body = document.getElementById("duplicates-body");
      const opening = body.classList.contains("hidden");
      body.classList.toggle("hidden", !opening);
      dupToggle.textContent = opening ? "Hide" : "Show";
      if (opening && !duplicatesLoaded) { duplicatesLoaded = true; refreshDuplicates(); }
    });
  }

  const deckPicker = document.getElementById("stats-character");
  if (deckPicker) {

    deckPicker.innerHTML = ['<option value="all">All characters</option>']
      .concat(
        [...CHARACTER_IDS]
          .sort()
          .map((id) => `<option value="${id}">${characterLabel(id)}</option>`)
      )
      .join("");
    deckPicker.value = statsCharacter;
    deckPicker.addEventListener("change", () => {
      statsCharacter = deckPicker.value;
      localStorage.setItem(STATS_CHARACTER_KEY, statsCharacter);
      refreshStatsPanels();
    });
  }

  const dummyPicker = document.getElementById("stats-dummy");
  if (dummyPicker) {

    dummyPicker.innerHTML = ['<option value="all">Any opponent</option>']
      .concat(
        [...CHARACTER_IDS]
          .sort()
          .map((id) => `<option value="${id}">${characterLabel(id)}</option>`)
      )
      .join("");
    dummyPicker.value = statsDummy;
    dummyPicker.addEventListener("change", () => {
      statsDummy = dummyPicker.value;
      localStorage.setItem(STATS_DUMMY_KEY, statsDummy);
      refreshStatsPanels();
    });
  }

  refreshOverview();
  refreshDrills();
  refreshLive();
  refreshHitZones();
  refreshToday();
  refreshForecast();
  refreshReviews();
  refreshIntervalsAndEase();
  refreshRetention();
  refreshHourly();
  refreshAnswerButtons();
  refreshAdded();
  setInterval(refreshLive, 1000);
  setInterval(refreshOverview, 5000);
  setInterval(refreshHitZones, 5000);
});

let duplicatesLoaded = false;

async function refreshDuplicates() {
  const body = document.getElementById("duplicates-body");
  if (!body) return;
  body.innerHTML = `<p class="dim">Looking&hellip;</p>`;
  const { ok, body: data } = await fetchJSON("/api/duplicates");
  if (!ok) {
    body.innerHTML = `<p class="form-error">${escapeHTML(data?.error || "could not load")}</p>`;
    return;
  }
  const groups = data.groups || [];
  if (!groups.length) {
    body.innerHTML = `<p class="dim">No drill shares a character and combo with another.</p>`;
    return;
  }
  body.innerHTML = groups.map(dupGroupHTML).join("");
}

function dupDrillHTML(d, keep) {
  const marks = [
    d.sessions ? `${d.sessions} session${d.sessions === 1 ? "" : "s"}` : "no history",
    d.imported ? "imported" : "hand-authored",
    d.difficulty || null,
  ].filter(Boolean);
  return `
    <div class="dup-drill${keep ? " dup-keep" : ""}">
      <div class="dup-drill-name">${keep ? "KEEP " : ""}${escapeHTML(d.name || d.id)}</div>
      <div class="dim mono" style="font-size:11px">${escapeHTML(d.id)}</div>
      <div class="dim" style="font-size:12px">${marks.map(escapeHTML).join(" &middot; ")}</div>
    </div>`;
}

function dupGroupHTML(g) {

  const risk = g.risk
    ? `<span class="dup-risk">holds practice history &mdash; deleting the wrong one loses it</span>`
    : "";
  return `
    <div class="dup-group">
      <div class="dup-head">
        <span class="mono">${escapeHTML(g.character_id || "no character")}</span>
        <span class="dim">${escapeHTML(g.combo || "")}</span>
        ${risk}
      </div>
      <div class="dim" style="font-size:12px; margin-bottom:6px">${escapeHTML(g.reason)}</div>
      ${dupDrillHTML(g.keep, true)}
      ${(g.others || []).map((d) => dupDrillHTML(d, false)).join("")}
    </div>`;
}

async function refreshDuplicatesSummary() {
  const el = document.getElementById("duplicates-summary");
  if (!el) return;
  const { ok, body } = await fetchJSON("/api/duplicates");
  if (!ok) return;
  const s = body.summary || {};
  el.textContent = s.groups
    ? `${s.groups} groups, ${s.drills} drills` +
      (s.with_history ? ` -- ${s.with_history} hold practice history` : "")
    : "none found";
}
