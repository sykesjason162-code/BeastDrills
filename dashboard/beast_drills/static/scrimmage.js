const GAVE = "var(--c-gave)";
const TOOK = "var(--c-took)";

const RUNGS = ["sa", "drive", "vitality", "drive recovery"];

let STATE = {};

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

function rungLabel(handicap) {
  if (!handicap) return "even gauges";
  const applied = RUNGS.slice(0, Math.abs(handicap));
  return applied.join(", ") + (handicap > 0 ? " against you" : " in your favour");
}

function roundChart(scores) {
  const w = 300, h = 130, pad = 26, n = scores.length || 1;
  const svg = svgEl("svg", {
    viewBox: "0 0 " + w + " " + h, role: "img",
    "aria-label": "Score for each of " + n + " rounds",
  });
  svg.style.width = "100%";
  svg.style.height = "auto";
  const band = (w - pad * 2) / n;
  scores.forEach((score, i) => {
    const value = score == null ? 0 : score;
    const barH = Math.max(2, (value / 100) * (h - pad - 24));
    const x = pad + i * band + band * 0.22;
    const bw = band * 0.56;

    svg.appendChild(svgEl("rect", {
      x: x, y: h - pad - barH, width: bw, height: barH, rx: 4, fill: GAVE,
    }));
    svg.appendChild(svgText({
      x: x + bw / 2, y: h - pad - barH - 6, "text-anchor": "middle",
      "font-size": 12, fill: "var(--txt)",
    }, value ? value.toFixed(0) : "-"));
    svg.appendChild(svgText({
      x: x + bw / 2, y: h - pad + 14, "text-anchor": "middle",
      "font-size": 11, fill: "var(--dim)",
    }, "R" + (i + 1)));
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
    gave + " you"));
  svg.appendChild(svgText({ x: w, y: 42, "text-anchor": "end", "font-size": 11,
    fill: "var(--dim)" }, took + " them"));
  return svg;
}

function weaknessChart(weaknesses, label) {

  if (!weaknesses) {
    return el("p", "muted", "Not recorded for this set — it predates the breakdown.");
  }
  const rows = weaknesses.slice(0, 8);
  if (!rows.length) return el("p", "muted", "Nothing landed on you worth ranking.");
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
      row.weakness.replace(/_/g, " ")));
    const bw = Math.max(2, (row.count / max) * (w - labelW - 30));
    svg.appendChild(svgEl("rect", { x: labelW, y: y, width: bw, height: 14, rx: 4,
      fill: TOOK }));
    svg.appendChild(svgText({ x: labelW + bw + 6, y: y + 12, "font-size": 11,
      fill: "var(--txt)" }, String(row.count)));
  });
  return svg;
}

function panel(title, sub, body) {
  const p = el("div", "scrim-panel");
  p.appendChild(el("h3", null, title));
  if (sub) p.appendChild(el("p", "sub", sub));
  p.appendChild(body);
  return p;
}

function fact(label, value) {
  const span = el("span");
  span.appendChild(document.createTextNode(label + " "));
  span.appendChild(el("b", null, value));
  return span;
}

function renderSession(session) {
  const host = document.getElementById("scrim-detail");
  host.textContent = "";
  if (!session) return;

  const results = session.round_results || session.match_results || [];
  const won = results.filter(Boolean).length;

  const hero = el("div", "scrim-hero");
  const score = el("div", "scrim-score", String(session.score == null ? "-" : session.score));
  score.appendChild(el("small", null, " / 100"));
  hero.appendChild(score);

  const facts = el("div", "scrim-facts");
  facts.appendChild(fact("Rounds", won + " of " + results.length));
  facts.appendChild(fact("Exchanges", String(session.exchanges == null ? "-" : session.exchanges)));
  facts.appendChild(fact("Difficulty",
    "CPU " + session.difficulty_before + "→" + session.difficulty_after));
  facts.appendChild(fact("Next", rungLabel(session.handicap_after || 0)));
  hero.appendChild(facts);
  host.appendChild(hero);

  const grid = el("div", "scrim-grid");

  grid.appendChild(panel("Each round",
    "The set score is the combined tally, not the average of these.",
    roundChart(session.per_round_scores || results.map(() => null))));

  const gave = session.giver_events, took = session.receiver_events;
  if (gave != null && took != null) {
    const body = el("div");
    const legend = el("div", "scrim-legend");
    const mark = (colour, text) => {
      const s = el("span");
      const i = el("i");
      i.style.background = colour;
      s.appendChild(i);
      s.appendChild(document.createTextNode(text));
      return s;
    };
    legend.appendChild(mark(GAVE, "You did"));
    legend.appendChild(mark(TOOK, "Done to you"));
    body.appendChild(legend);
    body.appendChild(splitChart(gave, took));
    grid.appendChild(panel("Where the score came from",
      "Your share of everything that happened.", body));
  } else {
    grid.appendChild(panel("Where the score came from",
      "Your share of everything that happened.",
      el("p", "muted", "Not recorded for this set — it predates the breakdown.")));
  }

  grid.appendChild(panel("What kept happening", "Worst first.",
    weaknessChart(session.weaknesses)));

  if (session.rounds && session.rounds.length) {
    const list = el("div", "scrim-rounds");
    session.rounds.forEach(round => {
      const box = el("div", "scrim-round");
      const head = el("div", "scrim-round-head");
      head.appendChild(el("b", null, "Round " + round.round));
      head.appendChild(el("span", round.won ? "won" : "lost",
        round.won ? "won" : "lost"));
      head.appendChild(el("span", "why",
        (round.score == null ? "-" : round.score) + " / 100"
        + (round.exchanges == null ? "" : "  ·  " + round.exchanges + " exchanges")));
      box.appendChild(head);
      const rows = round.weaknesses || [];
      if (rows.length) {
        box.appendChild(weaknessChart(rows,
          "Round " + round.round + ": what kept happening, worst first"));
      } else if (round.worst) {
        box.appendChild(el("p", "muted",
          "Worst: " + round.worst.replace(/_/g, " ") + " ×" + round.worst_count));
      }
      list.appendChild(box);
    });
    grid.appendChild(panel("Round by round",
      "Where each round's score came from.", list));
  }

  const work = el("ul", "scrim-list");
  (session.recommendations || []).forEach(pick => {
    const li = el("li");
    li.appendChild(el("span", null, pick.name || pick.drill_id));
    li.appendChild(el("span", "why",
      pick.weakness.replace(/_/g, " ") + " ×" + pick.weakness_count));
    work.appendChild(li);
  });
  if (!work.children.length) work.appendChild(el("li", "muted", "Nothing to assign."));
  grid.appendChild(panel("Work on", "Drills that train what went wrong.", work));

  const gaps = session.unaddressed || [];
  if (gaps.length) {
    const list = el("ul", "scrim-list");
    gaps.forEach(gap => {
      const li = el("li", "scrim-gap");
      li.appendChild(el("span", null, gap.weakness.replace(/_/g, " ")));
      li.appendChild(el("span", "why", "×" + gap.count));
      list.appendChild(li);
    });
    grid.appendChild(panel("No drill trains these",
      "A gap in the deck rather than in your play.", list));
  }

  host.appendChild(grid);
}

function fillSessions() {
  const matchup = document.getElementById("scrim-matchup").value;
  const picker = document.getElementById("scrim-session");
  const parts = matchup.split("|");
  const record = (STATE[parts[0]] || {})[parts[1]] || {};
  const sessions = record.sessions || [];
  picker.textContent = "";

  sessions.slice().reverse().forEach((session, i) => {
    const rounds = (session.round_results || session.match_results || []);
    const option = el("option", null,
      (session.at || "").replace("T", " ").replace("Z", "")
      + "  ·  " + rounds.filter(Boolean).length + "/" + rounds.length
      + "  ·  " + (session.score == null ? "-" : session.score));
    option.value = String(sessions.length - 1 - i);
    picker.appendChild(option);
  });
  picker.onchange = () => renderSession(sessions[Number(picker.value)]);
  renderSession(sessions[sessions.length - 1]);
}

async function load() {
  const res = await fetch("/api/scrimmage");
  STATE = await res.json();
  const picker = document.getElementById("scrim-matchup");
  let any = false;
  Object.keys(STATE || {}).forEach(character => {
    Object.keys(STATE[character] || {}).forEach(dummy => {
      const record = STATE[character][dummy];
      if (!record || !(record.sessions || []).length) return;
      any = true;
      const option = el("option", null,
        characterLabel(character) + " vs " + characterLabel(dummy)
        + "  ·  CPU " + record.difficulty);
      option.value = character + "|" + dummy;
      picker.appendChild(option);
    });
  });
  document.getElementById("scrim-empty").style.display = any ? "none" : "";
  document.querySelector(".scrim-picker").style.display = any ? "" : "none";
  if (any) {
    picker.onchange = fillSessions;
    fillSessions();
  }
}

load();
