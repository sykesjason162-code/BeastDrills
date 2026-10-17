const GAVE = "var(--c-gave)";
const TOOK = "var(--c-took)";

let MATCHES = [];
let OVERALL = {};

const T = (s) => (window.i18n ? window.i18n.T(s) : s);

const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
};

const svgEl = (tag, attrs) => {
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
  return n;
};

const svgText = (attrs, text) => {
  const n = svgEl("text", attrs);
  n.textContent = text;
  return n;
};

const when = (epoch) => {
  const d = new Date((epoch || 0) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate())
    + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
};

const charName = (id) => (id ? characterLabel(id) : T("Unknown"));

function result(m) {
  if (!m.finished) return T("Unfinished");
  if (m.won === true) return T("Won") + " " + m.wins + "–" + m.losses;
  if (m.won === false) return T("Lost") + " " + m.wins + "–" + m.losses;
  return m.wins + "–" + m.losses;
}

function opponent(m) {
  if (m.opponent_kind === "cpu") {
    return T("CPU") + (m.opponent_cpu_level != null && m.opponent_cpu_level >= 0
      ? " " + T("level") + " " + m.opponent_cpu_level : "");
  }
  if (m.opponent_kind === "online") return T("Online player");
  if (m.opponent_kind === "local") return T("Local player");
  return T("Unknown");
}

function roundChart(rounds) {
  const w = 300, h = 130, pad = 26, n = rounds.length || 1;
  const svg = svgEl("svg", {
    viewBox: "0 0 " + w + " " + h, role: "img",
    "aria-label": "Score for each of " + n + " rounds",
  });
  svg.style.width = "100%";
  svg.style.height = "auto";
  const band = (w - pad * 2) / n;
  rounds.forEach((round, i) => {
    const value = round.score == null ? 0 : round.score;
    const barH = Math.max(2, (value / 100) * (h - pad - 24));
    const x = pad + i * band + band * 0.22;
    const bw = band * 0.56;
    svg.appendChild(svgEl("rect", {
      x: x, y: h - pad - barH, width: bw, height: barH, rx: 4,
      fill: round.won === false ? TOOK : GAVE,
    }));
    svg.appendChild(svgText({
      x: x + bw / 2, y: h - pad - barH - 6, "text-anchor": "middle",
      "font-size": 12, fill: "var(--txt)",
    }, value ? value.toFixed(0) : "-"));
    svg.appendChild(svgText({
      x: x + bw / 2, y: h - pad + 14, "text-anchor": "middle",
      "font-size": 11, fill: "var(--dim)",
    }, "R" + round.round));
  });
  svg.appendChild(svgEl("line", {
    x1: pad, y1: h - pad, x2: w - pad, y2: h - pad,
    stroke: "var(--line2)", "stroke-width": 1,
  }));
  return svg;
}

function splitChart(gave, took) {
  const total = gave + took || 1;
  const w = 300, h = 46;
  const svg = svgEl("svg", {
    viewBox: "0 0 " + w + " " + h, role: "img",
    "aria-label": gave + " things you did against " + took + " done to you",
  });
  svg.style.width = "100%";
  svg.style.height = "auto";
  const gw = (gave / total) * w;
  svg.appendChild(svgEl("rect", {
    x: 0, y: 8, width: Math.max(0, gw - 1), height: 20, rx: 4, fill: GAVE,
  }));
  svg.appendChild(svgEl("rect", {
    x: gw + 1, y: 8, width: Math.max(0, w - gw - 1), height: 20, rx: 4, fill: TOOK,
  }));
  svg.appendChild(svgText({ x: 0, y: 42, "font-size": 11, fill: "var(--dim)" },
    gave + " " + T("you")));
  svg.appendChild(svgText({ x: w, y: 42, "text-anchor": "end", "font-size": 11,
    fill: "var(--dim)" }, took + " " + T("them")));
  return svg;
}

function weaknessChart(weaknesses, label) {
  const rows = (weaknesses || []).slice(0, 8);
  if (!rows.length) return el("p", "muted", T("Nothing landed on you worth ranking."));
  const max = Math.max.apply(null, rows.map(r => r.count)) || 1;
  const rowH = 22, labelW = 132, w = 320, h = rows.length * rowH + 6;
  const svg = svgEl("svg", {
    viewBox: "0 0 " + w + " " + h, role: "img",
    "aria-label": label || "What kept happening to you, worst first",
  });
  svg.style.width = "100%";
  svg.style.height = "auto";
  rows.forEach((row, i) => {
    const y = i * rowH + 4;
    svg.appendChild(svgText({ x: 0, y: y + 12, "font-size": 12, fill: "var(--dim)" },
      counterLabel(row.weakness)));
    const bw = Math.max(2, (row.count / max) * (w - labelW - 30));
    svg.appendChild(svgEl("rect", { x: labelW, y: y, width: bw, height: 14, rx: 4,
      fill: TOOK }));
    svg.appendChild(svgText({ x: labelW + bw + 6, y: y + 12, "font-size": 11,
      fill: "var(--txt)" }, String(row.count)));
  });
  return svg;
}

function panel(title, sub, body) {
  const p = el("div", "mt-panel");
  p.appendChild(el("h3", null, T(title)));
  if (sub) p.appendChild(el("p", "sub", T(sub)));
  p.appendChild(body);
  return p;
}

function fact(label, value) {
  const span = el("span");
  span.appendChild(document.createTextNode(T(label) + " "));
  span.appendChild(el("b", null, value));
  return span;
}

function renderMatch(m) {
  const host = document.getElementById("mt-detail");
  host.textContent = "";
  if (!m) return;

  const hero = el("div", "mt-hero");
  const score = el("div", "mt-score", String(m.score == null ? "-" : Math.round(m.score)));
  score.appendChild(el("small", null, " / 100"));
  hero.appendChild(score);

  const facts = el("div", "mt-facts");
  facts.appendChild(fact("Result", result(m)));
  facts.appendChild(fact("Mode", T(m.mode_name || "")));
  facts.appendChild(fact("Matchup", charName(m.character_id) + " vs " + charName(m.opponent_id)));
  facts.appendChild(fact("Opponent", opponent(m)));
  facts.appendChild(fact("Exchanges", String(m.exchanges == null ? "-" : m.exchanges)));
  hero.appendChild(facts);
  if (m.finished) hero.appendChild(starButton(m));
  host.appendChild(hero);

  if (m.player_side === 1) {
    host.appendChild(el("p", "mt-note", T("You played from the right side. The tally counts from the left, so this match was turned around to your side; whiffs, missed blocks and parries, parry whiffs, perfect parries and missed back rolls are only counted on the left side and are left out.")));
  } else if (m.player_side == null) {
    host.appendChild(el("p", "mt-note", T("No single player on this machine, so this is the left side's view and it does not change your next session.")));
  }
  if (!m.finished) {
    host.appendChild(el("p", "mt-note", T("The game closed before this match ended. The rounds that finished are kept; an unfinished match does not change your next session.")));
  }

  const grid = el("div", "mt-grid");
  const rounds = m.rounds_list || [];

  grid.appendChild(panel("Each round",
    "The match score is the combined tally, not the average of these.",
    roundChart(rounds)));

  const body = el("div");
  const legend = el("div", "mt-legend");
  const mark = (colour, text) => {
    const s = el("span");
    const i = el("i");
    i.style.background = colour;
    s.appendChild(i);
    s.appendChild(document.createTextNode(T(text)));
    return s;
  };
  legend.appendChild(mark(GAVE, "You did"));
  legend.appendChild(mark(TOOK, "Done to you"));
  body.appendChild(legend);
  body.appendChild(splitChart(m.giver_events || 0, m.receiver_events || 0));
  grid.appendChild(panel("Where the score came from",
    "Your share of everything that happened.", body));

  grid.appendChild(panel("What kept happening", "Worst first.",
    weaknessChart(m.weaknesses)));

  if (rounds.length) {
    const list = el("div", "mt-rounds");
    rounds.forEach(round => {
      const box = el("div", "mt-round");
      const head = el("div", "mt-round-head");
      head.appendChild(el("b", null, T("Round") + " " + round.round));
      const verdict = round.won === true ? "won" : round.won === false ? "lost" : "draw";
      head.appendChild(el("span", verdict, T(verdict === "draw" ? "double KO" : verdict)));
      if (round.finish === "time_up") head.appendChild(el("span", "draw", T("time up")));
      head.appendChild(el("span", "why",
        (round.score == null ? "-" : Math.round(round.score)) + " / 100"
        + (round.exchanges == null ? "" : "  ·  " + round.exchanges + " " + T("exchanges"))));
      box.appendChild(head);
      if ((round.weaknesses || []).length) {
        box.appendChild(weaknessChart(round.weaknesses,
          "Round " + round.round + ": what kept happening, worst first"));
      }
      list.appendChild(box);
    });
    grid.appendChild(panel("Round by round",
      "Where each round's score came from.", list));
  }

  const work = el("ul", "mt-list");
  (m.recommendations || []).forEach(pick => {
    const li = el("li");
    li.appendChild(el("span", null, pick.name || pick.drill_id));
    li.appendChild(el("span", "why",
      counterLabel(pick.weakness) + " ×" + pick.weakness_count));
    work.appendChild(li);
  });
  if (!work.children.length) work.appendChild(el("li", "muted", T("Nothing to assign.")));
  grid.appendChild(panel("Work on",
    "Drills that train what went wrong. The newest match puts these first in your next session.",
    work));

  const gaps = m.unaddressed || [];
  if (gaps.length) {
    const list = el("ul", "mt-list");
    gaps.forEach(gap => {
      const li = el("li", "mt-gap");
      li.appendChild(el("span", null, counterLabel(gap.weakness)));
      li.appendChild(el("span", "why", "×" + gap.count));
      list.appendChild(li);
    });
    grid.appendChild(panel("No drill trains these",
      "A gap in the deck rather than in your play.", list));
  }

  host.appendChild(grid);
}

function starButton(m) {
  const b = el("button", "mt-star" + (m.favorite ? " is-on" : ""),
    m.favorite ? "★ " + T("Starred") : "☆ " + T("Star"));
  b.title = T("A starred match is kept when old matches are cleared to save space.");
  b.onclick = async () => {
    const want = !m.favorite;
    try {
      const r = await fetch("/api/matches/" + encodeURIComponent(m.match_id) + "/favorite",
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ favorite: want }) });
      if (!r.ok) return;
    } catch { return; }
    m.favorite = want;
    const picker = document.getElementById("mt-match");
    const keep = picker.value;
    fillMatches();
    picker.value = keep;
    renderMatch(currentList()[Number(keep)]);
  };
  return b;
}

function renderOverall() {
  const host = document.getElementById("mt-overall");
  host.textContent = "";
  const wanted = document.getElementById("mt-character").value;
  const o = OVERALL[wanted || "all"];
  if (!o || !o.matches) return;

  const box = el("div", "mt-panel mt-overall");
  box.appendChild(el("h3", null, T("Overall") + (wanted ? " — " + charName(wanted) : "")));
  box.appendChild(el("p", "sub", T("Every match you have finished, including ones whose details were cleared to save space.")));
  const facts = el("div", "mt-facts");
  facts.appendChild(fact("Matches played", String(o.matches)));
  facts.appendChild(fact("Won", o.wins + "–" + o.losses));
  facts.appendChild(fact("Rounds", o.rounds_won + "–" + o.rounds_lost));
  facts.appendChild(fact("Score", o.score == null ? "-" : String(Math.round(o.score))));
  box.appendChild(facts);

  const grid = el("div", "mt-grid");
  grid.appendChild(panel("What keeps happening", "Across all of them, worst first.",
    weaknessChart(o.weaknesses)));
  const list = el("ul", "mt-list");
  (o.opponents || []).slice(0, 12).forEach(op => {
    const li = el("li");
    li.appendChild(el("span", null, charName(op.opponent_id)));
    li.appendChild(el("span", "why",
      op.wins + "–" + op.losses + "  ·  " + op.matches + " " + T("matches")
      + (op.score == null ? "" : "  ·  " + Math.round(op.score))));
    list.appendChild(li);
  });
  grid.appendChild(panel("By opponent", "Won–lost, matches, score.", list));
  box.appendChild(grid);
  host.appendChild(box);
}

function currentList() {
  const wanted = document.getElementById("mt-character").value;
  return MATCHES.filter(m => !wanted || m.character_id === wanted);
}

function fillMatches() {
  renderOverall();
  const picker = document.getElementById("mt-match");
  const shown = currentList();
  picker.textContent = "";
  shown.forEach((m, i) => {
    const option = el("option", null,
      (m.favorite ? "★ " : "") + when(m.timestamp) + "  ·  " + T(m.mode_name || "") + "  ·  "
      + charName(m.character_id) + " vs " + charName(m.opponent_id)
      + "  ·  " + result(m));
    option.value = String(i);
    picker.appendChild(option);
  });
  picker.onchange = () => renderMatch(shown[Number(picker.value)]);
  renderMatch(shown[0]);
}

async function load() {
  const res = await fetch("/api/matches");
  const body = (await res.json()) || {};
  MATCHES = body.matches || [];
  OVERALL = body.overall || {};
  const any = MATCHES.length > 0 || ((OVERALL.all || {}).matches || 0) > 0;
  document.getElementById("mt-empty").style.display = any ? "none" : "";
  document.querySelector(".mt-picker").style.display = any ? "" : "none";
  if (!any) return;

  const picker = document.getElementById("mt-character");
  const all = el("option", null, T("All characters"));
  all.value = "";
  picker.appendChild(all);
  const chars = MATCHES.map(m => m.character_id)
    .concat(Object.keys(OVERALL).filter(k => k !== "all"));
  [...new Set(chars.filter(Boolean))].sort().forEach(id => {
    const option = el("option", null, charName(id));
    option.value = id;
    picker.appendChild(option);
  });
  picker.onchange = fillMatches;
  fillMatches();
}

load();
