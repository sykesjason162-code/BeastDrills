const STORE_KEY = "bd.profile.character";
let selected = localStorage.getItem(STORE_KEY) || "jp";
let drills = [];
let hitZones = {};

async function getJSON(url) {
  try {
    const r = await fetch(url);
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

const drillsFor = (id) =>
  drills.flatMap((d) => {
    if (d.character_id === id) return [d];
    if (d.character_id) return [];
    const progress = (d.character_progress || {})[id];
    return progress ? [{ ...d, ...progress }] : [];
  });

function summarise(list) {
  const sum = (k) => list.reduce((a, d) => a + (d[k] || 0), 0);
  const attempts = sum("total_attempts");
  const successes = sum("total_successes");
  const graded = list.filter((d) => d.average_grade);
  return {
    drills: list.length,
    due: list.filter((d) => d.is_due).length,
    sessions: sum("total_sessions"),
    attempts,
    successes,
    rate: attempts ? Math.round((successes / attempts) * 100) : null,
    avgGrade: graded.length
      ? (graded.reduce((a, d) => a + d.average_grade, 0) / graded.length).toFixed(1)
      : null,
    bestStreak: list.reduce((a, d) => Math.max(a, d.streak || 0), 0),
    buckets: list.reduce((acc, d) => {
      const b = d.bucket || "new";
      acc[b] = (acc[b] || 0) + 1;
      return acc;
    }, {}),
  };
}

function zonesFor(id) {
  const entry = hitZones[id];
  if (!entry || !entry.counts) return null;
  const c = entry.counts;
  const total = (c.high || 0) + (c.mid || 0) + (c.low || 0);
  return total ? { ...c, total } : null;
}

function statRows(rows) {
  return rows.map(([k, v]) =>
    `<div class="pf-stat"><span>${k}</span><b>${v == null ? "&mdash;" : v}</b></div>`).join("");
}

function renderHero(id, s) {
  const el = document.getElementById("pf-hero");
  el.innerHTML = `
    <div class="pf-hero-art">
      <img src="/static/profile_characters/${id}.png" alt="${characterLabel(id)}"
           onerror="this.style.display='none'">
    </div>
    <div class="pf-hero-info">
      <div class="pf-hero-role">Selected Character</div>
      <div class="pf-hero-name">${characterLabel(id)}</div>
      <div class="pf-hero-rows">
        ${statRows([
          ["Drills", s.drills],
          ["Due now", s.due],
          ["Sessions", s.sessions],
          ["Success rate", s.rate == null ? null : `${s.rate}%`],
          ["Average grade", s.avgGrade],
          ["Best streak", s.bestStreak],
        ])}
      </div>
    </div>`;
}

function renderDonut(s) {
  const el = document.getElementById("pf-donut");
  const order = [
    ["new", "var(--todo)"],
    ["learning", "var(--prog)"],
    ["review_young", "var(--cyan)"],
    ["review_mature", "var(--done)"],
    ["review", "var(--done)"],
  ];
  const parts = order
    .map(([k, c]) => [k, s.buckets[k] || 0, c])
    .filter(([, n]) => n > 0);
  const total = parts.reduce((a, [, n]) => a + n, 0);

  if (!total) {
    el.innerHTML = `<p class="dim">No drills for this character yet.</p>`;
    return;
  }

  const R = 52, C = 2 * Math.PI * R;
  let offset = 0;
  const rings = parts.map(([, n, colour]) => {
    const len = (n / total) * C;
    const seg = `<circle cx="70" cy="70" r="${R}" fill="none" stroke="${colour}"
      stroke-width="16" stroke-dasharray="${len} ${C - len}"
      stroke-dashoffset="${-offset}" transform="rotate(-90 70 70)"></circle>`;
    offset += len;
    return seg;
  }).join("");

  el.innerHTML = `
    <svg viewBox="0 0 140 140" class="pf-donut-svg" role="img"
         aria-label="Drill buckets for ${characterLabel(selected)}">
      <circle cx="70" cy="70" r="${R}" fill="none" stroke="var(--inset)" stroke-width="16"></circle>
      ${rings}
      <text x="70" y="76" text-anchor="middle" class="pf-donut-total">${total}</text>
    </svg>
    <div class="pf-legend">
      ${parts.map(([k, n, c]) =>
        `<div class="pf-legend-row"><span class="pf-dot" style="background:${c}"></span>
           <span>${bucketLabel(k)}</span><b>${n}</b></div>`).join("")}
    </div>`;
}

function renderZones(id) {
  const el = document.getElementById("pf-zones");
  const z = shared ? sharedZones(id) : zonesFor(id);
  if (!z) {
    el.innerHTML = `<p class="dim">No hits recorded for ${characterLabel(id)} yet.</p>`;
    return;
  }
  el.innerHTML = ["high", "mid", "low"].map((k) => {
    const pct = Math.round(((z[k] || 0) / z.total) * 100);
    return `
      <div class="pf-zone">
        <div class="pf-zone-head"><span>${k.toUpperCase()}</span>
          <b>${pct}%</b> <span class="dim">(${z[k] || 0})</span></div>
        <div class="pf-zone-bar"><i style="width:${pct}%"></i></div>
      </div>`;
  }).join("") + `<div class="pf-zone-total"><b>${z.total}</b> hits taken</div>`;
}

function sharedZones(id) {
  const c = shared && shared.characters && shared.characters[id]
    ? shared.characters[id].hit_zones : null;
  if (!c) return null;
  const total = (c.high || 0) + (c.mid || 0) + (c.low || 0);
  return total ? { ...c, total } : null;
}

function renderTop(id) {

  if (shared) {
    document.getElementById("pf-drills").innerHTML =
      `<p class="dim">A shared profile carries totals only, not individual
       drills.</p>`;
    return;
  }

  const el = document.getElementById("pf-drills");
  const list = drillsFor(id).slice().sort((a, b) => (a.streak || 0) - (b.streak || 0)).slice(0, 8);
  if (!list.length) {
    el.innerHTML = `<p class="dim">No drills assigned to ${characterLabel(id)}.</p>`;
    return;
  }
  el.innerHTML = list.map((d) => `
    <a class="pf-drill" href="/drills">
      <span class="pf-drill-name">${d.name || d.id}</span>
      <span class="pf-drill-meta">
        <span class="pf-chip pf-chip-${d.bucket || "new"}">${bucketLabel(d.bucket || "new")}</span>
        <span class="dim">streak ${d.streak || 0}</span>
      </span>
    </a>`).join("");
}

let tallyDummy = localStorage.getItem("bd.profile.tally.dummy") || "all";
let tallyMatchups = [];

const GOT_PREFIXES = ["got_", "lost_"];
const GOT_SUFFIXES = ["_whiffed", "_teched", "_stuffed", "_miss"];
const isReceiver = (k) =>
  GOT_PREFIXES.some((p) => k.startsWith(p)) ||
  GOT_SUFFIXES.some((x) => k.endsWith(x));

async function renderTally() {
  const el = document.getElementById("pf-tally");
  if (!el) return;
  if (shared) {

    el.innerHTML = `<p class="dim">Tallies are not part of a shared profile.</p>`;
    return;
  }
  const q = new URLSearchParams({ character: selected });
  if (tallyDummy && tallyDummy !== "all") q.set("dummy", tallyDummy);
  const data = (await getJSON("/api/stats/tally?" + q.toString())) || {};
  tallyMatchups = data.matchups || [];
  renderTallyPicker();

  const totals = data.totals || {};
  const keys = Object.keys(totals);
  if (!keys.length) {

    el.innerHTML = `<p class="dim">No tally recorded for ${characterLabel(selected)}${
      tallyDummy !== "all" ? " vs " + characterLabel(tallyDummy) : ""
    } yet. Stopping or resetting a tally in game saves it here.</p>`;
    return;
  }
  const gave = keys.filter((k) => !isReceiver(k));
  const took = keys.filter(isReceiver);
  const column = (title, list) => {
    if (!list.length) return "";
    const max = Math.max(...list.map((k) => totals[k]));
    const rows = list
      .sort((a, b) => totals[b] - totals[a])
      .map((k) => `
        <div class="pf-tally-row">
          <span class="pf-tally-name">${titleCase(k)}</span>
          <span class="pf-tally-bar"><i style="width:${Math.round((totals[k] / max) * 100)}%"></i></span>
          <b>${totals[k]}</b>
        </div>`).join("");
    return `<div class="pf-tally-col"><h3>${title}</h3>${rows}</div>`;
  };
  el.innerHTML = column("What I did to them", gave) + column("What they did to me", took);
}

function renderTallyPicker() {
  const sel = document.getElementById("pf-tally-dummy");
  if (!sel) return;

  const opponents = [...new Set(
    tallyMatchups
      .filter((m) => m.character_id === selected && m.dummy_character_id)
      .map((m) => m.dummy_character_id))];
  sel.innerHTML = ['<option value="all">Any opponent</option>']
    .concat(opponents.map((c) => `<option value="${c}">${characterLabel(c)}</option>`))
    .join("");

  sel.value = opponents.includes(tallyDummy) ? tallyDummy : "all";
  sel.onchange = () => {
    tallyDummy = sel.value;
    localStorage.setItem("bd.profile.tally.dummy", tallyDummy);
    renderTally();
  };
}

const EXPORT_VERSION = 1;
let shared = null;

function sharedSummary(id) {
  const s = shared && shared.characters && shared.characters[id]
    ? shared.characters[id].summary
    : null;
  if (!s) return null;

  return {
    drills: s.drills,
    due: null,
    sessions: s.sessions,
    attempts: s.attempts,
    successes: s.successes,
    rate: s.rate,
    avgGrade: s.average_grade,
    bestStreak: s.best_streak,
    buckets: s.buckets || {},
  };
}

function readSharedFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    let data;
    try {
      data = JSON.parse(reader.result);
    } catch {
      alert("That file is not a profile -- it is not valid JSON.");
      return;
    }

    if (!data || data.format !== "beast_drills_profile") {
      alert("That file is not a Beast Drills profile.");
      return;
    }
    if (data.version > EXPORT_VERSION) {
      alert(
        `That profile was written by a newer version (v${data.version}; this ` +
        `page reads v${EXPORT_VERSION}). Some of it may not show correctly.`
      );
    } else if (data.version < EXPORT_VERSION) {
      alert(
        `That profile is an older format (v${data.version}); showing what ` +
        `still applies.`
      );
    }
    shared = data;
    const who = Object.keys(shared.characters || {});
    if (who.length && !who.includes(selected)) selected = who[0];
    renderPicker();
    render();
  };
  reader.onerror = () => alert("Could not read that file.");
  reader.readAsText(file);
}

function renderViewingBar() {
  const bar = document.getElementById("pf-viewing");
  if (!bar) return;
  bar.hidden = !shared;
  if (!shared) return;
  const when = (shared.exported_at || "").slice(0, 10);
  const n = Object.keys(shared.characters || {}).length;
  document.getElementById("pf-viewing-text").textContent =
    `Viewing a shared profile${when ? " from " + when : ""} -- ` +
    `${n} character${n === 1 ? "" : "s"}. Nothing here touches your own data.`;
}

function wireShare() {
  const btn = document.getElementById("pf-import-btn");
  const input = document.getElementById("pf-import-file");
  if (btn && input) {
    btn.onclick = () => input.click();
    input.onchange = () => {
      if (input.files && input.files[0]) readSharedFile(input.files[0]);

      input.value = "";
    };
  }
  const exit = document.getElementById("pf-viewing-exit");
  if (exit) {
    exit.onclick = () => {
      shared = null;
      renderPicker();
      render();
    };
  }
}

function render() {
  renderViewingBar();

  const s = shared ? sharedSummary(selected) : summarise(drillsFor(selected));
  renderHero(selected, s || summarise([]));
  renderDonut(s || summarise([]));
  renderZones(selected);
  renderTop(selected);
  renderTally();
}

function renderPicker() {
  const sel = document.getElementById("pf-character");

  const played = new Set(
    shared
      ? Object.keys(shared.characters || {})
      : [
          ...drills.map((d) => d.character_id).filter(Boolean),
          ...Object.keys(hitZones),
        ]
  );
  const ordered = [
    ...CHARACTER_ROSTER.filter((c) => played.has(c)),
    ...CHARACTER_ROSTER.filter((c) => !played.has(c)),
  ];
  sel.innerHTML = ordered.map((c) =>
    `<option value="${c}"${c === selected ? " selected" : ""}>${characterLabel(c)}${
      played.has(c) ? "" : " · no data"}</option>`).join("");
  sel.onchange = () => {
    selected = sel.value;
    localStorage.setItem(STORE_KEY, selected);
    render();
  };
}

(async function init() {
  const [d, hz] = await Promise.all([
    getJSON("/api/drills"),
    getJSON("/api/stats/hit_zones"),
  ]);
  drills = Array.isArray(d) ? d : (d && d.drills) || [];
  hitZones = hz || {};
  if (!CHARACTER_ROSTER.includes(selected)) selected = "jp";
  wireShare();
  renderPicker();
  render();
})();
